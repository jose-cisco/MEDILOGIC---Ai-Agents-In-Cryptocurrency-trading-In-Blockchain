"""
LLM Provider Routing — Direct Provider Connection
==================================================
Each model connects directly to its provider's API:

  • glm-5.1 → io.net (IONET_API_KEY)
  • grok-4.20-0309 → x.ai v1 (XAI_API_KEY)
  • grok-4.20-0309-v2 → x.ai v2 (XAI_API_KEY)
  • mimo-v2-pro → Xiaomi (XIAOMI_API_KEY)
  • qwen-3.6-plus → Alibaba Cloud (ALIBABA_API_KEY)

No OpenRouter dependency - each provider is connected independently.

Ollama is NEVER used for live/paper trading — only for backtesting.
Set the appropriate API key in .env to activate each provider.
Falls back to Ollama ONLY when no cloud keys are configured (local dev).

Per-role tuning (temperature, top_p, max_tokens, frequency/presence penalty)
is read from Settings so each agent gets optimal inference parameters.
"""
import logging
from typing import Optional, Any
from contextvars import ContextVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from app.core.config import get_settings
from app.core.llm_auto_tune import (
    get_auto_tuner,
    auto_tune_planner,
    auto_tune_verifier,
    auto_tune_controller,
    TaskType,
    ComplexityLevel,
    RiskLevel,
)

logger = logging.getLogger(__name__)

# Context variable to track if we are currently in backtest mode
# This ensures that cloud LLMs are NEVER instantiated during backtests to avoid costs.
is_backtest_mode: ContextVar[bool] = ContextVar("is_backtest_mode", default=False)

# ─── Custom LLM Overrides ──────────────────────────────────────────────────
# Users can provide their own LLM API keys and base URLs per request.
custom_llm_provider: ContextVar[Optional[str]] = ContextVar("custom_llm_provider", default=None)
custom_llm_api_key: ContextVar[Optional[str]] = ContextVar("custom_llm_api_key", default=None)
custom_llm_base_url: ContextVar[Optional[str]] = ContextVar("custom_llm_base_url", default=None)
custom_llm_model: ContextVar[Optional[str]] = ContextVar("custom_llm_model", default=None)


# ─── Direct Provider Model Catalogue ─────────────────────────────────────────
# Each model connects directly to its provider - no OpenRouter routing.
# 
# Provider → Model mapping:
#   - io.net → GLM-5.1 (Reasoning) - TEXT ONLY
#   - x.ai → Grok 4.20 0309 (Reasoning) v1 & v2 - TEXT + IMAGE INPUT
#   - Xiaomi → MiMo-V2-Pro (Reasoning) - TEXT ONLY
#   - Alibaba Cloud → Qwen 3.6 Plus (Reasoning) - TEXT ONLY
#
# IMAGE INPUT: Only Grok 4.20 0309 (v1 and v2) support image input!
#
DIRECT_PROVIDER_MODELS: dict[str, dict] = {
    "glm-5.1": {"provider": "ionet", "label": "GLM-5.1 (Reasoning)", "reasoning": True, "supports_image": False},
    "grok-4.20-0309": {"provider": "xai", "label": "Grok 4.20 0309 (Reasoning) v1", "reasoning": True, "supports_image": True},
    "grok-4.20-0309-v2": {"provider": "xai", "label": "Grok 4.20 0309 (Reasoning) v2", "reasoning": True, "supports_image": True},
    "mimo-v2-pro": {"provider": "xiaomi", "label": "MiMo-V2-Pro (Reasoning)", "reasoning": True, "supports_image": False},
    "qwen-3.6-plus": {"provider": "alibaba", "label": "Qwen 3.6 Plus (Reasoning)", "reasoning": True, "supports_image": False},
}


def model_supports_image(model_id: str) -> bool:
    """
    Check if a model supports image input.
    
    IMPORTANT: ONLY Grok 4.20 0309 (v1 and v2) support image input.
    All other models (glm-5.1, mimo-v2-pro, qwen-3.6-plus) are TEXT ONLY.
    
    Args:
        model_id: The model identifier string
        
    Returns:
        True if the model supports image input, False otherwise
    """
    model_info = DIRECT_PROVIDER_MODELS.get(model_id, {})
    return model_info.get("supports_image", False)


