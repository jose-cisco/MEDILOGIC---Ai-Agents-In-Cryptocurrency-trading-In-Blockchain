"""
Trading Graph — Dual-Model Auto-Assignment + Hybrid RAG Architecture
====================================================================

User selects 2 cloud models (model_1, model_2). Agents auto-assign:
  • model_1 → Planner + Controller  (2 invocations, 1 API key)
  • model_2 → Verifier              (1 invocation, 1 API key)

If model_1 == model_2, all 3 agents use the same model (cost optimized).

Ollama is NOT used for live/paper trading — only for backtesting.

RAG context is fetched via hybrid semantic + lexical retrieval (top 10–15)
and injected into every node as a Context-augmented prompt.

Reference: Karim et al. (2025) framework achieving 95% synthetic /
           93% real-world accuracy via context-augmented LLM prompts.
"""
import json
import logging
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm import get_planner_llm, get_verifier_llm, get_controller_llm
from app.rag.knowledge_base import MarketKnowledgeBase

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# State Schema
# ─────────────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    market_data: dict
    trade_prompt: str
    token_pair: str
    chain: str
    rag_context: str
    rag_metadata: dict
    # Dual-model auto-assignment: model_1 → Planner+Controller, model_2 → Verifier
    model_1: str
    model_2: str
    planner_decision: dict
    verifier_result: dict
    controller_approval: bool
    final_decision: dict
    risk_score: float
    monitoring_strategy: dict
    adjustment_logic: dict

# ─────────────────────────────────────────────────────────────────────────────
# System Prompts
# ─────────────────────────────────────────────────────────────────────────────

PLANNER_SYSTEM = """You are an expert crypto trading analyst AI agent (Planner).
You specialise in Perceive → Plan → Reason → Act workflows for DeFi trading.

You have access to retrieved market knowledge from a HYBRID RAG system (semantic + lexical retrieval,
top 10–25 results fused via Reciprocal Rank Fusion). Use this context alongside real-time market data
to make a well-informed decision. Cite relevant RAG source IDs in your reasoning.

Return a JSON object with EXACTLY these fields:
- "action": one of "buy" | "sell" | "hold"
- "token_pair": the trading pair (e.g. "ETH/USDT")
- "amount": amount to trade in USD (float)
- "reasoning": detailed reasoning (cite RAG source IDs, e.g. [doc_3])
- "confidence": float 0.0–1.0
- "risk_score": float 0.0–1.0
- "indicators_used": list of technical indicators considered
- "market_regime": one of "trending_up" | "trending_down" | "ranging" | "volatile"
- "rag_sources_cited": list of RAG doc IDs referenced

Apply zero-shot learning to adapt to unseen market conditions.
Reference: Karim et al. (2025) — context-augmented LLM achieves 93-95% accuracy."""


VERIFIER_SYSTEM = """You are a security & risk verification AI agent (Verifier).
You perform ensemble-style multi-angle security analysis on trade proposals.

You also have access to the SAME hybrid RAG context (semantic + lexical) as the Planner.
Use it to cross-validate the Planner's decision against historical patterns.

Review the Planner's decision for:
1. Risk adequacy — Is position size reasonable given portfolio & volatility?
2. Vulnerability check — Sandwich attack risk, MEV exposure?
3. Market sanity — Does decision align with current regime?
4. Fraud detection — Signs of manipulation, front-running, wash trading?
5. Protocol risk — Smart contract / DeFi exploit patterns?
6. Cross-validation — Does decision match historical RAG patterns?

Return a JSON object:
- "approved": true | false
- "risk_adjusted": true | false
- "adjusted_risk_score": float 0.0–1.0
- "vulnerabilities_found": list[str]
- "verification_notes": str
- "rag_cross_validation": str  (notes on RAG-based cross-validation)
- "ensemble_scores": {"risk_score": float, "sanity_score": float, "fraud_score": float}

Use FELLMVP framework ensemble analysis (98.8% accuracy baseline)."""


