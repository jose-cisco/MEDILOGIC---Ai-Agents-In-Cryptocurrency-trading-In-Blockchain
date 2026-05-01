# Walkthrough: MiniMax & Provider Discovery Upgrade

This update expands the platform's model support and provides a more dynamic view of the OpenRouter ecosystem, capturing provider variety and ensuring local backtest compatibility for MiniMax.

## Key Changes

### 1. MiniMax Backtesting
- **Ollama Integration**: Added `minimax-m2.7` to the `BACKTEST_MODELS` list in `BacktestPage.jsx`. This enables zero-cost historical simulations using MiniMax reasoning, provided you have the model pulled in your local Ollama instance.
- **Zero-Cost Badge**: The model is correctly tagged as an "Ollama" provider in the backtest UI to stay consistent with the free-tier enforcement.

### 2. Auto-Discovery of Model Variations
- **Dynamic Search**: Updated the `/providers/openrouter` API to automatically scan the entire OpenRouter model catalogue for any variations of `minimax`, `glm-5`, or `grok-4`.
- **Pricing Variety**: The UI now surfaces multiple providers and price points for these models if OpenRouter lists them separately, addressing the need to see "many providers in different price."
- **Primary vs. Discover**: The Payments page now distinguishes between the platform's **Primary Enforced** models (where reasoning is strictly locked by the backend) and other auto-discovered variations.

## UI walkthrough

### BacktestPage selection
- MiniMax M2.7 is now available in the backtest dropdown for free simulation.

### PaymentsPage grid
- The OpenRouter grid now shows a broader variety of models, each with live prompt/completion pricing and a "Primary" badge for the core trading models.

## Verification
- [x] **Backtest Model**: Confirmed `minimax-m2.7` appears in the simulation options.
- [x] **Live Discovery**: Verified the backend correctly merges hardcoded models with live variations from the OpenRouter API feed.
- [x] **UI Clarity**: Confirmed the new badges and pricing layouts correctly handle multiple model variations.
