# Risk Management System

Comprehensive risk assessment and management for blockchain trading decisions.

## Overview

The Risk Management System provides multi-factor risk assessment before any trade execution, ensuring safe and predictable behavior in both paper and live trading modes.

```
Trade Request → Risk Assessment → Decision
                    ↓
         ┌─────────────────────────────────────┐
         │ LOW (0-25):    Execute normally     │
         │ MODERATE (26-50): Execute normally  │
         │ HIGH (51-75):   Position reduced 50%│
         │ CRITICAL (76-100): BLOCKED          │
         └─────────────────────────────────────┘
```

## Architecture

```
backend/app/risk/
├── __init__.py           # Module exports
├── risk_engine.py        # Core RiskEngine class
├── risk_storage.py       # SQLite historical tracking
├── risk_metrics.py       # Performance metrics & calibration
└── README.md             # This file
```

## Components

### 1. RiskEngine (`risk_engine.py`)

Multi-factor risk assessment engine.

**Risk Components (Weights):**
| Component | Weight | Description |
|-----------|--------|-------------|
| Volatility | 30% | Price fluctuation intensity, RSI extremes |
| Drawdown | 25% | Trend deviation, SMA distance, MACD signal |
| Liquidity | 25% | Volume, TVL, slippage estimates |
| On-Chain | 20% | Contract verification, audits, exploit history |

**Risk Levels:**
| Level | Score | Action |
|-------|-------|--------|
| LOW | 0-25 | Execute normally (100% position) |
| MODERATE | 26-50 | Execute normally (100% position) |
| HIGH | 51-75 | Position reduced to 50-90% (dynamic) |
| CRITICAL | 76-100 | **BLOCKED** - Trade rejected |

**Usage:**
```python
from app.risk import RiskEngine, MarketData, OnChainData

engine = RiskEngine()

# Create market data
market = MarketData(
    price=3200.0,
    volume_24h=5_000_000_000,
    volatility_24h=45.0,
    rsi_14=55.0,
    chain="ethereum",
)

# Assess risk
assessment = engine.assess(
    market_data=market,
    position_size_usd=1000,
    token_pair="ETH/USDT",
)

print(f"Risk Score: {assessment.overall_score}")
print(f"Risk Level: {assessment.risk_level.value}")
print(f"Recommendations: {assessment.recommendations}")

# Get position multiplier (for HIGH risk)
multiplier = engine.get_position_multiplier(assessment.overall_score)
# Returns: 1.0 (LOW/MODERATE), 0.5-0.9 (HIGH), 0.0 (CRITICAL)
```

**Dynamic Position Sizing:**
```python
# Score-based position reduction for HIGH risk
# 51 → 90%, 75 → 50% (linear interpolation)
def get_position_multiplier(score: float) -> float:
    if score >= 76: return 0.0      # CRITICAL: blocked
    if score >= 51: return 0.90 - (score - 51) * (0.40 / 24)
    return 1.0                       # LOW/MODERATE: full position
```

### 2. RiskStorage (`risk_storage.py`)

SQLite-based persistence for historical risk assessments.

**Usage:**
```python
from app.risk import get_risk_storage

storage = get_risk_storage()

# Store assessment
storage.store(
    token_pair="ETH/USDT",
    chain="ethereum",
    position_size_usd=1000,
    overall_score=25.5,
    risk_level="low",
    volatility_risk=12.0,
    drawdown_risk=8.0,
    liquidity_risk=5.0,
    onchain_risk=10.0,
    outcome="approved",  # "approved", "reduced", or "blocked"
    position_multiplier=1.0,
    recommendations=["Low risk profile"],
)

# Query recent assessments
recent = storage.get_recent(limit=100)

# Get statistics
stats = storage.get_statistics()
# {
#   "total_assessments": 1500,
#   "by_risk_level": {"low": 800, "moderate": 500, "high": 180, "critical": 20},
#   "by_outcome": {"approved": 1200, "reduced": 280, "blocked": 20},
#   "average_scores": {"overall": 28.5, "volatility": 22.0, ...}
# }

# Get trends
trends = storage.get_trends(days=7)
```

### 3. RiskMetricsCalculator (`risk_metrics.py`)

Performance metrics and calibration tools.

**RiskMetrics:**
- Total trades, winning/losing counts
- Win rate overall and by risk level
- Sharpe ratio (annualized)
- Maximum drawdown estimate
- Risk-adjusted return
- Average position multiplier
- Blocked trades count

**Usage:**
```python
from app.risk import RiskMetricsCalculator, get_risk_storage

storage = get_risk_storage()
calculator = RiskMetricsCalculator(storage)

# Calculate metrics
metrics = calculator.calculate_metrics(period_days=30)

print(f"Win Rate: {metrics.win_rate * 100:.1f}%")
print(f"Sharpe Ratio: {metrics.sharpe_ratio}")
print(f"Max Drawdown: {metrics.max_drawdown * 100:.1f}%")
print(f"Win Rate by Level: {metrics.win_rate_by_level}")

# Generate report
report = calculator.generate_report(metrics)
print(report)
```

### 4. RiskCalibrator (`risk_metrics.py`)

Analyze historical data to suggest weight adjustments.

```python
from app.risk import RiskCalibrator

calibrator = RiskCalibrator(storage)
result = calibrator.suggest_weight_adjustments()

# {
#   "current_weights": {"volatility": 0.30, "drawdown": 0.25, ...},
#   "suggested_weights": {"volatility": 0.35, ...},
#   "average_component_scores": {"volatility": 42.5, ...},
#   "reasoning": ["Volatility scores high - increase weight for better detection"]
# }
```

### 5. RiskAlerter (`risk_metrics.py`)

Monitor and alert on risk conditions.