# ─── Low-level factory helpers ─────────────────────────────────────────────────

def _get_ionet_llm(
    temperature: float = 0.1,
    top_p: float = 0.92,
    max_tokens: int = 4096,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
) -> BaseChatModel:
    """GLM-5.1 Reasoning via io.net OpenAI-compatible endpoint."""
    settings = get_settings()
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        base_url=settings.IONET_BASE_URL,
        api_key=settings.IONET_API_KEY,
        model=settings.IONET_MODEL,
        temperature=temperature,
        model_kwargs={
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        },
        max_tokens=max_tokens,
    )


def _get_xai_llm(
    model_id: str = "grok-4.20-0309-v2-reasoning",
    temperature: float = 0.0,
    top_p: float = 0.85,
    max_tokens: int = 2048,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
) -> BaseChatModel:
    """Grok 4.20 Reasoning via x.ai OpenAI-compatible endpoint."""
    settings = get_settings()
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        base_url=settings.XAI_BASE_URL,
        api_key=settings.XAI_API_KEY,
        model=model_id,
        temperature=temperature,
        model_kwargs={
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        },
        max_tokens=max_tokens,
    )


def _get_xiaomi_llm(
    temperature: float = 0.1,
    top_p: float = 0.92,
    max_tokens: int = 4096,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
) -> BaseChatModel:
    """MiMo-V2-Pro Reasoning via Xiaomi OpenAI-compatible endpoint."""
    settings = get_settings()
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        base_url=settings.XIAOMI_BASE_URL,
        api_key=settings.XIAOMI_API_KEY,
        model=settings.XIAOMI_MODEL,
        temperature=temperature,
        model_kwargs={
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        },
        max_tokens=max_tokens,
    )


def _get_alibaba_llm(
    temperature: float = 0.1,
    top_p: float = 0.92,
    max_tokens: int = 4096,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
) -> BaseChatModel:
    """Qwen 3.6 Plus Reasoning via Alibaba Cloud OpenAI-compatible endpoint."""
    settings = get_settings()
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        base_url=settings.ALIBABA_BASE_URL,
        api_key=settings.ALIBABA_API_KEY,
        model=settings.ALIBABA_MODEL,
        temperature=temperature,
        model_kwargs={
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        },
        max_tokens=max_tokens,
    )


def _get_ollama_llm(
    temperature: float = 0.1,
    top_p: float = 0.90,
    num_predict: int = 2048,
) -> BaseChatModel:
    """Ollama local/cloud — ONLY used for backtesting or local dev fallback."""
    settings = get_settings()
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        temperature=temperature,
        model_kwargs={
            "top_p": top_p,
            "num_predict": num_predict,
        },
    )


def _get_backtest_ollama_llm(
    temperature: float = 0.15,
    top_p: float = 0.90,
    num_predict: int = 4096,
) -> BaseChatModel:
    """
    Backtest path is fixed to Ollama endpoint (cloud/local), independent
    from live-trading provider routing.
    """
    settings = get_settings()
    return ChatOllama(
        base_url=settings.BACKTEST_OLLAMA_BASE_URL or settings.OLLAMA_BASE_URL,
        model=settings.BACKTEST_OLLAMA_MODEL or settings.OLLAMA_MODEL,
        temperature=temperature,
        model_kwargs={
            "top_p": top_p,
            "num_predict": num_predict,
        },
    )


# ─── Generic provider selector ─────────────────────────────────────────────────

def get_llm(temperature: float = 0.1, provider: str | None = None) -> BaseChatModel:
    settings = get_settings()
    provider = provider or settings.LLM_PROVIDER
    if provider == "ionet" and settings.IONET_API_KEY:
        return _get_ionet_llm(temperature=temperature)
    if provider == "xai" and settings.XAI_API_KEY:
        return _get_xai_llm(temperature=temperature)
    if provider == "xiaomi" and settings.XIAOMI_API_KEY:
        return _get_xiaomi_llm(temperature=temperature)
    if provider == "alibaba" and settings.ALIBABA_API_KEY:
        return _get_alibaba_llm(temperature=temperature)
    return _get_ollama_llm(temperature=temperature)


