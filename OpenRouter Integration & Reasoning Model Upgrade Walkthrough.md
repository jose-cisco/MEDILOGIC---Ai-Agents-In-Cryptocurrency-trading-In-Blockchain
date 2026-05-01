# OpenRouter Integration & Reasoning Model Upgrade Walkthrough

This upgrade transitions the AI trading platform to use OpenRouter as the primary provider for high-capability models, enforcing reasoning parameters for GLM and Grok variants to ensure maximum strategic accuracy.

## Key Changes

### 1. Backend Infrastructure
- **OpenRouter Factory**: Implemented `_get_openrouter_llm` in `llm.py` which supports the `reasoning: True` parameter.
- **Routing Logic**: Updated `_get_cloud_llm` to prioritize OpenRouter for:
    - `z-ai/glm-5.1` (Reasoning Enforced)
    - `z-ai/glm-5` (Reasoning Enforced)
    - `x-ai/grok-4.20-multi-agent` (Reasoning Enforced)
    - `minimax/minimax-m2.7` (Standard Agentic Mode)
- **Configuration**: Added `OPENROUTER_API_KEY` and specific model ID settings to `config.py`.

### 2. API Enhancements
- **Model Discovery**: New `GET /api/v1/payments/providers/openrouter` endpoint exposes the model catalogue, pricing, and reasoning status to the frontend.

### 3. Frontend Updates
- **Trading Dashboard**: Updated the model selection dropdowns to include the new OpenRouter-backed reasoning models.
- **Backtesting**: Added `MiniMax M2.7` and updated `GLM` descriptions in the backtest engine.
- **Payments Page**: Integrated a new `OpenRouterPanel` providing visibility into the configured models and API status.

## Visual Overview

### Trading Dashboard Selection
The dashboard now explicitly shows "Reasoning Enforced" for GLM and Grok models, ensuring users understand they are using the most capable variants.

### Payments & Providers
The Payments page now features a dedicated OpenRouter panel alongside Claw402, providing a complete picture of the platform's multi-cloud provider strategy.

## Verification
- [x] **Reasoning Parameter**: Verified that `model_kwargs={"reasoning": True}` is passed to the underlying `ChatOpenAI` instance for GLM and Grok models.
- [x] **Routing Priority**: Confirmed that if `OPENROUTER_API_KEY` is present, it is used for the specified models before falling back to `ionet` or `xai`.
- [x] **UI Consistency**: Verified that the new models and their reasoning capabilities are correctly reflected in the Trading and Backtest interfaces.
