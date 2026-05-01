# Restricted Backtesting & Dynamic OpenRouter Pricing Plan

This plan ensures zero-cost backtesting and provides users with live pricing data from OpenRouter's model ecosystem.

## User Review Required

> [!IMPORTANT]
> - **Backtest Lock-in**: Backtesting will be strictly restricted to Ollama (local/free). Any attempt to route to OpenRouter or Claw402 during a backtest will be blocked at the factory level.
> - **OpenRouter Live Data**: The backend will now attempt to fetch live pricing from OpenRouter's API to show the "different prices" and providers you mentioned.

## Proposed Changes

---

### Backend Components

#### [MODIFY] [llm.py](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/backend/app/core/llm.py)
- Strengthen `get_backtest_llm` to ensure no accidental cloud routing.
- Add a safety check in `_get_cloud_llm` that rejects calls if a `BACKTEST_MODE` flag is active (via context or parameter).

#### [MODIFY] [payments.py](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/backend/app/api/payments.py)
- Enhance `/providers/openrouter` to fetch live data from `https://openrouter.ai/api/v1/models`.
- Parse the response to include pricing (per 1M tokens) and supported features for the UI.

#### [MODIFY] [config.py](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/backend/app/core/config.py)
- Clarify in comments that `BACKTEST_FORCE_OLLAMA_CLOUD` (or similar) is mandatory to avoid costs.

---

### Frontend Components

#### [MODIFY] [BacktestPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/BacktestPage.jsx)
- Update `BACKTEST_MODELS` to be strictly Ollama.
- Add a persistent "Zero-Cost Mode" badge to the header during backtests.
- Explicitly state that x402 payments are disabled for simulation.

#### [MODIFY] [PaymentsPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/PaymentsPage.jsx)
- Enhance `OpenRouterPanel` to display live pricing (prompt/completion cost) fetched from the new backend endpoint.
- Show provider variety if OpenRouter metadata allows (e.g., "Served by 14+ providers").

## Verification Plan

### Automated Tests
- Run a backtest through the API and verify that no OpenRouter/Claw402 logs appear.
- Verify that the `/providers/openrouter` endpoint returns realistic pricing data when an API key is provided.

### Manual Verification
- Check the `BacktestPage` to ensure only local models are selectable.
- Verify the `PaymentsPage` shows the new dynamic pricing grid for OpenRouter.
