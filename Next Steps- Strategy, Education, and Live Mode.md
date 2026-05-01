# Next Steps: Strategy, Education, and Live Mode

This plan covers the implementation of the three major requested features: Strategy management, an educational FAQ, and a professional "Live Mode" dashboard refine.

## User Review Required

> [!IMPORTANT]
> - **Strategy Builder**: I will implement a "Smart Strategy" builder in the new Strategy page. Users will be able to configure parameters (RSI, Take Profit, Stop Loss) which will then be passed to the backend for backtesting or live execution.
> - **Live Mode Visuals**: "Live" mode will trigger a significant aesthetic shift in the Dashboard (Pulse effects, secondary confirmation for trades) to prevent accidental execution and provide a "High-Stakes" feel as requested.

## Proposed Changes

---

### Backend Components

#### [MODIFY] [backtest.py](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/backend/app/api/backtest.py)
- Enhance `/run-rules` to accept quantitative parameters (RSI thresholds, EMA periods) rather than just a name.

---

### Frontend Components

#### [NEW] [StrategyPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/StrategyPage.jsx)
- **Strategy Selection**: Pick from Mean Reversion, Momentum, Grid, etc.
- **Rule Builder**: Form-based interface to set quantitative rules.
- **Save Strategy**: Allow users to save their custom configurations.

#### [NEW] [FAQPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/FAQPage.jsx)
- **Educational Cards**: 
    - **PoT**: Explaining Proof-of-Thought and how agents reach consensus.
    - **x402**: Explaining the "Payment Required" protocol and wallet signing.
    - **Governance**: Explaining the DAO voting system.

#### [MODIFY] [TradingDashboard.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/TradingDashboard.jsx)
- **Live/Paper Toggle**: Add a prominent toggle at the top.
- **Live Mode Refine**: 
    - Switch background to a darker, more intense gradient.
    - Add "HOT WALLET" status more prominently.
    - Implement a "Live Depth" mock chart.

#### [MODIFY] [App.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/App.jsx)
- Register `/strategy` and `/faq` routes and add them to the navigation.

## Verification Plan

### Automated Tests
- Verify that toggling "Live Mode" correctly updates the local execution state and UI classes.
- Verify that Strategy form values are correctly serialized before being sent to the backend.

### Manual Verification
- Verify the FAQ page is responsive and informative.
- Verify the visual "Live Mode" shift feels premium and distinct from backtesting simulations.
