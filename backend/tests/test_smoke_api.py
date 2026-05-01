import hashlib
import hmac
import time
from dataclasses import dataclass, field
from types import SimpleNamespace
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

from app.main import create_app
import app.api.trading as trading_api
import app.api.backtest as backtest_api


@dataclass
class DummyMetrics:
    initial_capital: float = 10000.0
    final_capital: float = 10300.0
    total_return_pct: float = 3.0
    sharpe_ratio: float = 1.1
    max_drawdown_pct: float = 4.2
    win_rate: float = 62.5
    total_trades: int = 8
    winning_trades: int = 5
    losing_trades: int = 3
    avg_trade_return_pct: float = 0.4
    profit_factor: float = 1.7
    trades: list = field(
        default_factory=lambda: [
            {
                "date": "2024-01-02",
                "action": "buy",
                "amount_usd": 250.0,
                "price": 2100.0,
                "reasoning": "smoke test",
                "confidence": 0.7,
                "portfolio_value": 10000.0,
            }
        ]
    )


def test_status_system_smoke():
    app = create_app()
    client = TestClient(app)
    res = client.get("/api/v1/status/system")
    assert res.status_code == 200
    payload = res.json()
    assert "name" in payload
    assert "llm" in payload
    assert payload["trading_mode"] in {"paper", "live"}