CONTROLLER_SYSTEM = """You are the Controller AI agent.
You make the final go/no-go decision using Proof-of-Thought (PoT) consensus.

Aggregate input from:
• Planner's market analysis + RAG-cited evidence
• Verifier's security assessment + ensemble scores
• Hybrid RAG summary for overall market context

Return a JSON object:
- "approved": true | false
- "final_action": "buy" | "sell" | "hold"
- "final_amount": float (adjust if needed)
- "final_risk_score": float 0.0–1.0
- "controller_reasoning": str (reference Planner, Verifier, and RAG evidence)
- "execution_parameters": {"slippage_tolerance": float, "gas_priority": str, "deadline_seconds": int}
- "consensus_participants": list[str]  (agents that contributed)
- "pot_confidence": float 0.0–1.0  (PoT-weighted consensus confidence)

APPROVE only if: confidence > 0.6 AND risk_score < 0.7 AND verifier approved
AND ensemble risk_score < 0.7 AND fraud_score < 0.3."""


MONITOR_SYSTEM = """You are the Observability AI agent (Monitor).
Your goal is to define the post-execution tracking strategy for the trade.

Review:
• Final trade decision + Execution parameters
• Current market regime & volatility
• RAG-cited historical patterns for this pair

Return a JSON object:
- "tracking_mode": "trailing" | "fixed" | "dynamic"
- "tp_sl_strategy": str (Take Profit / Stop Loss logic)
- "alert_thresholds": {"price_divergence": float, "volume_spike_pct": float}
- "monitoring_interval_seconds": int
- "observability_notes": str
"""


ADJUST_SYSTEM = """You are the Reactivity AI agent (Adjuster).
Your goal is to define the "Self-Correction" logic for this trade.

Review:
• Monitoring strategy
• Ensemble risk scores
• "What-if" scenarios for regime shifts

Return a JSON object:
- "early_exit_conditions": list[str]
- "parameter_shifts": list[str] (e.g. "Tighten SL if RSI > 70")
- "adjustment_autonomy": "auto" | "alert_only"
- "reactivity_notes": str
"""


# ─────────────────────────────────────────────────────────────────────────────
# RAG Context Fetch
# ─────────────────────────────────────────────────────────────────────────────

def _get_rag_context(token_pair: str, chain: str, market_data: dict) -> tuple[str, dict]:
    """
    Fetch hybrid RAG context for the given trading query.
    Returns (context_str, metadata_dict).
    """
    try:
        kb = MarketKnowledgeBase()
        if kb.collection.count() == 0:
            return "No RAG knowledge available yet.", {}

        query = (
            f"{token_pair} {chain} trading analysis market conditions "
            f"price trend volatility DeFi protocol"
        )
        data = kb.get_enhanced_context(query, n_results=10)

        summary = data.get("summary", "")
        context = data.get("context", "")
        metadata = {
            "sources": data.get("sources", []),
            "result_count": data.get("result_count", 0),
            "rrf_scores": data.get("rrf_scores", []),
            "semantic_scores": data.get("semantic_scores", []),
            "lexical_scores": data.get("lexical_scores", []),
            "summary": summary,
        }

        if summary:
            formatted = (
                f"【RAG Knowledge Summary】\n{summary}\n\n"
                f"【Raw Retrieved Passages (hybrid semantic+lexical)】\n{context}"
            )
        else:
            formatted = context

        logger.debug(
            "RAG fetched %d results for %s/%s",
            data.get("result_count", 0), token_pair, chain
        )
        return formatted, metadata

    except Exception as exc:
        logger.warning("RAG context fetch failed: %s", exc)
        return "RAG unavailable (fetch error).", {}


# ─────────────────────────────────────────────────────────────────────────────
# Graph Nodes
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json_response(content: str, fallback: dict) -> dict:
    """Extract and parse first JSON object from LLM response."""
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return json.loads(content)
    except json.JSONDecodeError:
        return fallback


