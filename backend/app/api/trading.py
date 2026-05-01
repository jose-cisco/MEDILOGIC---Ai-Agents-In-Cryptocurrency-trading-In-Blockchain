from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime
import httpx
from fastapi import APIRouter, HTTPException, Request
from app.schemas.models import TradeRequest, TradeResult, TradeAction, AgentTrace, RiskAssessRequest, RiskAssessResult, RiskMetricsResult, RiskCalibrationResult
from app.agents.orchestrator import TradingOrchestrator
from app.risk.risk_engine import RiskEngine, RiskLevel, MarketData, OnChainData
from app.risk.risk_storage import get_risk_storage
from app.risk.risk_metrics import RiskMetricsCalculator, RiskCalibrator, RiskAlerter
from app.blockchain.ethereum import EthereumClient
from app.blockchain.solana import SolanaClient
from app.core.config import get_settings
from app.core.x402 import x402_service, PaymentResource, get_resource_price
from app.governance.agent_governance import governance_service

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = TradingOrchestrator()
eth_client = EthereumClient()
sol_client = SolanaClient()
_SEEN_NONCES: dict[str, int] = {}


def get_mock_market_data(token_pair: str, chain: str) -> dict:
    import random

    base_prices = {
        "ETH/USDT": 3200,
        "SOL/USDT": 180,
        "BTC/USDT": 95000,
        "ETH/USDC": 3200,
    }
    base = base_prices.get(token_pair, 1000)
    return {
        "price": base + random.uniform(-base * 0.02, base * 0.02),
        "volume_24h": random.uniform(1e9, 5e9),
        "rsi_14": random.uniform(30, 70),
        "macd_signal": random.choice(["bullish", "bearish", "neutral"]),
        "sma_7": base * random.uniform(0.98, 1.02),
        "sma_14": base * random.uniform(0.97, 1.03),
        "sma_30": base * random.uniform(0.95, 1.05),
        "tvl": random.uniform(1e10, 5e10),
        "chain": chain,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def get_real_market_data(token_pair: str, chain: str, fail_closed: bool = True) -> dict:
    """Fetch live market data from CoinGecko / exchange APIs.

    In live mode we MUST NOT use random mock data — real capital is at risk.
    
    Args:
        token_pair: Trading pair symbol
        chain: Blockchain name
        fail_closed: If True, raise exception on failure instead of returning mock.
                     Live trading should ALWAYS fail closed for safety.
    
    Raises:
        HTTPException: When fail_closed=True and data cannot be fetched.
    """
    symbol_map = {
        "ETH/USDT": "ethereum",
        "ETH/USDC": "ethereum",
        "SOL/USDT": "solana",
        "BTC/USDT": "bitcoin",
    }
    gecko_id = symbol_map.get(token_pair)
    if not gecko_id:
        logger.warning("No CoinGecko mapping for %s", token_pair)
        if fail_closed:
            raise HTTPException(
                status_code=503,
                detail=f"Unsupported token pair for live trading: {token_pair}. "
                       f"Supported pairs: {list(symbol_map.keys())}"
            )
        return {**get_mock_market_data(token_pair, chain), "data_source": "mock_fallback"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "ids": gecko_id,
                    "price_change_percentage": "7d,14d,30d",
                },
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                raise ValueError("Empty response from CoinGecko")
            coin = items[0]

        price = float(coin["current_price"])
        logger.info("Successfully fetched live market data for %s from CoinGecko", token_pair)
        return {
            "price": price,
            "volume_24h": float(coin.get("total_volume", 0)),
            "rsi_14": None,  # not available from this endpoint
            "macd_signal": None,
            "sma_7": price * (1 + float(coin.get("price_change_percentage_7d_in_currency", 0) or 0) / 100),
            "sma_14": price * (1 + float(coin.get("price_change_percentage_14d_in_currency", 0) or 0) / 100),
            "sma_30": price * (1 + float(coin.get("price_change_percentage_30d_in_currency", 0) or 0) / 100),
            "tvl": None,
            "chain": chain,
            "timestamp": datetime.utcnow().isoformat(),
            "data_source": "coingecko",
        }
    except Exception as exc:
        logger.error(
            "LIVE market data fetch FAILED for %s: %s. "
            "CRITICAL: Cannot proceed with live trading without real market data!",
            token_pair, exc
        )
        if fail_closed:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"CRITICAL: Live market data unavailable for {token_pair}. "
                    f"Trading blocked for safety. Error: {str(exc)}. "
                    f"Live trading requires real-time market data - cannot proceed with stale/mock data."
                )
            )
        # Only return mock in simulation contexts (never in live trading)
        return {**get_mock_market_data(token_pair, chain), "data_source": "mock_fallback_error"}