# ─── Role-specific parameter bundles ───────────────────────────────────────────

def _planner_params() -> dict:
    """Read Planner tuning from Settings."""
    s = get_settings()
    return dict(
        temperature=s.PLANNER_TEMPERATURE,
        top_p=s.PLANNER_TOP_P,
        max_tokens=s.PLANNER_MAX_TOKENS,
        frequency_penalty=s.PLANNER_FREQUENCY_PENALTY,
        presence_penalty=s.PLANNER_PRESENCE_PENALTY,
    )


def _verifier_params() -> dict:
    """Read Verifier tuning from Settings."""
    s = get_settings()
    return dict(
        temperature=s.VERIFIER_TEMPERATURE,
        top_p=s.VERIFIER_TOP_P,
        max_tokens=s.VERIFIER_MAX_TOKENS,
        frequency_penalty=s.VERIFIER_FREQUENCY_PENALTY,
        presence_penalty=s.VERIFIER_PRESENCE_PENALTY,
    )


def _controller_params() -> dict:
    """Read Controller tuning from Settings."""
    s = get_settings()
    return dict(
        temperature=s.CONTROLLER_TEMPERATURE,
        top_p=s.CONTROLLER_TOP_P,
        max_tokens=s.CONTROLLER_MAX_TOKENS,
        frequency_penalty=s.CONTROLLER_FREQUENCY_PENALTY,
        presence_penalty=s.CONTROLLER_PRESENCE_PENALTY,
    )


def _rag_params() -> dict:
    """Read RAG summariser tuning from Settings."""
    s = get_settings()
    return dict(
        temperature=s.RAG_TEMPERATURE,
        top_p=s.RAG_TOP_P,
        max_tokens=s.RAG_MAX_TOKENS,
        frequency_penalty=s.RAG_FREQUENCY_PENALTY,
        presence_penalty=s.RAG_PRESENCE_PENALTY,
    )


def _backtest_params() -> dict:
    """Read Backtest tuning from Settings."""
    s = get_settings()
    return dict(
        temperature=s.BACKTEST_TEMPERATURE,
        top_p=s.BACKTEST_TOP_P,
        num_predict=s.BACKTEST_MAX_TOKENS,
    )


# ─── Cloud model factory (Direct Provider Routing) ─────────────────────────────