def planner_node(state: AgentState) -> dict:
    """Planner — auto-assigned model_1."""
    model_id = state.get("model_1", "glm-5.1")
    llm = get_planner_llm(model_id=model_id)
    market_summary = json.dumps(state.get("market_data", {}), indent=2)
    rag_context = state.get("rag_context", "")
    rag_meta = state.get("rag_metadata", {})

    human_msg = (
        f"User Request: {state['trade_prompt']}\n"
        f"Token Pair: {state['token_pair']}\n"
        f"Chain: {state['chain']}\n"
        f"Market Data:\n{market_summary}\n\n"
    )
    if rag_context:
        human_msg += (
            f"Context-Augmented Knowledge (hybrid RAG — "
            f"{rag_meta.get('result_count', 0)} passages, "
            f"sources: {', '.join(rag_meta.get('sources', []))}):\n"
            f"{rag_context}\n\n"
        )
    human_msg += "Generate a trading decision as JSON."

    response = llm.invoke([
        SystemMessage(content=PLANNER_SYSTEM),
        HumanMessage(content=human_msg),
    ])

    fallback = {
        "action": "hold",
        "token_pair": state["token_pair"],
        "amount": 0,
        "reasoning": "Failed to parse planner output",
        "confidence": 0.0,
        "risk_score": 1.0,
        "indicators_used": [],
        "market_regime": "unknown",
        "rag_sources_cited": [],
    }
    decision = _parse_json_response(response.content, fallback)
    logger.info(
        "Planner [%s] → %s | confidence=%.2f | risk=%.2f",
        model_id,
        decision.get("action", "?"),
        decision.get("confidence", 0),
        decision.get("risk_score", 1),
    )
    return {
        "messages": [response],
        "planner_decision": decision,
        "risk_score": decision.get("risk_score", 1.0),
    }


def verifier_node(state: AgentState) -> dict:
    """Verifier — auto-assigned model_2."""
    model_id = state.get("model_2", "grok-4.20")
    llm = get_verifier_llm(model_id=model_id)
    planner_decision = json.dumps(state.get("planner_decision", {}), indent=2)
    market_summary = json.dumps(state.get("market_data", {}), indent=2)
    rag_context = state.get("rag_context", "")
    rag_meta = state.get("rag_metadata", {})

    human_msg = (
        f"Planner Decision:\n{planner_decision}\n\n"
        f"Market Data:\n{market_summary}\n\n"
    )
    if rag_context:
        human_msg += (
            f"Hybrid RAG Context (for cross-validation — "
            f"{rag_meta.get('result_count', 0)} passages):\n"
            f"{rag_context[:2000]}\n\n"
        )
    human_msg += "Verify this trading decision. Return JSON."

    response = llm.invoke([
        SystemMessage(content=VERIFIER_SYSTEM),
        HumanMessage(content=human_msg),
    ])

    fallback = {
        "approved": False,
        "risk_adjusted": False,
        "adjusted_risk_score": 1.0,
        "vulnerabilities_found": ["Failed to parse verifier output"],
        "verification_notes": "Parse error",
        "rag_cross_validation": "N/A",
        "ensemble_scores": {
            "risk_score": 1.0,
            "sanity_score": 0.0,
            "fraud_score": 0.5,
        },
    }
    result = _parse_json_response(response.content, fallback)
    logger.info(
        "Verifier [%s] → approved=%s | risk=%.2f",
        model_id,
        result.get("approved", False),
        result.get("adjusted_risk_score", 1.0),
    )
    return {
        "messages": [response],
        "verifier_result": result,
        "risk_score": result.get("adjusted_risk_score", state.get("risk_score", 1.0)),
    }