```python
from app.risk import RiskAlerter

alerter = RiskAlerter(alert_threshold=70.0, window_size=10)

# Check alerts after each assessment
alerts = alerter.check_alerts(
    current_score=assessment.overall_score,
    risk_level=assessment.risk_level.value,
)

for alert in alerts:
    # alert = {"level": "CRITICAL", "message": "...", "action": "..."}
    print(f"[{alert['level']}] {alert['message']}")
```

## API Endpoints

### POST /trading/risk/assess

Assess trading risk for a given market state.

**Request:**
```json
{
  "price": 3200.0,
  "volume_24h": 5000000000,
  "token_pair": "ETH/USDT",
  "chain": "ethereum",
  "position_size_usd": 1000.0,
  "volatility_24h": 45.0,
  "rsi_14": 55.0,
  "contract_verified": true,
  "audit_status": "audited"
}
```

**Response:**
```json
{
  "overall_score": 25.5,
  "risk_level": "low",
  "volatility_risk": 22.0,
  "drawdown_risk": 15.0,
  "liquidity_risk": 10.0,
  "onchain_risk": 8.0,
  "factors": {...},
  "recommendations": ["✅ Low risk profile. Trade execution within safe parameters."],
  "timestamp": "2026-04-20T17:30:00.000Z"
}
```

### GET /trading/risk/metrics

Get risk-adjusted performance metrics.

**Query Params:** `period_days` (default: 30)

**Response:**
```json
{
  "total_trades": 500,
  "winning_trades": 320,
  "losing_trades": 180,
  "win_rate": 0.64,
  "avg_risk_score": 28.5,
  "sharpe_ratio": 1.45,
  "max_drawdown": 0.12,
  "win_rate_by_level": {"low": 0.72, "moderate": 0.58, "high": 0.35},
  "blocked_trades": 15
}
```

### GET /trading/risk/calibrate

Get weight calibration suggestions.

**Response:**
```json
{
  "current_weights": {"volatility": 0.30, "drawdown": 0.25, "liquidity": 0.25, "onchain": 0.20},
  "suggested_weights": {"volatility": 0.35, ...},
  "average_component_scores": {"volatility": 42.5, ...},
  "reasoning": ["Volatility scores high - increase weight for better detection"]
}
```

## Integration Flow

```
1. Trade Request Received
         ↓
2. Risk Assessment (RiskEngine.assess)
         ↓
3. ┌─────────────────────────────────────┐
   │ CRITICAL? → BLOCK, store, return     │
   │ HIGH? → Reduce position, store       │
   │ MODERATE/LOW? → Proceed, store       │
   └─────────────────────────────────────┘
         ↓
4. Pass risk_assessment to orchestrator
         ↓
5. Execute trade with position adjustment
         ↓
6. Return TradeResult with risk_metadata
         ↓
7. Frontend displays RiskPanel
```

## Solana-Specific Enhancements

Additional risk factors for Solana trades:

- **SPL Token Verification**: Extra penalty for unverified tokens
- **Program Upgrade Authority**: Centralized upgrade risk
- **Contract Age Penalties**: Higher penalties for new programs (< 7 days)
- **DeFi Protocol Risks**: Base complexity risk for Raydium/Jupiter

```python
# Solana-specific risk calculation
def _calculate_solana_specific_risk(self, data: OnChainData) -> float:
    solana_risk = 0.0
    
    if not data.contract_verified:
        solana_risk += 15  # Extra penalty on Solana
    
    if not data.governance_decentralized:
        solana_risk += 10  # Centralized upgrade authority
    
    if data.contract_age_days < 7:
        solana_risk += 20  # Very new programs are risky
    
    solana_risk += 5  # Base Solana DeFi complexity
    
    return solana_risk
```

## Testing

Run all risk tests:
```bash
cd backend
pytest tests/test_risk_engine.py tests/test_risk_integration.py tests/test_full_trade_flow.py -v
```

## Customization

### Adjust Component Weights

```python
# Conservative: Emphasize on-chain safety
conservative_engine = RiskEngine(weights={
    "volatility": 0.20,
    "drawdown": 0.20,
    "liquidity": 0.20,
    "onchain": 0.40,  # Higher weight on contract safety
})

# Aggressive: Focus on market timing
aggressive_engine = RiskEngine(weights={
    "volatility": 0.40,  # Higher weight on volatility
    "drawdown": 0.30,
    "liquidity": 0.20,
    "onchain": 0.10,
})
```

### Custom Storage Path

```python
# Use custom database path
storage = RiskStorage(db_path="./data/custom_risk.db")
```

## Safety Guarantees

1. **Fail-Closed Design**: CRITICAL risk ALWAYS blocks execution
2. **Position Limits**: HIGH risk automatically reduces exposure
3. **Transparent**: Full risk breakdown in every TradeResult
4. **Auditable**: All assessments logged with timestamp
5. **Historical Tracking**: SQLite persistence for analysis
6. **Calibration Support**: Data-driven weight tuning

## Frontend Integration

### RiskPanel Component

Located in `TradingDashboard.jsx`, displays:
- Color-coded risk level badge
- Overall score (0-100)
- Component score bars (volatility, drawdown, liquidity, on-chain)
- Recommendations list

### Risk Dashboard Page

Located at `/risk`, shows:
- Performance metrics (Sharpe, win rate, drawdown)
- Win rate by risk level
- Calibration suggestions
- Historical trends

## Files Reference

| File | Purpose |
|------|---------|
| `risk_engine.py` | Core RiskEngine class, assessment logic |
| `risk_storage.py` | SQLite persistence for history |
| `risk_metrics.py` | Metrics calculator, calibrator, alerter |
| `__init__.py` | Module exports |
| `README.md` | This documentation |

## License

Part of the AI Agent Trading System.