def _get_cloud_llm(model_id: str, **kwargs) -> BaseChatModel:
    """
    Instantiate a cloud LLM by model identifier - direct provider connection.

    model_id: "glm-5.1" | "grok-4.20-0309" | "grok-4.20-0309-v2" | "mimo-v2-pro" | "qwen-3.6-plus"
    kwargs: forwarded to the underlying factory (temperature, top_p, etc.)
    """
    settings = get_settings()

    # ─── Custom LLM Override Logic ─────────────────────────────────────────
    custom_provider = custom_llm_provider.get()
    custom_key = custom_llm_api_key.get()
    custom_url = custom_llm_base_url.get()
    custom_mdl = custom_llm_model.get()

    if custom_provider and custom_key:
        from langchain_openai import ChatOpenAI
        logger.info("Using custom LLM provider: %s", custom_provider)
        return ChatOpenAI(
            base_url=custom_url,  # Optional, can be None for native OpenAI/Anthropic etc. if using their SDKs, but ChatOpenAI uses it
            api_key=custom_key,
            model=custom_mdl or model_id,
            temperature=kwargs.get("temperature", 0.1),
            model_kwargs={
                "top_p": kwargs.get("top_p", 0.92),
                "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
                "presence_penalty": kwargs.get("presence_penalty", 0.0),
            },
            max_tokens=kwargs.get("max_tokens", 4096),
        )

    # CRITICAL SAFETY: Never allow cloud models during backtests
    if is_backtest_mode.get():
        logger.error("ACCESS DENIED: Attempted to instantiate cloud model '%s' during backtest.", model_id)
        raise RuntimeError(
            f"Backtesting is restricted to local/free models (Ollama). "
            f"Cloud model '{model_id}' cannot be used to avoid costs."
        )

    # GLM-5.1 Reasoning (io.net direct)
    if model_id == "glm-5.1":
        if settings.IONET_API_KEY:
            logger.info("Routing GLM-5.1 via io.net (Direct) (Reasoning: ON)")
            return _get_ionet_llm(**kwargs)
        raise RuntimeError("GLM-5.1 requires IONET_API_KEY.")

    # Grok 4.20 0309 Reasoning v1 (x.ai direct)
    if model_id == "grok-4.20-0309":
        if settings.XAI_API_KEY:
            logger.info("Routing Grok 4.20 0309 v1 via x.ai (Direct) (Reasoning: ON)")
            return _get_xai_llm(model_id=settings.XAI_MODEL_V1, **kwargs)
        raise RuntimeError("Grok 4.20 0309 v1 requires XAI_API_KEY.")

    # Grok 4.20 0309 Reasoning v2 (x.ai direct)
    if model_id == "grok-4.20-0309-v2":
        if settings.XAI_API_KEY:
            logger.info("Routing Grok 4.20 0309 v2 via x.ai (Direct) (Reasoning: ON)")
            return _get_xai_llm(model_id=settings.XAI_MODEL_V2, **kwargs)
        raise RuntimeError("Grok 4.20 0309 v2 requires XAI_API_KEY.")

    # MiMo-V2-Pro (Xiaomi direct)
    if model_id == "mimo-v2-pro":
        if settings.XIAOMI_API_KEY:
            logger.info("Routing MiMo-V2-Pro via Xiaomi (Direct) (Reasoning: ON)")
            return _get_xiaomi_llm(**kwargs)
        raise RuntimeError("MiMo-V2-Pro requires XIAOMI_API_KEY.")

    # Qwen 3.6 Plus (Alibaba Cloud direct)
    if model_id == "qwen-3.6-plus":
        if settings.ALIBABA_API_KEY:
            logger.info("Routing Qwen 3.6 Plus via Alibaba Cloud (Direct) (Reasoning: ON)")
            return _get_alibaba_llm(**kwargs)
        raise RuntimeError("Qwen 3.6 Plus requires ALIBABA_API_KEY.")

    raise ValueError(
        f"Unknown cloud model '{model_id}'. "
        f"Valid options: 'glm-5.1' (io.net), 'grok-4.20-0309' (xAI v1), 'grok-4.20-0309-v2' (xAI v2), "
        f"'mimo-v2-pro' (Xiaomi), 'qwen-3.6-plus' (Alibaba)."
    )


# ─── Per-Agent Model Selection ────────────────────────────────────────────────

def resolve_agent_models(
    planner_model: str = "glm-5.1",
    verifier_model: str = "grok-4.20-0309",
    controller_model: str = "glm-5.1",
    monitor_model: str = "glm-5.1",
    adjuster_model: str = "glm-5.1",
) -> dict:
    """
    Resolve models for each agent independently.
    
    Users can select different models for each of the 5 agents:
      - Planner: Market analysis and trade proposals
      - Verifier: Security audits and risk validation
      - Controller: Final consensus decisions
      - Monitor: Post-execution tracking
      - Adjuster: Reactive self-correction
    
    Args:
        planner_model: Model for Planner agent (default: glm-5.1)
        verifier_model: Model for Verifier agent (default: grok-4.20-0309)
        controller_model: Model for Controller agent (default: glm-5.1)
        monitor_model: Model for Monitor agent (default: glm-5.1)
        adjuster_model: Model for Adjuster agent (default: glm-5.1)
    
    Returns:
        Dict with model assignment for each agent
    """
    assignment = {
        "planner_llm": planner_model,
        "verifier_llm": verifier_model,
        "controller_llm": controller_model,
        "monitor_llm": monitor_model,
        "adjuster_llm": adjuster_model,
    }
    
    # Log unique models for cost tracking
    unique_models = set(assignment.values())
    if len(unique_models) == 1:
        logger.info(
            "Agent model assignment: ALL 5 agents → %s (single model, cost optimized)",
            list(unique_models)[0],
        )
    else:
        logger.info(
            "Agent model assignment: Planner → %s | Verifier → %s | Controller → %s | Monitor → %s | Adjuster → %s (%d unique models)",
            planner_model, verifier_model, controller_model, monitor_model, adjuster_model,
            len(unique_models),
        )
    
    return assignment