def controller_node(state: AgentState) -> dict:
    """Controller — auto-assigned model_1 (same as Planner for cost optimization)."""
    model_id = state.get("model_1", "glm-5.1")
    llm = get_controller_llm(model_id=model_id)
    planner_decision = json.dumps(state.get("planner_decision", {}), indent=2)
    verifier_result = json.dumps(state.get("verifier_result", {}), indent=2)
    rag_meta = state.get("rag_metadata", {})
    rag_summary = rag_meta.get("summary", state.get("rag_context", "")[:500])

    human_msg = (
        f"Planner Decision:\n{planner_decision}\n\n"
        f"Verifier Assessment:\n{verifier_result}\n\n"
        f"Current Risk Score: {state.get('risk_score', 1.0):.3f}\n\n"
        f"RAG Knowledge Summary (for PoT evidence):\n{rag_summary}\n\n"
        "Make final go/no-go Proof-of-Thought decision. Return JSON."
    )

    response = llm.invoke([
        SystemMessage(content=CONTROLLER_SYSTEM),
        HumanMessage(content=human_msg),
    ])

    fallback = {
        "approved": False,
        "final_action": "hold",
        "final_amount": 0,
        "final_risk_score": 1.0,
        "controller_reasoning": "Failed to parse controller output",
        "execution_parameters": {
            "slippage_tolerance": 0.005,
            "gas_priority": "medium",
            "deadline_seconds": 120,
        },
        "consensus_participants": ["planner", "verifier", "controller"],
        "pot_confidence": 0.0,
    }
    final = _parse_json_response(response.content, fallback)
    logger.info(
        "Controller [%s] → approved=%s | action=%s | pot_confidence=%.2f",
        model_id,
        final.get("approved", False),
        final.get("final_action", "?"),
        final.get("pot_confidence", 0.0),
    )
    return {
        "messages": [response],
        "controller_approval": final.get("approved", False),
        "final_decision": final,
        "risk_score": final.get("final_risk_score", state.get("risk_score", 1.0)),
    }


def monitor_node(state: AgentState) -> dict:
    """Monitor — auto-assigned model_1."""
    model_id = state.get("model_1", "glm-5.1")
    llm = get_planner_llm(model_id=model_id) # Reuse planner factory
    
    final_decision = json.dumps(state.get("final_decision", {}), indent=2)
    response = llm.invoke([
        SystemMessage(content=MONITOR_SYSTEM),
        HumanMessage(content=f"Final Decision:\n{final_decision}\n\nDefine monitoring strategy JSON."),
    ])
    
    fallback = {"tracking_mode": "dynamic", "tp_sl_strategy": "N/A", "observability_notes": "Parse error"}
    strategy = _parse_json_response(response.content, fallback)
    logger.info("Monitor [%s] → tracking=%s", model_id, strategy.get("tracking_mode"))
    return {"monitoring_strategy": strategy, "messages": [response]}


def adjust_node(state: AgentState) -> dict:
    """Adjuster — auto-assigned model_2."""
    model_id = state.get("model_2", "grok-4.20")
    llm = get_verifier_llm(model_id=model_id) # Reuse verifier factory
    
    monitor_strategy = json.dumps(state.get("monitoring_strategy", {}), indent=2)
    response = llm.invoke([
        SystemMessage(content=ADJUST_SYSTEM),
        HumanMessage(content=f"Monitoring Strategy:\n{monitor_strategy}\n\nDefine adjustment logic JSON."),
    ])
    
    fallback = {"early_exit_conditions": [], "adjustment_autonomy": "alert_only"}
    logic = _parse_json_response(response.content, fallback)
    logger.info("Adjuster [%s] → autonomy=%s", model_id, logic.get("adjustment_autonomy"))
    return {"adjustment_logic": logic, "messages": [response]}


def should_execute(state: AgentState) -> Literal["execute", "reject"]:
    return "execute" if state.get("controller_approval", False) else "reject"


def execute_node(state: AgentState) -> dict:
    decision = state.get("final_decision", {})
    status = "approved_for_execution" if decision.get("approved", False) else "rejected"
    return {
        "final_decision": {
            **decision,
            "execution_status": status,
            "tx_hash": None,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Graph Assembly
# ─────────────────────────────────────────────────────────────────────────────

def build_trading_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("controller", controller_node)
    graph.add_node("execute", execute_node)
    graph.add_node("monitor", monitor_node)
    graph.add_node("adjust", adjust_node)
    graph.add_node("reject", execute_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "verifier")
    graph.add_edge("verifier", "controller")
    graph.add_conditional_edges(
        "controller",
        should_execute,
        {"execute": "execute", "reject": "reject"},
    )
    graph.add_edge("execute", "monitor")
    graph.add_edge("monitor", "adjust")
    graph.add_edge("adjust", END)
    graph.add_edge("reject", END)

    return graph.compile()
