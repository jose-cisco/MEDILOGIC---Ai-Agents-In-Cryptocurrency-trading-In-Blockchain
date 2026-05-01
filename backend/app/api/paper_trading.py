"""
Paper Trading API — Forward Testing with Virtual Money
=======================================================

This module provides REST API endpoints for paper trading (forward testing).

Paper trading runs the AI agent on REAL-TIME market data with VIRTUAL money.
This is the CRITICAL validation step between backtesting and live trading.

Key Differences:
- Backtesting: Historical data, very fast, low realism
- Paper Trading: Real-time data, actual waiting, much higher realism
- Live Trading: Real-time data, real money, full risk

Use paper trading AFTER backtesting shows good results, BEFORE live trading.
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging

from app.backtesting.paper_trading import (
    get_paper_trading_engine,
    PaperTradingState,
    PaperOrderType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/paper", tags=["Paper Trading"])


# ─── Request/Response Models ─────────────────────────────────────────────────

class PaperSessionStartRequest(BaseModel):
    """Request to start a new paper trading session."""
    initial_capital: float = Field(default=10000.0, description="Initial virtual capital in USD")
    slippage_pct: float = Field(default=0.001, description="Simulated slippage percentage (default 0.1%)")
    fee_pct: float = Field(default=0.001, description="Simulated trading fee percentage (default 0.1%)")
    simulate_latency: bool = Field(default=True, description="Whether to simulate AI decision and execution delays")
    decision_delay_ms: float = Field(default=500.0, description="Simulated AI decision delay in milliseconds")
    execution_delay_ms: float = Field(default=200.0, description="Simulated network execution delay in milliseconds")


class PaperOrderRequest(BaseModel):
    """Request to submit a paper trading order."""
    token_pair: str = Field(default="ETH/USDT", description="Trading pair")
    chain: str = Field(default="ethereum", description="Blockchain network")
    side: str = Field(description="Order side: 'buy' or 'sell'")
    amount: float = Field(description="USD amount for buy, token amount for sell")
    order_type: str = Field(default="market", description="Order type: 'market', 'limit', 'stop_loss', 'take_profit'")
    price: Optional[float] = Field(default=None, description="Limit price (for limit orders)")
    reasoning: str = Field(default="", description="Agent's reasoning for the trade")
    confidence: float = Field(default=0.5, description="Agent's confidence (0-1)")


class PaperSessionStatusResponse(BaseModel):
    """Response for session status query."""
    session_id: str
    state: str
    start_time: str
    current_capital: float
    positions: dict
    metrics: dict


class PaperOrderResponse(BaseModel):
    """Response for order submission."""
    success: bool
    order_id: Optional[str] = None
    status: Optional[str] = None
    side: Optional[str] = None
    token_pair: Optional[str] = None
    amount: Optional[float] = None
    market_price: Optional[float] = None
    fill_price: Optional[float] = None
    slippage_pct: Optional[float] = None
    slippage_usd: Optional[float] = None
    fee_usd: Optional[float] = None
    decision_time_ms: Optional[float] = None
    execution_delay_ms: Optional[float] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


# ─── API Endpoints ─────────────────────────────────────────────────────────

@router.post("/session/start")
async def start_paper_session(request: PaperSessionStartRequest):
    """
    Start a new paper trading session.
    
    This initializes a virtual trading account with:
    - Specified initial capital
    - Configured slippage and fee simulation
    - Optional latency simulation for realistic execution
    
    Paper trading uses REAL-TIME market data but VIRTUAL money.
    No real funds are at risk.
    
    **When to use:** After backtesting shows good results, before live trading.
    
    **Advantages over backtesting:**
    - Tests real-time data handling
    - Reveals slippage and execution delays
    - Tests agent decision speed under real conditions
    - Shows realistic performance metrics
    """
    engine = get_paper_trading_engine(initial_capital=request.initial_capital)
    
    # Configure simulation parameters
    engine.session.config["slippage_pct"] = request.slippage_pct
    engine.session.config["fee_pct"] = request.fee_pct
    engine.session.config["simulate_latency"] = request.simulate_latency
    engine.session.config["decision_delay_ms"] = request.decision_delay_ms
    engine.session.config["execution_delay_ms"] = request.execution_delay_ms
    
    result = await engine.start_session()
    
    if result.get("success"):
        logger.info(
            "Paper trading session started: %s | Capital: $%.2f | Slippage: %.2f%% | Fee: %.2f%%",
            result["session_id"],
            request.initial_capital,
            request.slippage_pct * 100,
            request.fee_pct * 100,
        )
    else:
        logger.warning("Failed to start paper session: %s", result.get("error"))
    
    return result


@router.post("/session/stop")
async def stop_paper_session():
    """
    Stop the current paper trading session.
    
    Returns comprehensive performance metrics:
    - Final PnL (absolute and percentage)
    - Win/loss statistics
    - Maximum drawdown
    - Average decision and execution latency
    - Session duration
    
    **Use this to:**
    - End a forward testing session
    - Review performance before going live
    - Compare with backtesting results
    """
    engine = get_paper_trading_engine()
    result = await engine.stop_session()
    
    if result.get("success"):
        metrics = result.get("metrics", {})
        logger.info(
            "Paper trading session ended: %s | PnL: $%.2f (%.2f%%) | Win Rate: %.1f%%",
            result.get("session_id"),
            metrics.get("total_pnl_usd", 0),
            metrics.get("total_pnl_pct", 0),
            metrics.get("win_rate_pct", 0),
        )
    
    return result


@router.get("/session/status")
async def get_paper_session_status():
    """
    Get current paper trading session status.
    
    Returns:
    - Session ID and state
    - Current capital
    - Open positions with unrealized PnL
    - Performance metrics to date
    """
    engine = get_paper_trading_engine()
    status = await engine.get_session_status()
    return status


@router.post("/order")
async def submit_paper_order(request: PaperOrderRequest):
    """
    Submit a paper trading order.
    
    This simulates:
    1. Real-time price fetching from CoinGecko
    2. AI agent decision time (configurable delay)
    3. Network latency to exchange (configurable delay)
    4. Realistic slippage based on order size
    5. Trading fees
    
    **Request:**
    - token_pair: e.g., "ETH/USDT"
    - side: "buy" or "sell"
    - amount: USD value for buy orders, token amount for sell
    - order_type: "market" (more types coming soon)
    - reasoning: Agent's explanation for the trade
    - confidence: Agent's confidence (0-1)
    
    **Response includes:**
    - Fill price (with slippage)
    - Slippage amount and percentage
    - Trading fee
    - Decision and execution latency
    
    This reveals real-world execution challenges that backtesting misses.
    """
    engine = get_paper_trading_engine()
    
    # Validate order type
    try:
        order_type = PaperOrderType(request.order_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid order_type: {request.order_type}. Valid options: market, limit, stop_loss, take_profit"
        )
    
    # Validate side
    if request.side.lower() not in ("buy", "sell"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid side: {request.side}. Must be 'buy' or 'sell'"
        )
    
    result = await engine.submit_order(
        token_pair=request.token_pair,
        chain=request.chain,
        side=request.side.lower(),
        amount=request.amount,
        order_type=order_type,
        price=request.price,
        reasoning=request.reasoning,
        confidence=request.confidence,
    )
    
    if not result.get("success"):
        logger.warning("Paper order failed: %s", result.get("error"))
    
    return result


@router.post("/positions/update")
async def update_paper_positions():
    """
    Update all position values with current real-time prices.
    
    Call this periodically to track unrealized PnL on open positions.
    Fetches live prices from CoinGecko for each held token pair.
    
    **Use to:**
    - Track unrealized PnL during active session
    - Monitor position values in real-time
    - Get accurate equity curves
    """
    engine = get_paper_trading_engine()
    result = await engine.update_position_values()
    return result


@router.get("/price/{token_pair}")
async def get_real_time_price(token_pair: str):
    """
    Get real-time market price for a token pair.
    
    This fetches LIVE prices from CoinGecko, which is what makes
    paper trading "forward testing" vs backtesting's historical data.
    
    **Supported pairs:**
    - ETH/USDT
    - ETH/USDC
    - SOL/USDT
    - BTC/USDT
    - BTC/USDC
    """
    engine = get_paper_trading_engine()
    result = await engine.get_real_time_price(token_pair)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch price for {token_pair}: {result.get('error')}"
        )
    
    return result


@router.get("/compare/backtesting-vs-paper")
async def compare_backtesting_vs_paper():
    """
    Get educational comparison between backtesting and paper trading.
    
    Returns a detailed comparison showing:
    - Key differences
    - When to use each
    - Advantages and limitations
    - Recommended workflow
    """
    return {
        "comparison": {
            "backtesting": {
                "data_used": "Historical (past)",
                "speed": "Very fast (years in minutes)",
                "realism": "Low",
                "risk": "None",
                "best_for": "Strategy development & optimization",
                "limitations": [
                    "Overfitting risk - model can memorize historical patterns",
                    "Doesn't account for real-world slippage",
                    "No trading fees or liquidity problems",
                    "No emotional or execution delays"
                ]
            },
            "paper_trading": {
                "data_used": "Live / real-time",
                "speed": "Real-time (takes days/weeks)",
                "realism": "Much higher",
                "risk": "None (virtual money)",
                "best_for": "Final validation before live trading",
                "advantages": [
                    "Tests current market conditions",
                    "Reveals real slippage and API delays",
                    "Tests agent decision speed",
                    "Much closer to live trading performance"
                ],
                "limitations": [
                    "Still not 100% real (no emotional pressure)",
                    "Takes real time to complete"
                ]
            },
            "live_trading": {
                "data_used": "Live / real-time",
                "speed": "Real-time",
                "realism": "Full",
                "risk": "Real capital at risk",
                "best_for": "Production deployment",
                "requirements": [
                    "Backtesting shows positive results",
                    "Paper trading validates performance",
                    "Risk management in place",
                    "Capital ready to deploy"
                ]
            }
        },
        "recommended_workflow": [
            {
                "step": 1,
                "name": "Backtesting",
                "description": "Test strategy on historical data",
                "duration": "Minutes to hours",
                "success_criteria": "Positive returns, acceptable drawdown"
            },
            {
                "step": 2,
                "name": "Paper Trading",
                "description": "Validate on real-time data with virtual money",
                "duration": "Days to weeks",
                "success_criteria": "Consistent performance, realistic slippage acceptable"
            },
            {
                "step": 3,
                "name": "Live Trading",
                "description": "Deploy with real capital",
                "duration": "Ongoing",
                "success_criteria": "Monitor and adjust continuously"
            }
        ]
    }


@router.get("/health")
async def paper_trading_health():
    """Health check for paper trading engine."""
    engine = get_paper_trading_engine()
    return {
        "status": "healthy",
        "session_state": engine.session.state.value,
        "session_id": engine.session.session_id,
    }