# ─── Legacy Dual-Model Assignment (Backward Compatibility) ─────────────────────

def resolve_agent_models_dual(model_1: str, model_2: str) -> dict:
    """
    Legacy dual-model assignment for backward compatibility.
    
    Auto-assign cloud models to agents based on user's 2-model selection.
    Assignment strategy (cost-optimized):
      - model_1 → Planner + Controller  (2 invocations, 1 API key)
      - model_2 → Verifier              (1 invocation, 1 API key)
    
    If model_1 == model_2, all agents use the same model (1 API key only).
    
    Returns dict with keys: planner_llm, verifier_llm, controller_llm
    """
    assignment = {
        "planner_llm": model_1,
        "verifier_llm": model_2,
        "controller_llm": model_1,
        "monitor_llm": model_1,
        "adjuster_llm": model_1,
    }
    
    if model_1 == model_2:
        logger.info(
            "Agent model assignment: ALL agents → %s (single model, cost optimized)",
            model_1,
        )
    else:
        logger.info(
            "Agent model assignment: Planner+Controller → %s | Verifier → %s (dual model)",
            model_1, model_2,
        )
    
    return assignment


# ─── Role-specific public API ─────────────────────────────────────────────────

def get_planner_llm(model_id: str = "glm-5.1", **overrides) -> BaseChatModel:
    """
    Planner LLM — auto-assigned from user's model selection.
    
    Optimal: temperature=0.3, top_p=0.92, max_tokens=4096
    Rationale: Planner needs moderate creativity to explore market scenarios
    and generate diverse trading hypotheses while staying grounded in data.
    top_p=0.92 allows broad token sampling for richer analysis.
    """
    params = _planner_params()
    params.update(overrides)
    settings = get_settings()

    # Check if we have the required API key for this model
    model_info = DIRECT_PROVIDER_MODELS.get(model_id, {})
    provider = model_info.get("provider", "")
    
    has_key = (
        (provider == "ionet" and settings.IONET_API_KEY) or
        (provider == "xai" and settings.XAI_API_KEY) or
        (provider == "xiaomi" and settings.XIAOMI_API_KEY) or
        (provider == "alibaba" and settings.ALIBABA_API_KEY)
    )

    if has_key:
        logger.info("Planner → %s [Direct Provider]", model_id)
        return _get_cloud_llm(model_id, **params)

    # Fallback to Ollama for local dev
    logger.warning("Planner → Ollama fallback (no API key for %s)", model_id)
    return _get_ollama_llm(
        temperature=params.get("temperature", 0.3),
        top_p=params.get("top_p", 0.92),
        num_predict=params.get("max_tokens", 4096),
    )


def get_verifier_llm(model_id: str = "grok-4.20-0309", **overrides) -> BaseChatModel:
    """
    Verifier LLM — auto-assigned from user's model selection.
    """
    params = _verifier_params()
    params.update(overrides)
    settings = get_settings()

    model_info = DIRECT_PROVIDER_MODELS.get(model_id, {})
    provider = model_info.get("provider", "")
    
    has_key = (
        (provider == "ionet" and settings.IONET_API_KEY) or
        (provider == "xai" and settings.XAI_API_KEY) or
        (provider == "xiaomi" and settings.XIAOMI_API_KEY) or
        (provider == "alibaba" and settings.ALIBABA_API_KEY)
    )

    if has_key:
        logger.info("Verifier → %s [Direct Provider]", model_id)
        return _get_cloud_llm(model_id, **params)

    logger.warning("Verifier → Ollama fallback (no API key for %s)", model_id)
    return _get_ollama_llm(
        temperature=params.get("temperature", 0.0),
        top_p=params.get("top_p", 0.85),
        num_predict=params.get("max_tokens", 2048),
    )