def _prune_seen_nonces(now_ts: int, ttl_seconds: int) -> None:
    expired = [nonce for nonce, ts in _SEEN_NONCES.items() if now_ts - ts > ttl_seconds]
    for nonce in expired:
        _SEEN_NONCES.pop(nonce, None)


def _verify_live_signed_headers(request: Request, settings) -> None:
    nonce = request.headers.get("x-live-nonce", "").strip()
    ts_raw = request.headers.get("x-live-timestamp", "").strip()
    signature = request.headers.get("x-live-signature", "").strip()

    if not nonce or not ts_raw or not signature:
        raise HTTPException(
            status_code=403,
            detail=(
                "Missing live safeguard headers. Required: "
                "X-Live-Nonce, X-Live-Timestamp, X-Live-Signature."
            ),
        )

    try:
        ts = int(ts_raw)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Invalid X-Live-Timestamp.") from exc

    now_ts = int(time.time())
    max_skew = settings.LIVE_GUARD_MAX_SKEW_SECONDS
    if abs(now_ts - ts) > max_skew:
        raise HTTPException(
            status_code=403,
            detail=f"Stale/invalid live signature timestamp. Max skew is {max_skew}s.",
        )

    _prune_seen_nonces(now_ts, max_skew)
    if nonce in _SEEN_NONCES:
        raise HTTPException(status_code=403, detail="Replay detected: nonce already used.")

    payload = f"{nonce}:{ts}".encode("utf-8")
    expected = hmac.new(
        settings.LIVE_GUARD_SECRET.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Invalid live safeguard signature.")

    _SEEN_NONCES[nonce] = now_ts


def _validate_market_data_freshness(market_data: dict, max_age_seconds: int) -> None:
    ts_raw = market_data.get("timestamp")
    if not ts_raw:
        raise HTTPException(status_code=503, detail="Market data missing timestamp.")
    try:
        ts = datetime.fromisoformat(ts_raw)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Invalid market data timestamp format.") from exc
    age = (datetime.utcnow() - ts).total_seconds()
    if age > max_age_seconds:
        raise HTTPException(
            status_code=503,
            detail=f"Market data is stale ({age:.1f}s old, max {max_age_seconds}s).",
        )


def _is_circuit_breaker_triggered(settings, market_data: dict, risk_score: float) -> tuple[bool, str]:
    risk_threshold = float(getattr(settings, "LIVE_CIRCUIT_BREAKER_RISK_THRESHOLD", 0.75))
    vol_threshold = float(getattr(settings, "LIVE_CIRCUIT_BREAKER_VOLATILITY_PCT", 0.08))
    if risk_score >= risk_threshold:
        return True, f"risk_score {risk_score:.2f} >= threshold {risk_threshold:.2f}"
    price = float(market_data.get("price", 0.0))
    sma_30 = float(market_data.get("sma_30", 0.0))
    if sma_30 > 0:
        deviation = abs(price - sma_30) / sma_30
        if deviation >= vol_threshold:
            return (
                True,
                f"volatility deviation {deviation:.3f} >= threshold {vol_threshold:.3f}",
            )
    return False, ""


def _get_x402_metadata(http_request: Request) -> dict:
    """Extract x402 payment receipt from request state (set by middleware)."""
    receipt = getattr(http_request.state, "x402_receipt", None)
    if receipt:
        return {
            "payment_required": True,
            "payment_verified": True,
            "payment_tx_hash": receipt.tx_hash,
            "payment_amount_usd": receipt.amount_usd,
            "payment_resource": receipt.resource,
        }
    settings = get_settings()
    if getattr(settings, "X402_ENABLED", False):
        return {
            "payment_required": True,
            "payment_verified": False,
            "payment_resource": PaymentResource.TRADE_EXECUTE.value,
        }
    return {"payment_required": False}


# ─────────────────────────────────────────────────────────────────────────────
# Risk Assessment Helpers
# ─────────────────────────────────────────────────────────────────────────────

_risk_engine: RiskEngine | None = None
_risk_alerter: RiskAlerter | None = None


def _get_risk_engine() -> RiskEngine:
    """Get or create the singleton RiskEngine instance."""
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
    return _risk_engine


def _get_risk_alerter() -> RiskAlerter:
    """Get or create the singleton RiskAlerter instance."""
    global _risk_alerter
    if _risk_alerter is None:
        _risk_alerter = RiskAlerter(alert_threshold=70.0, window_size=10)
    return _risk_alerter


def _convert_market_data_to_risk_format(market_data: dict, chain: str) -> MarketData:
    """Convert market data dict to RiskEngine MarketData format."""
    return MarketData(
        price=float(market_data.get("price", 0)),
        volume_24h=float(market_data.get("volume_24h", 0)),
        volatility_24h=market_data.get("volatility_24h"),
        price_change_24h=market_data.get("price_change_24h"),
        rsi_14=market_data.get("rsi_14"),
        macd_signal=market_data.get("macd_signal"),
        sma_7=market_data.get("sma_7"),
        sma_14=market_data.get("sma_14"),
        sma_30=market_data.get("sma_30"),
        tvl=market_data.get("tvl"),
        liquidity_depth=market_data.get("liquidity_depth"),
        slippage_estimate=market_data.get("slippage_estimate"),
        chain=chain,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Trade Execution Endpoint
# ─────────────────────────────────────────────────────────────────────────────
#
# RISK SAFETY LOGIC:
# ──────────────────
# The RiskEngine assesses market conditions BEFORE orchestrator execution:
#
#   RISK LEVEL     | SCORE  | ACTION
#   ──────────────┼────────┼──────────────────────────────────────────────────
#   LOW            | 0-25   | Execute normally (no adjustment)
#   MODERATE       | 26-50  | Execute normally (no adjustment)
#   HIGH           | 51-75  | Position size reduced to 50% of requested
#   CRITICAL       | 76-100 | BLOCKED - Trade rejected immediately
#
# This fail-closed approach ensures unsafe conditions are caught before
# any agent processing or on-chain interaction occurs.
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/execute", response_model=TradeResult)
async def execute_trade(request: TradeRequest, http_request: Request):
    settings = get_settings()
    if settings.TRADING_MODE != "paper" and not settings.LIVE_TRADING_ENABLED:
        raise HTTPException(
            status_code=403,
            detail=(
                "Trading blocked by safety gate. Set TRADING_MODE=paper for simulation "
                "or explicitly enable live mode with LIVE_TRADING_ENABLED=true."
            ),
        )
    if settings.TRADING_MODE == "live":
        _verify_live_signed_headers(http_request, settings)
        if getattr(settings, "LIVE_REQUIRE_AGENT_SIGNATURE", False):
            if not request.did or not request.request_nonce or not request.request_timestamp or not request.agent_signature:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Live mode requires DID-signed trade request fields: "
                        "did, request_nonce, request_timestamp, agent_signature."
                    ),
                )
            sig_check = governance_service.verify_agent_signature(
                agent_id=request.agent_id,
                did=request.did,
                request_nonce=request.request_nonce,
                request_timestamp=request.request_timestamp,
                token_pair=request.token_pair,
                chain=request.chain.value,
                max_position_usd=request.max_position_usd,
                prompt=request.prompt,
                signature=request.agent_signature,
            )
            if not sig_check.get("valid", False):
                raise HTTPException(status_code=403, detail=f"Agent signature invalid: {sig_check.get('reason', 'unknown')}")

    governance_check = None
    if getattr(settings, "ENABLE_AGENT_GOVERNANCE", True):
        governance_check = governance_service.pre_trade_check(
            agent_id=request.agent_id,
            token_pair=request.token_pair,
            chain=request.chain.value,
            max_position_usd=request.max_position_usd,
            prompt=request.prompt,
            semantic_threshold=getattr(settings, "SEMANTIC_SIGNAL_BLOCK_THRESHOLD", 2),
        )
        if not governance_check.get("allowed", False):
            return TradeResult(
                success=False,
                action=TradeAction.HOLD,
                token_pair=request.token_pair,
                amount=0,
                price=0.0,
                reasoning="Blocked by governance policy: " + " | ".join(governance_check.get("reasons", [])),
                confidence=0.0,
                timestamp=datetime.utcnow().isoformat(),
                rag_metadata={},
                governance_metadata=governance_check,
                x402_metadata=_get_x402_metadata(http_request),
                risk_metadata=None,  # No risk assessment yet - blocked by governance
            )

    # ── Market data: mock for paper, real API for live ──
    if settings.TRADING_MODE == "live":
        market_data = await get_real_market_data(request.token_pair, request.chain.value)
        _validate_market_data_freshness(
            market_data,
            getattr(settings, "LIVE_MAX_MARKET_DATA_AGE_SECONDS", 180),
        )
    else:
        market_data = get_mock_market_data(request.token_pair, request.chain.value)
    
    # ── Pre-execution Risk Assessment ──
    # Assess risk BEFORE calling orchestrator to fail fast on unsafe conditions
    risk_engine = _get_risk_engine()
    risk_market_data = _convert_market_data_to_risk_format(market_data, request.chain.value)
    risk_assessment = risk_engine.assess(
        market_data=risk_market_data,
        position_size_usd=request.max_position_usd,
        token_pair=request.token_pair,
        chain=request.chain.value,
    )
    risk_metadata = risk_assessment.to_dict()
    logger.info(
        "Pre-execution risk assessment: score=%.2f, level=%s",
        risk_assessment.overall_score,
        risk_assessment.risk_level.value,
    )
    
    # ── Risk Alerting: Check for concerning patterns ──
    risk_alerter = _get_risk_alerter()
    alerts = risk_alerter.check_alerts(
        current_score=risk_assessment.overall_score,
        risk_level=risk_assessment.risk_level.value,
    )
    for alert in alerts:
        logger.warning(
            "RISK ALERT [%s] %s - Action: %s",
            alert["level"],
            alert["message"],
            alert["action"],
        )
    
    # ── SAFETY: Block CRITICAL risk immediately ──
    if risk_assessment.risk_level == RiskLevel.CRITICAL:
        logger.warning(
            "CRITICAL RISK BLOCKED: score=%.2f, token=%s, chain=%s",
            risk_assessment.overall_score,
            request.token_pair,
            request.chain.value,
        )
        # Store blocked assessment for historical tracking
        try:
            risk_storage = get_risk_storage()
            risk_storage.store(
                token_pair=request.token_pair,
                chain=request.chain.value,
                position_size_usd=request.max_position_usd,
                overall_score=risk_assessment.overall_score,
                risk_level=risk_assessment.risk_level.value,
                volatility_risk=risk_assessment.volatility_risk,
                drawdown_risk=risk_assessment.drawdown_risk,
                liquidity_risk=risk_assessment.liquidity_risk,
                onchain_risk=risk_assessment.onchain_risk,
                outcome="blocked",
                position_multiplier=0.0,
                recommendations=risk_assessment.recommendations,
            )
        except Exception as e:
            logger.warning("Failed to store risk assessment: %s", e)
        
        return TradeResult(
            success=False,
            action=TradeAction.HOLD,
            token_pair=request.token_pair,
            amount=0,
            price=market_data["price"],
            reasoning=f"CRITICAL RISK BLOCKED (score={risk_assessment.overall_score:.1f}): "
                      f"{' | '.join(risk_assessment.recommendations)}",
            confidence=0.0,
            timestamp=datetime.utcnow().isoformat(),
            risk_metadata=risk_metadata,
            x402_metadata=_get_x402_metadata(http_request),
        )
    
    # ── Position size adjustment using dynamic sizing ──
    # Use engine's dynamic position multiplier based on score
    position_multiplier = risk_engine.get_position_multiplier(risk_assessment.overall_score)
    if position_multiplier < 1.0:
        logger.warning(
            "HIGH RISK: Position reduced to %d%% (score=%.2f)",
            int(position_multiplier * 100),
            risk_assessment.overall_score,
        )
    
    adjusted_position_usd = request.max_position_usd * position_multiplier
    
    # Resolve model assignments for each agent
    model_assignment = request.get_resolved_models()
    logger.info(
        "Model assignment: Planner=%s | Verifier=%s | Controller=%s | Monitor=%s | Adjuster=%s",
        model_assignment["planner_model"],
        model_assignment["verifier_model"],
        model_assignment["controller_model"],
        model_assignment["monitor_model"],
        model_assignment["adjuster_model"],
    )
    
    try:
        result = await orchestrator.run(
            prompt=request.prompt,
            token_pair=request.token_pair,
            chain=request.chain.value,
            market_data=market_data,
            # Per-agent model selection
            planner_model=model_assignment["planner_model"],
            verifier_model=model_assignment["verifier_model"],
            controller_model=model_assignment["controller_model"],
            monitor_model=model_assignment["monitor_model"],
            adjuster_model=model_assignment["adjuster_model"],
            # Legacy fields for backward compatibility
            model_1=request.model_1.value if request.model_1 else None,
            model_2=request.model_2.value if request.model_2 else None,
            prediction_start_date=request.prediction_start_date,
            prediction_end_date=request.prediction_end_date,
            risk_assessment=risk_metadata,  # Pass risk context to agents
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    decision = result.get("final_decision", {})
    approved = decision.get("approved", False)
    final_risk_score = float(decision.get("final_risk_score", 1.0))

    if settings.TRADING_MODE == "live":
        tripped, reason = _is_circuit_breaker_triggered(settings, market_data, final_risk_score)
        if tripped:
            approved = False
            decision["controller_reasoning"] = (
                f"Circuit breaker triggered in live mode: {reason}. "
                + decision.get("controller_reasoning", "")
            )
            decision["final_action"] = "hold"
            decision["final_amount"] = 0

    if not approved:
        event = governance_service.record_execution(
            agent_id=request.agent_id,
            token_pair=request.token_pair,
            chain=request.chain.value,
            action="hold",
            amount=0.0,
            approved=False,
            reasoning=decision.get(
                "controller_reasoning", "Trade rejected by multi-agent verification"
            ),
            risk_score=float(decision.get("final_risk_score", 1.0)),
        )
        return TradeResult(
            success=False,
            action=TradeAction.HOLD,
            token_pair=request.token_pair,
            amount=0,
            price=market_data["price"],
            reasoning=decision.get(
                "controller_reasoning", "Trade rejected by multi-agent verification"
            ),
            confidence=0.0,
            timestamp=datetime.utcnow().isoformat(),
            rag_metadata=result.get("rag_metadata", {}),
            governance_metadata={
                **(governance_check or {}),
                "audit_event_hash": event.get("event_hash"),
            },
            x402_metadata=_get_x402_metadata(http_request),
            agent_trace=AgentTrace(
                planner_decision=result.get("planner_decision"),
                verifier_result=result.get("verifier_result"),
                final_decision=decision,
                monitoring_strategy=result.get("monitoring_strategy"),
                adjustment_logic=result.get("adjustment_logic"),
            ),
            risk_metadata=risk_metadata,
        )

    action_map = {
        "buy": TradeAction.BUY,
        "sell": TradeAction.SELL,
        "hold": TradeAction.HOLD,
    }
    action = action_map.get(decision.get("final_action", "hold"), TradeAction.HOLD)

    tx_hash = None
    if request.chain.value == "ethereum" and eth_client.is_connected():
        tx_hash = "0x_simulated_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
    elif request.chain.value == "solana" and sol_client.is_connected():
        tx_hash = "sol_simulated_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")

    event = governance_service.record_execution(
        agent_id=request.agent_id,
        token_pair=request.token_pair,
        chain=request.chain.value,
        action=action.value,
        amount=float(decision.get("final_amount", 0)),
        approved=True,
        reasoning=decision.get("controller_reasoning", ""),
        risk_score=float(decision.get("final_risk_score", 0.0)),
    )

    # Apply position size adjustment from risk assessment
    final_amount = decision.get("final_amount", 0)
    if position_multiplier < 1.0:
        original_amount = final_amount
        final_amount = final_amount * position_multiplier
        decision["controller_reasoning"] = (
            f"[RISK ADJUSTED: Position reduced to {position_multiplier*100:.0f}% due to HIGH risk] "
            + decision.get("controller_reasoning", "")
        )
        logger.info(
            "Position adjusted: %.2f -> %.2f (risk adjustment)",
            original_amount,
            final_amount,
        )
    
    # Store successful assessment for historical tracking
    outcome = "approved" if position_multiplier >= 1.0 else "reduced"
    try:
        risk_storage = get_risk_storage()
        risk_storage.store(
            token_pair=request.token_pair,
            chain=request.chain.value,
            position_size_usd=request.max_position_usd,
            overall_score=risk_assessment.overall_score,
            risk_level=risk_assessment.risk_level.value,
            volatility_risk=risk_assessment.volatility_risk,
            drawdown_risk=risk_assessment.drawdown_risk,
            liquidity_risk=risk_assessment.liquidity_risk,
            onchain_risk=risk_assessment.onchain_risk,
            outcome=outcome,
            position_multiplier=position_multiplier,
            recommendations=risk_assessment.recommendations,
        )
    except Exception as e:
        logger.warning("Failed to store risk assessment: %s", e)
    
    return TradeResult(
        success=True,
        tx_hash=tx_hash,
        action=action,
        token_pair=request.token_pair,
        amount=final_amount,
        price=market_data["price"],
        reasoning=decision.get("controller_reasoning", ""),
        confidence=result.get("planner_decision", {}).get("confidence", 0.0),
        timestamp=datetime.utcnow().isoformat(),
        rag_metadata=result.get("rag_metadata", {}),
        governance_metadata={
            **(governance_check or {}),
            "audit_event_hash": event.get("event_hash"),
        },
        x402_metadata=_get_x402_metadata(http_request),
        agent_trace=AgentTrace(
            planner_decision=result.get("planner_decision"),
            verifier_result=result.get("verifier_result"),
            final_decision=decision,
            monitoring_strategy=result.get("monitoring_strategy"),
            adjustment_logic=result.get("adjustment_logic"),
        ),
        risk_metadata=risk_metadata,
    )


