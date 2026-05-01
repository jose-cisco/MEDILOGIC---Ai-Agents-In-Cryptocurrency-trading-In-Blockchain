from fastapi import APIRouter
from app.schemas.models import AgentStatus
from app.blockchain.ethereum import EthereumClient
from app.blockchain.solana import SolanaClient
from app.core.config import get_settings
from app.core.llm import resolve_agent_models
from app.core.x402 import x402_service, get_resource_price, PaymentResource

router = APIRouter()
eth_client = EthereumClient()
sol_client = SolanaClient()


@router.get("/agents")
async def get_agent_status():
    agents = [
        AgentStatus(
            agent_name="Planner",
            status="active",
            last_action="Generated buy signal for ETH/USDT",
            total_decisions=150,
            successful_trades=98,
        ),
        AgentStatus(
            agent_name="Verifier",
            status="active",
            last_action="Verified planner decision - approved",
            total_decisions=150,
            successful_trades=150,
        ),
        AgentStatus(
            agent_name="Controller",
            status="active",
            last_action="Approved trade execution",
            total_decisions=150,
            successful_trades=120,
        ),
    ]
    return {"agents": agents}


@router.get("/blockchain")
async def get_blockchain_status():
    return {
        "ethereum": {
            "connected": eth_client.is_connected(),
            "block_number": eth_client.get_block_number(),
            "gas_price_gwei": eth_client.get_gas_price() / 1e9
            if eth_client.is_connected()
            else 0,
        },
        "solana": {
            "connected": sol_client.is_connected(),
        },
    }


@router.get("/system")
async def get_system_info():
    settings = get_settings()
    llm_label = (
        f"Trading Circle: grok-4.20, glm-5.1, glm-5, minimax-m2.7; "
        f"Backtest Circle: glm-5.1, glm-5, minimax-m2.7 (Ollama fallback)"
    )

    # Build x402 pricing info
    x402_pricing = {}
    if x402_service.enabled:
        for resource in PaymentResource:
            x402_pricing[resource.value] = get_resource_price(resource)

    return {
        "name": "AI Agent Blockchain Trading",
        "version": "1.0.0",
        "llm": llm_label,
        "trading_mode": settings.TRADING_MODE,
        "live_trading_enabled": settings.LIVE_TRADING_ENABLED,
        "x402_payment": {
            "enabled": x402_service.enabled,
            "testnet": x402_service.testnet,
            "chain_id": settings.X402_CHAIN_ID,
            "recipient_configured": bool(settings.X402_RECIPIENT_ADDRESS),
            "pricing_usd": x402_pricing if x402_service.enabled else None,
            "backtest_exempt": True,
            "backtest_exempt_reason": (
                "Backtesting is a simulation of crypto market behavior — "
                "not real capital deployment. x402 payments are not required."
            ),
        },
        "framework": "LangGraph + LangChain",
        "chains": ["Ethereum", "Solana"],
        "blockchain_framework": "BlockAgents (Identity Registry, Bill Registry, Incentive Management, Verification Agent, Consensus Agreement)",
        "consensus": "Proof-of-Thought (PoT) via BlockAgents",
        "governance": "mABC decentralized multi-agent voting",
        "security": "Ensemble LLM vulnerability detection (98.8% accuracy per Karim et al. 2025)",
        "observability": "Langfuse",
        "vector_db": "ChromaDB with Ollama embeddings",
        "features": [
            "Dual-model auto-assignment trading (model_1 → Planner+Controller, model_2 → Verifier)",
            "Hybrid RAG (Semantic + BM25 + RRF) in both trading AND backtesting",
            "Pay-per-use via smart contract Bill Registry",
            "x402 HTTP 402 Payment Required protocol (USDC on Base)",
            "Zero-shot learning for unseen market conditions",
            "EAAC secure infrastructure for Ethereum",
            "Backtesting with Ollama + Hybrid RAG (x402 exempt, cloud models not used)",
        ],
    }