def test_trading_execute_smoke(monkeypatch):
    app = create_app()
    client = TestClient(app)

    async def fake_run(prompt: str, token_pair: str, chain: str, market_data: dict, **kwargs):
        return {
            "final_decision": {
                "approved": True,
                "final_action": "buy",
                "final_amount": 100.0,
                "controller_reasoning": "smoke-approved",
            },
            "planner_decision": {"confidence": 0.73},
            "rag_metadata": {"result_count": 0, "sources": []},
        }

    monkeypatch.setattr(trading_api.orchestrator, "run", fake_run)
    monkeypatch.setattr(trading_api.eth_client, "is_connected", lambda: False)
    monkeypatch.setattr(trading_api.sol_client, "is_connected", lambda: False)

    res = client.post(
        "/api/v1/trading/execute",
        json={
            "prompt": "smoke test prompt",
            "chain": "ethereum",
            "token_pair": "ETH/USDT",
            "max_position_usd": 1000,
            "agent_id": "default-trader",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["token_pair"] == "ETH/USDT"
    assert payload["action"] in {"buy", "sell", "hold"}
    assert "reasoning" in payload
    assert "governance_metadata" in payload


def test_backtest_run_smoke(monkeypatch):
    app = create_app()
    client = TestClient(app)

    monkeypatch.setattr(
        backtest_api.engine,
        "run_backtest",
        lambda **_: DummyMetrics(),
    )

    res = client.post(
        "/api/v1/backtest/run",
        json={
            "strategy": "momentum smoke",
            "token_pair": "ETH/USDT",
            "start_date": "2024-01-01",
            "end_date": "2024-02-01",
            "initial_capital": 10000.0,
            "chain": "ethereum",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["strategy"] == "momentum smoke"
    assert "final_capital" in payload
    assert isinstance(payload["trades"], list)


def test_trading_execute_live_requires_signed_headers(monkeypatch):
    app = create_app()
    client = TestClient(app)

    async def fake_run(prompt: str, token_pair: str, chain: str, market_data: dict, **kwargs):
        return {
            "final_decision": {
                "approved": True,
                "final_action": "buy",
                "final_amount": 10.0,
                "controller_reasoning": "live-ok",
            },
            "planner_decision": {"confidence": 0.8},
            "rag_metadata": {},
        }

    settings = SimpleNamespace(
        TRADING_MODE="live",
        LIVE_TRADING_ENABLED=True,
        LIVE_GUARD_SECRET="unit-test-secret",
        LIVE_GUARD_MAX_SKEW_SECONDS=120,
    )

    monkeypatch.setattr(trading_api, "get_settings", lambda: settings)
    monkeypatch.setattr(trading_api.orchestrator, "run", fake_run)
    monkeypatch.setattr(trading_api.eth_client, "is_connected", lambda: False)
    monkeypatch.setattr(trading_api.sol_client, "is_connected", lambda: False)
    trading_api._SEEN_NONCES.clear()

    payload = {
        "prompt": "live smoke",
        "chain": "ethereum",
        "token_pair": "ETH/USDT",
        "max_position_usd": 1000,
        "agent_id": "default-trader",
    }

    # Missing signature headers -> blocked.
    blocked = client.post("/api/v1/trading/execute", json=payload)
    assert blocked.status_code == 403

    nonce = "nonce-live-1"
    ts = int(time.time())
    sig = hmac.new(
        settings.LIVE_GUARD_SECRET.encode("utf-8"),
        f"{nonce}:{ts}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "X-Live-Nonce": nonce,
        "X-Live-Timestamp": str(ts),
        "X-Live-Signature": sig,
    }
    ok = client.post("/api/v1/trading/execute", json=payload, headers=headers)
    assert ok.status_code == 200


def test_governance_blocks_high_semantic_signal_prompt(monkeypatch):
    app = create_app()
    client = TestClient(app)

    settings = SimpleNamespace(
        TRADING_MODE="paper",
        LIVE_TRADING_ENABLED=False,
        ENABLE_AGENT_GOVERNANCE=True,
        SEMANTIC_SIGNAL_BLOCK_THRESHOLD=2,
    )

    monkeypatch.setattr(trading_api, "get_settings", lambda: settings)

    blocked = client.post(
        "/api/v1/trading/execute",
        json={
            "prompt": (
                "Use delayed activation and staged execution. "
                "Then trigger a phase transition for coordinated action."
            ),
            "chain": "ethereum",
            "token_pair": "ETH/USDT",
            "max_position_usd": 1000,
            "agent_id": "default-trader",
        },
    )
    assert blocked.status_code == 200
    payload = blocked.json()
    assert payload["success"] is False
    assert payload["action"] == "hold"
    assert "Blocked by governance policy" in payload["reasoning"]


def test_backtest_run_rules_regression_unmocked():
    """
    Regression guard: ensure /backtest/run-rules works without monkeypatching
    and returns structurally valid data from the safe engine path.
    """
    app = create_app()
    client = TestClient(app)

    res = client.post(
        "/api/v1/backtest/run-rules",
        params={
            "token_pair": "ETH/USDT",
            "start_date": "2024-01-01",
            "end_date": "2024-03-01",
            "initial_capital": 10000.0,
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["strategy"] == "rules-based"
    assert payload["token_pair"] == "ETH/USDT"
    assert payload["data_source"] in {"dataset", "ccxt", "synthetic"}
    assert isinstance(payload["trades"], list)
    assert len(payload["trades"]) > 0
    first = payload["trades"][0]
    for key in ["date", "action", "amount_usd", "price", "reasoning", "confidence", "portfolio_value"]:
        assert key in first


def test_live_requires_agent_signature_when_enabled(monkeypatch):
    app = create_app()
    client = TestClient(app)

    ephemeral = Account.create()
    trading_api.governance_service.register_agent(
        agent_id="sig-agent",
        did="did:ethr:polygon:sig-agent",
        public_key=ephemeral.address,
    )

    async def fake_run(prompt: str, token_pair: str, chain: str, market_data: dict, **kwargs):
        return {
            "final_decision": {
                "approved": True,
                "final_action": "buy",
                "final_amount": 10.0,
                "controller_reasoning": "live-ok",
                "final_risk_score": 0.2,
            },
            "planner_decision": {"confidence": 0.8},
            "rag_metadata": {},
        }

    settings = SimpleNamespace(
        TRADING_MODE="live",
        LIVE_TRADING_ENABLED=True,
        LIVE_GUARD_SECRET="unit-test-secret",
        LIVE_GUARD_MAX_SKEW_SECONDS=120,
        LIVE_REQUIRE_AGENT_SIGNATURE=True,
        LIVE_MAX_MARKET_DATA_AGE_SECONDS=180,
        LIVE_CIRCUIT_BREAKER_RISK_THRESHOLD=0.75,
        LIVE_CIRCUIT_BREAKER_VOLATILITY_PCT=0.08,
        ENABLE_AGENT_GOVERNANCE=True,
        SEMANTIC_SIGNAL_BLOCK_THRESHOLD=2,
    )

    monkeypatch.setattr(trading_api, "get_settings", lambda: settings)
    monkeypatch.setattr(trading_api.orchestrator, "run", fake_run)
    monkeypatch.setattr(trading_api.eth_client, "is_connected", lambda: False)
    monkeypatch.setattr(trading_api.sol_client, "is_connected", lambda: False)
    trading_api._SEEN_NONCES.clear()

    ts = int(time.time())
    nonce = "nonce-live-sig"
    header_sig = hmac.new(
        settings.LIVE_GUARD_SECRET.encode("utf-8"),
        f"{nonce}:{ts}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "X-Live-Nonce": nonce,
        "X-Live-Timestamp": str(ts),
        "X-Live-Signature": header_sig,
    }

    # Missing DID/signature payload -> blocked.
    blocked = client.post(
        "/api/v1/trading/execute",
        json={
            "prompt": "live signed test",
            "chain": "ethereum",
            "token_pair": "ETH/USDT",
            "max_position_usd": 1000,
            "agent_id": "sig-agent",
        },
        headers=headers,
    )
    assert blocked.status_code == 403

    req_nonce = "req-nonce-1"
    req_ts = int(time.time())
    prompt = "live signed test"
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    sign_payload = (
        f"sig-agent:did:ethr:polygon:sig-agent:{req_nonce}:{req_ts}:"
        f"ETH/USDT:ethereum:{1000.0:.8f}:{prompt_hash}"
    )
    signature = Account.sign_message(
        encode_defunct(text=sign_payload),
        ephemeral.key,
    ).signature.hex()
    if not signature.startswith("0x"):
        signature = "0x" + signature

    # Fresh headers because header nonce is replay-protected.
    ts2 = int(time.time())
    nonce2 = "nonce-live-sig-2"
    header_sig2 = hmac.new(
        settings.LIVE_GUARD_SECRET.encode("utf-8"),
        f"{nonce2}:{ts2}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    headers2 = {
        "X-Live-Nonce": nonce2,
        "X-Live-Timestamp": str(ts2),
        "X-Live-Signature": header_sig2,
    }

    ok = client.post(
        "/api/v1/trading/execute",
        json={
            "prompt": prompt,
            "chain": "ethereum",
            "token_pair": "ETH/USDT",
            "max_position_usd": 1000,
            "agent_id": "sig-agent",
            "did": "did:ethr:polygon:sig-agent",
            "request_nonce": req_nonce,
            "request_timestamp": req_ts,
            "agent_signature": signature,
        },
        headers=headers2,
    )
    assert ok.status_code == 200
