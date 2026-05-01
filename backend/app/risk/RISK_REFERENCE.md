# Risk System Reference Guide

**Quick reference for the AI Agent Trading System's Risk Management**

---

## Risk Levels at a Glance

| Level | Score | Position | Action |
|-------|-------|----------|--------|
| 🟢 LOW | 0-25 | 100% | Execute normally |
| 🔵 MODERATE | 26-50 | 100% | Execute normally |
| 🟡 HIGH | 51-75 | 50-90% | Reduced position |
| 🔴 CRITICAL | 76-100 | **BLOCKED** | Trade rejected |

---

## Risk Components (Weights)

| Component | Weight | What It Measures |
|-----------|--------|-----------------|
| Volatility | 30% | Price swings, RSI extremes |
| Drawdown | 25% | Trend deviation, SMA distance |
| Liquidity | 25% | Volume, TVL, slippage |
| On-Chain | 20% | Contract verification, audits |

---

## API Endpoints

### POST /trading/risk/assess
Assess trading risk before execution.
```bash
curl -X POST /api/v1/trading/risk/assess \
  -H "Content-Type: application/json" \
  -d '{
    "price": 3200.0,
    "volume_24h": 5000000000,
    "token_pair": "ETH/USDT",
    "chain": "ethereum"
  }'
```

### GET /trading/risk/metrics
Get historical performance metrics.
```bash
curl /api/v1/trading/risk/metrics?period_days=30
```

### GET /trading/risk/calibrate
Get weight calibration suggestions.
```bash
curl /api/v1/trading/risk/calibrate
```

---

## Quick Integration

```python
from app.risk import RiskEngine, MarketData

engine = RiskEngine()
assessment = engine.assess(
    market_data=MarketData(price=3200, volume_24h=5e9, chain="ethereum"),
    position_size_usd=1000,
    token_pair="ETH/USDT",
)

if assessment.risk_level.value == "critical":
    print("BLOCKED: Risk too high")
elif assessment.risk_level.value == "high":
    multiplier = engine.get_position_multiplier(assessment.overall_score)
    print(f"REDUCED: Position at {multiplier*100}%")
else:
    print("APPROVED: Full position")
```

---

## Frontend Components

### RiskPanel (TradingDashboard)
- Shows real-time risk assessment
- Color-coded risk level badge
- Component score breakdown

### RiskDashboardPage (/risk)
- Historical metrics & trends
- Win rate by risk level
- Calibration suggestions

---

## Data Flow

```
User Request → RiskEngine.assess()
                      ↓
              ┌──────────────────┐
              │ CRITICAL? BLOCK   │
              │ HIGH? Reduce 50%  │
              │ MODERATE/LOW? OK  │
              └──────────────────┘
                      ↓
              RiskStorage.store()
                      ↓
              Return risk_metadata
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `risk_engine.py` | Core assessment logic |
| `risk_storage.py` | SQLite persistence |
| `risk_metrics.py` | Metrics & calibration |
| `trading.py` | API integration |

---

## Testing

```bash
cd backend
pytest tests/test_risk_engine.py tests/test_risk_integration.py -v
```

---

## Safety Features

1. **Fail-Closed**: CRITICAL always blocks
2. **Historical Tracking**: All assessments logged
3. **Dynamic Sizing**: Position reduced for HIGH risk
4. **Alerting**: Warnings for consistent high risk
5. **Transparency**: Full breakdown in every response