def get_controller_llm(model_id: str = "glm-5.1", **overrides) -> BaseChatModel:
    """
    Controller LLM — auto-assigned from user's model selection.
    """
    params = _controller_params()
    params.update(overrides)
    settings = get_settings()

    model_info = DIRECT_PROVIDER_MODELS.get(model_id, {})
    provider = model_info.get("provider", "")
    
    has_key = (
        (provider == "ionet" and settings.IONET_API_KEY) or
        (provider == "xai" and settings.XAI_API_KEY) or
        (provider == "xiaomi" and settings.XIAOMI_API_KEY) or
        (provider == "alibaba" and settings.ALIBABA_API_KEY)
    )

    if has_key:
        logger.info("Controller → %s [Direct Provider]", model_id)
        return _get_cloud_llm(model_id, **params)

    logger.warning("Controller → Ollama fallback (no API key for %s)", model_id)
    return _get_ollama_llm(
        temperature=params.get("temperature", 0.0),
        top_p=params.get("top_p", 0.85),
        num_predict=params.get("max_tokens", 2048),
    )


def get_backtest_llm(**overrides) -> BaseChatModel:
    """
    Backtest LLM — always uses Ollama route (cloud/local).
    
    Optimal: temperature=0.15, top_p=0.90, max_tokens=4096
    Rationale: Backtesting needs slight creativity to simulate diverse
    strategy decisions across historical data, but must stay grounded
    to avoid hallucinating unrealistic trades. Higher max_tokens for
    generating full arrays of trade decisions.
    """
    params = _backtest_params()
    params.update(overrides)

    # ─── Custom LLM Override for Backtesting ──────────────────────────────
    custom_provider = custom_llm_provider.get()
    custom_key = custom_llm_api_key.get()
    custom_url = custom_llm_base_url.get()
    custom_mdl = custom_llm_model.get()

    if custom_provider and custom_key:
        from langchain_openai import ChatOpenAI
        logger.info("Using custom LLM provider for BACKTEST: %s", custom_provider)
        return ChatOpenAI(
            base_url=custom_url,
            api_key=custom_key,
            model=custom_mdl or "gpt-4o", # Default for custom if not specified
            temperature=params.get("temperature", 0.15),
            model_kwargs={
                "top_p": params.get("top_p", 0.90),
            },
            max_tokens=params.get("num_predict", 4096),
        )

    return _get_backtest_ollama_llm(**params)


def get_rag_llm(model_id: str = "glm-5.1", **overrides) -> BaseChatModel:
    """
    RAG Summariser LLM — uses model_1 (Planner/Controller model) for neutral synthesis.
    
    Optimal: temperature=0.0, top_p=0.85, max_tokens=1024
           frequency_penalty=0.3, presence_penalty=0.2
    Rationale: RAG summarisation must be factual and neutral — no creative
    extrapolation. frequency/presence penalties prevent repetitive summaries
    and encourage coverage of diverse source passages. Lower max_tokens
    since output is a concise 3-5 bullet point summary.
    """
    params = _rag_params()
    params.update(overrides)
    return get_controller_llm(model_id=model_id, **params)


# ─── Auto-Tuned LLM Getters (Self-Configuring) ────────────────────────────────

def get_auto_tuned_planner_llm(
    model_id: str = "glm-5.1",
    input_text: str = "",
    market_data: Optional[dict] = None,
    is_live: bool = False,
    **overrides,
) -> BaseChatModel:
    """
    Get Planner LLM with auto-tuned parameters.
    
    The system automatically detects:
    - Input complexity (simple, moderate, complex)
    - Risk level (low, medium, high)
    - Model-specific optimizations
    
    And configures optimal temperature, top_p, max_tokens, etc.
    """
    tuner = get_auto_tuner()
    tuned_params = tuner.get_agent_params(
        agent_role="planner",
        model_id=model_id,
        input_text=input_text,
        market_data=market_data,
        is_live=is_live,
    )
    
    # Convert to dict and apply overrides
    params = tuned_params.to_dict()
    params.update(overrides)
    
    logger.info(
        "Auto-tuned Planner: model=%s | temp=%.3f | top_p=%.3f | max_tokens=%d | reasoning=%s",
        model_id, params["temperature"], params["top_p"], params["max_tokens"], params["reasoning"]
    )
    
    return _get_cloud_llm(
        model_id,
        temperature=params["temperature"],
        top_p=params["top_p"],
        max_tokens=params["max_tokens"],
        frequency_penalty=params["frequency_penalty"],
        presence_penalty=params["presence_penalty"],
    )