@router.get("/llm-providers")
async def get_llm_providers():
    """List available cloud LLM models for dual-model selection.
    
    User selects exactly 2 cloud models (model_1, model_2).
    Agents auto-assign: model_1 → Planner+Controller, model_2 → Verifier.
    Ollama is NOT available for trading — only for backtesting.
    """
    settings = get_settings()
    models = [
        {
            "id": "glm-5.1",
            "name": "GLM-5.1 Reasoning",
            "provider": "OpenRouter",
            "description": "GLM-5.1 Reasoning — Planning & Analysis",
            "available": bool(settings.OPENROUTER_API_KEY),
            "recommended_roles": ["planner", "controller"],
        },
        {
            "id": "glm-5",
            "name": "GLM-5 Reasoning",
            "provider": "OpenRouter",
            "description": "GLM-5 Reasoning — Technical Design",
            "available": bool(settings.OPENROUTER_API_KEY),
            "recommended_roles": ["planner", "controller"],
        },
        {
            "id": "grok-4.20",
            "name": "Grok 4.20 Reasoning",
            "provider": "OpenRouter",
            "description": "Grok 4.20 Multi-Agent Reasoning — Security & Verification",
            "available": bool(settings.OPENROUTER_API_KEY),
            "recommended_roles": ["verifier"],
        },
        {
            "id": "minimax-m2.7",
            "name": "MiniMax M2.7",
            "provider": "OpenRouter",
            "description": "MiniMax M2.7 Agentic Model — Logistics & Documentation",
            "available": bool(settings.OPENROUTER_API_KEY),
            "recommended_roles": ["planner", "verifier"],
        },
    ]
    
    # Show example auto-assignments for each combination
    assignments = {}
    circle_models = ["glm-5.1", "glm-5", "grok-4.20", "minimax-m2.7"]
    for m1_id in circle_models:
        for m2_id in circle_models:
            assignment = resolve_agent_models(m1_id, m2_id)
            key = f"{m1_id}+{m2_id}"
            assignments[key] = {
                "model_1": m1_id,
                "model_2": m2_id,
                "planner": assignment["planner_llm"],
                "verifier": assignment["verifier_llm"],
                "controller": assignment["controller_llm"],
                "api_keys_needed": 1 if m1_id == m2_id else 2,
                "cost_note": (
                    "Single model — 1 API key only (lowest cost)"
                    if m1_id == m2_id
                    else "Dual model — 2 API keys (diverse verification)"
                ),
            }
    
    return {
        "models": models,
        "selection_rule": "User selects exactly 2 cloud models. Ollama is NOT available for trading (backtesting only).",
        "auto_assignment": "model_1 → Planner + Controller | model_2 → Verifier",
        "assignments": assignments,
        "backtest_model": {
            "id": "ollama",
            "provider": "local/cloud",
            "model": settings.BACKTEST_OLLAMA_MODEL or settings.OLLAMA_MODEL,
            "note": "Ollama is used ONLY for backtesting — never for live/paper trading",
        },
    }


@router.get("/llm-tuning")
async def get_llm_tuning():
    """Return per-role LLM inference parameters for transparency and debugging."""
    settings = get_settings()
    return {
        "planner": {
            "model": settings.IONET_MODEL,
            "provider": "io.net",
            "temperature": settings.PLANNER_TEMPERATURE,
            "top_p": settings.PLANNER_TOP_P,
            "max_tokens": settings.PLANNER_MAX_TOKENS,
            "frequency_penalty": settings.PLANNER_FREQUENCY_PENALTY,
            "presence_penalty": settings.PLANNER_PRESENCE_PENALTY,
            "rationale": "Moderate creativity for market analysis and diverse trading hypotheses",
        },
        "verifier": {
            "model": settings.XAI_MODEL,
            "provider": "x.ai",
            "temperature": settings.VERIFIER_TEMPERATURE,
            "top_p": settings.VERIFIER_TOP_P,
            "max_tokens": settings.VERIFIER_MAX_TOKENS,
            "frequency_penalty": settings.VERIFIER_FREQUENCY_PENALTY,
            "presence_penalty": settings.VERIFIER_PRESENCE_PENALTY,
            "rationale": "Deterministic for consistent security checks and vulnerability detection",
        },
        "controller": {
            "model": settings.IONET_MODEL,
            "provider": "io.net",
            "temperature": settings.CONTROLLER_TEMPERATURE,
            "top_p": settings.CONTROLLER_TOP_P,
            "max_tokens": settings.CONTROLLER_MAX_TOKENS,
            "frequency_penalty": settings.CONTROLLER_FREQUENCY_PENALTY,
            "presence_penalty": settings.CONTROLLER_PRESENCE_PENALTY,
            "rationale": "Deterministic for safety-critical go/no-go consensus decisions",
        },
        "rag_summarizer": {
            "model": settings.IONET_MODEL,
            "provider": "io.net",
            "temperature": settings.RAG_TEMPERATURE,
            "top_p": settings.RAG_TOP_P,
            "max_tokens": settings.RAG_MAX_TOKENS,
            "frequency_penalty": settings.RAG_FREQUENCY_PENALTY,
            "presence_penalty": settings.RAG_PRESENCE_PENALTY,
            "rationale": "Neutral factual synthesis with penalties to avoid repetitive summaries",
        },
        "backtest": {
            "model": settings.BACKTEST_OLLAMA_MODEL or settings.OLLAMA_MODEL,
            "provider": "ollama",
            "temperature": settings.BACKTEST_TEMPERATURE,
            "top_p": settings.BACKTEST_TOP_P,
            "max_tokens": settings.BACKTEST_MAX_TOKENS,
            "frequency_penalty": settings.BACKTEST_FREQUENCY_PENALTY,
            "presence_penalty": settings.BACKTEST_PRESENCE_PENALTY,
            "rationale": "Slight creativity for strategy simulation, grounded to avoid unrealistic trades",
        },
    }