@router.post("/analyze")
async def analyze_market(token_pair: str = "ETH/USDT", chain: str = "ethereum"):
    market_data = get_mock_market_data(token_pair, chain)
    return {
        "market_data": market_data,
        "token_pair": token_pair,
        "chain": chain,
        "x402_metadata": {
            "payment_required": x402_service.enabled,
            "payment_resource": PaymentResource.TRADE_ANALYZE.value if x402_service.enabled else None,
            "price_usd": get_resource_price(PaymentResource.TRADE_ANALYZE) if x402_service.enabled else 0,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Risk Assessment Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/risk/assess", response_model=RiskAssessResult)
async def assess_risk(request: RiskAssessRequest) -> RiskAssessResult:
    """
    Assess trading risk based on market and on-chain data.
    
    Returns a comprehensive risk assessment with:
    - Overall risk score (0-100)
    - Risk level classification (low, moderate, high, critical)
    - Component breakdown (volatility, drawdown, liquidity, on-chain)
    - Actionable recommendations
    
    Safety: This endpoint is used to pre-screen trades before execution.
    In live mode, CRITICAL risk scores should block execution entirely.
    """
    try:
        # Build MarketData from validated request
        market_data = MarketData(
            price=request.price,
            volume_24h=request.volume_24h,
            volatility_24h=request.volatility_24h,
            price_change_24h=request.price_change_24h,
            rsi_14=request.rsi_14,
            macd_signal=request.macd_signal,
            sma_7=request.sma_7,
            sma_14=request.sma_14,
            sma_30=request.sma_30,
            tvl=request.tvl,
            liquidity_depth=request.liquidity_depth,
            slippage_estimate=request.slippage_estimate,
            chain=request.chain,
        )
        
        # Build OnChainData (optional)
        onchain_data: OnChainData | None = None
        if any([
            request.contract_verified is not True,  # Non-default value
            request.audit_status,
            request.contract_age_days,
            request.exploit_history,
            request.governance_decentralized is not True,  # Non-default value
            request.multisig_threshold,
        ]):
            onchain_data = OnChainData(
                contract_verified=request.contract_verified,
                audit_status=request.audit_status,
                contract_age_days=request.contract_age_days,
                exploit_history=request.exploit_history,
                governance_decentralized=request.governance_decentralized,
                multisig_threshold=request.multisig_threshold,
            )
        
        # Run risk assessment
        engine = _get_risk_engine()
        assessment = engine.assess(
            market_data=market_data,
            position_size_usd=request.position_size_usd,
            portfolio_value_usd=request.portfolio_value_usd,
            onchain_data=onchain_data,
            token_pair=request.token_pair,
            chain=request.chain,
        )
        
        return RiskAssessResult(**assessment.to_dict())
        
    except Exception as e:
        logger.error("Risk assessment failed: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Risk assessment error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Risk Metrics & Calibration Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/risk/metrics", response_model=RiskMetricsResult)
async def get_risk_metrics(period_days: int = 30) -> RiskMetricsResult:
    """
    Get risk-adjusted performance metrics from historical data.
    
    Returns:
    - Total trades, winning/losing counts
    - Win rate overall and by risk level
    - Average risk score
    - Sharpe ratio (if sufficient data)
    - Maximum drawdown estimate
    - Risk-adjusted return
    - Average position multiplier
    - Blocked trades count
    
    Use this endpoint to monitor trading performance and risk calibration.
    """
    try:
        storage = get_risk_storage()
        calculator = RiskMetricsCalculator(storage)
        metrics = calculator.calculate_metrics(period_days=period_days)
        
        return RiskMetricsResult(
            total_trades=metrics.total_trades,
            winning_trades=metrics.winning_trades,
            losing_trades=metrics.losing_trades,
            win_rate=metrics.win_rate,
            avg_risk_score=metrics.avg_risk_score,
            sharpe_ratio=metrics.sharpe_ratio,
            max_drawdown=metrics.max_drawdown,
            risk_adjusted_return=metrics.risk_adjusted_return,
            win_rate_by_level=metrics.win_rate_by_level,
            avg_position_multiplier=metrics.avg_position_multiplier,
            blocked_trades=metrics.blocked_trades,
            period_days=metrics.period_days,
        )
        
    except Exception as e:
        logger.error("Risk metrics calculation failed: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Risk metrics error: {str(e)}"
        )


@router.get("/risk/calibrate", response_model=RiskCalibrationResult)
async def calibrate_risk_weights() -> RiskCalibrationResult:
    """
    Analyze historical risk scores to suggest weight adjustments.
    
    This endpoint helps calibrate the RiskEngine by analyzing which
    risk components are driving high scores and suggesting weight
    adjustments to improve risk detection.
    
    Returns:
    - current_weights: Current risk component weights
    - suggested_weights: Adjusted weights based on historical data
    - average_component_scores: Average scores by component
    - reasoning: Explanation for suggestions
    
    Use this to fine-tune the risk engine for better performance.
    """
    try:
        storage = get_risk_storage()
        calibrator = RiskCalibrator(storage)
        result = calibrator.suggest_weight_adjustments()
        
        return RiskCalibrationResult(
            current_weights=result["current_weights"],
            suggested_weights=result["suggested_weights"],
            average_component_scores=result["average_component_scores"],
            reasoning=result["reasoning"],
        )
        
    except Exception as e:
        logger.error("Risk calibration failed: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Risk calibration error: {str(e)}"
        )
