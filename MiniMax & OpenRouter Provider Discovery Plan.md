# MiniMax & OpenRouter Provider Discovery Plan

This plan addresses the missing MiniMax models in backtesting and provides a more detailed view of OpenRouter's model/provider ecosystem for real trading.

## User Review Required

> [!NOTE]
> - **MiniMax in Backtesting**: I will add `minimax-m2.7` to the Ollama backtest list. Please ensure you have this model pulled in your local Ollama instance (`ollama pull minimax-m2.7`).
> - **OpenRouter Provider Variety**: I will update the discovery logic to show multiple variations of models if OpenRouter lists them separately (e.g. via different providers or tiers) to reflect the "different price" variety you mentioned.

## Proposed Changes

---

### Backend Components

#### [MODIFY] [payments.py](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/backend/app/api/payments.py)
- Update the merging logic to show ALL models matching `minimax`, `glm`, and `grok` from OpenRouter, not just the hardcoded ones.
- This will capture provider-specific versions and price variations automatically.

---

### Frontend Components

#### [MODIFY] [BacktestPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/BacktestPage.jsx)
- Add `minimax-m2.7` to `BACKTEST_MODELS`.
- Update the header/icons to include MiniMax in the backtest context.

#### [MODIFY] [PaymentsPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/PaymentsPage.jsx)
- Enhance the model card to show "OpenRouter Provider Info" or description if available.
- Ensure the pricing display handles any variation in prompt/completion costs.

## Verification Plan

### Automated Tests
- Verify `/providers/openrouter` returns multiple MiniMax-related entries if they exist in the live feed.

### Manual Verification
- Check `BacktestPage` for the new MiniMax option.
- Verify `PaymentsPage` shows the expanded model list with live pricing.