def get_auto_tuned_verifier_llm(
    model_id: str = "grok-4.20-0309",
    input_text: str = "",
    market_data: Optional[dict] = None,
    is_live: bool = False,
    **overrides,
) -> BaseChatModel:
    """
    Get Verifier LLM with auto-tuned parameters.
    
    Verifier uses lower temperature for precision in security audits.
    Automatically adjusts based on task complexity and risk.
    """
    tuner = get_auto_tuner()
    tuned_params = tuner.get_agent_params(
        agent_role="verifier",
        model_id=model_id,
        input_text=input_text,
        market_data=market_data,
        is_live=is_live,
    )
    
    params = tuned_params.to_dict()
    params.update(overrides)
    
    logger.info(
        "Auto-tuned Verifier: model=%s | temp=%.3f | top_p=%.3f | max_tokens=%d | reasoning=%s",
        model_id, params["temperature"], params["top_p"], params["max_tokens"], params["reasoning"]
    )
    
    return _get_cloud_llm(
        model_id,
        temperature=params["temperature"],
        top_p=params["top_p"],
        max_tokens=params["max_tokens"],
        frequency_penalty=params["frequency_penalty"],
        presence_penalty=params["presence_penalty"],
    )


def get_auto_tuned_controller_llm(
    model_id: str = "glm-5.1",
    input_text: str = "",
    market_data: Optional[dict] = None,
    is_live: bool = False,
    **overrides,
) -> BaseChatModel:
    """
    Get Controller LLM with auto-tuned parameters.
    
    Controller uses very low temperature for deterministic consensus decisions.
    Automatically tightens parameters in high-risk situations.
    """
    tuner = get_auto_tuner()
    tuned_params = tuner.get_agent_params(
        agent_role="controller",
        model_id=model_id,
        input_text=input_text,
        market_data=market_data,
        is_live=is_live,
    )
    
    params = tuned_params.to_dict()
    params.update(overrides)
    
    logger.info(
        "Auto-tuned Controller: model=%s | temp=%.3f | top_p=%.3f | max_tokens=%d | reasoning=%s",
        model_id, params["temperature"], params["top_p"], params["max_tokens"], params["reasoning"]
    )
    
    return _get_cloud_llm(
        model_id,
        temperature=params["temperature"],
        top_p=params["top_p"],
        max_tokens=params["max_tokens"],
        frequency_penalty=params["frequency_penalty"],
        presence_penalty=params["presence_penalty"],
    )


def get_auto_tuned_llm(
    agent_role: str,
    model_id: str,
    input_text: str = "",
    market_data: Optional[dict] = None,
    is_live: bool = False,
    **overrides,
) -> BaseChatModel:
    """
    Generic auto-tuned LLM getter for any agent role.
    
    Args:
        agent_role: 'planner', 'verifier', 'controller', 'monitor', 'adjuster'
        model_id: LLM model identifier
        input_text: Input text for complexity detection
        market_data: Market data for risk detection
        is_live: Whether in live trading mode
        **overrides: Custom parameter overrides
    
    Returns:
        BaseChatModel with auto-tuned parameters
    """
    role_getters = {
        "planner": get_auto_tuned_planner_llm,
        "verifier": get_auto_tuned_verifier_llm,
        "controller": get_auto_tuned_controller_llm,
        "monitor": get_auto_tuned_planner_llm,  # Monitor similar to planner
        "adjuster": get_auto_tuned_controller_llm,  # Adjuster similar to controller
    }
    
    getter = role_getters.get(agent_role.lower(), get_auto_tuned_planner_llm)
    return getter(
        model_id=model_id,
        input_text=input_text,
        market_data=market_data,
        is_live=is_live,
        **overrides,
    )