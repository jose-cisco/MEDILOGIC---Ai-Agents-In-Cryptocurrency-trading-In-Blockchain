# OpenRouter Integration & Reasoning Model Upgrade

This plan outlines the steps to integrate OpenRouter for advanced reasoning models and enforce reasoning parameters for GLM and Grok models, while adding support for the MiniMax M2.7 multi-agent model.

## User Review Required

> [!IMPORTANT]
> - **API Key Migration**: You will need to provide an `OPENROUTER_API_KEY` in your `.env` file.
> - **Cost Consideration**: GLM-5.1, GLM-5, and Grok 4.20 Multi-Agent on OpenRouter have specific pricing models ($0.95 - $2.00 per 1M input tokens).
> - **Reasoning Enforcement**: Non-reasoning modes for GLM and Grok will be removed from the selection logic to ensure maximum output quality.

## Proposed Changes

---

### Backend Components

#### [MODIFY] [config.py](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/backend/app/core/config.py)
- Add `OPENROUTER_API_KEY`.
- Add `OPENROUTER_BASE_URL` (default: `https://openrouter.ai/api/v1`).
- Clean up/Deprecate `IONET_API_KEY` and `XAI_API_KEY` if they are no longer the primary routes for these models.

#### [MODIFY] [llm.py](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/backend/app/core/llm.py)
- Implement `_get_openrouter_llm()` factory using `ChatOpenAI` with `model_kwargs={"reasoning": True}` for supported models.
- Update `_get_cloud_llm()` to route:
    - `"glm-5.1"` -> `z-ai/glm-5.1` (Reasoning: ON)
    - `"glm-5"` -> `z-ai/glm-5` (Reasoning: ON)
    - `"grok-4.20"` -> `x-ai/grok-4.20-multi-agent` (Reasoning: ON)
    - `"minimax-m2.7"` -> `minimax/minimax-m2.7` (Reasoning: OFF/Normal)
- Update `CLAW402_MODELS` to reflect these updates if they are also served through Claw402, or prioritize OpenRouter for cloud usage.

#### [NEW] [openrouter_routes.py](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/backend/app/api/openrouter_routes.py)
- Create a simple endpoint to return the current OpenRouter model list and prices for the UI.

---

### Frontend Components

#### [MODIFY] [PaymentsPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/PaymentsPage.jsx)
- Add an `OpenRouterPanel` component to display the new models and their reasoning capabilities.
- Show pricing information retrieved from the OpenRouter API (proxied via backend).

#### [MODIFY] [Trading Dashboard (App.jsx or dedicated page)]
- Update model selection dropdowns to use the new OpenRouter model IDs.

## OpenRouter Model Details
- **GLM-5.1**: `z-ai/glm-5.1` (Reasoning enabled)
- **GLM-5**: `z-ai/glm-5` (Reasoning enabled)
- **Grok 4.20 Multi-Agent**: `x-ai/grok-4.20-multi-agent` (Reasoning enabled)
- **MiniMax M2.7**: `minimax/minimax-m2.7` (Standard agentic mode)

## Verification Plan

### Automated Tests
- Run `pytest` on a mock LLM factory to ensure `model_kwargs` includes `"reasoning": True` for the specified models.
- Validate that selecting a non-reasoning mode for GLM fails or defaults to the reasoning model.

### Manual Verification
- Deploy to development environment.
- Test the "Request -> 402 -> Payment -> Retry -> Success" flow with an OpenRouter backed model using the `PaymentsPage` simulator.
- Verify that LLM responses from OpenRouter contain reasoning details (if inspected via logs).
