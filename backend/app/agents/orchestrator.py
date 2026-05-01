"""
Trading Orchestrator — Dual-Model Auto-Assignment
===================================================
User selects 2 cloud models (model_1, model_2). The system auto-assigns:
  • model_1 → Planner + Controller  (2 invocations, 1 API key)
  • model_2 → Verifier              (1 invocation, 1 API key)

If model_1 == model_2, all 3 agents use the same model (cost optimized).
Ollama is NOT used for live/paper trading — only for backtesting.

RAG context (hybrid semantic + lexical) is pre-fetched and injected into the
initial state so every node gets the same context-augmented prompt.
"""
import logging
from app.agents.trading_graph import build_trading_graph, AgentState, _get_rag_context
from app.core.llm import resolve_agent_models

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    def __init__(self):
        self.graph = build_trading_graph()

    def _build_initial_state(
        self, prompt: str, token_pair: str, chain: str, market_data: dict,
        model_1: str = "glm-5.1",
        model_2: str = "grok-4.20",
        prediction_start_date: str | None = None,
        prediction_end_date: str | None = None,
        risk_assessment: dict | None = None,
    ) -> AgentState:
        rag_context, rag_metadata = _get_rag_context(token_pair, chain, market_data)
        
        # Auto-assign models to agents based on user's 2-model selection
        assignment = resolve_agent_models(model_1, model_2)
        
        # Build enhanced prompt with prediction window if provided
        enhanced_prompt = prompt
        if prediction_start_date or prediction_end_date:
            window_info = []
            if prediction_start_date:
                window_info.append(f"Prediction Start: {prediction_start_date}")
            if prediction_end_date:
                window_info.append(f"Prediction End: {prediction_end_date}")
            enhanced_prompt = f"[PREDICTION WINDOW]\n{' | '.join(window_info)}\n\n{prompt}"
        
        # Inject risk context into prompt if available
        if risk_assessment:
            risk_level = risk_assessment.get("risk_level", "unknown")
            risk_score = risk_assessment.get("overall_score", 0)
            recommendations = risk_assessment.get("recommendations", [])
            risk_context = f"\n\n[RISK ASSESSMENT]\nRisk Level: {risk_level.upper()}\nRisk Score: {risk_score:.1f}/100\n"
            if recommendations:
                risk_context += f"Recommendations: {' | '.join(recommendations[:3])}\n"
            enhanced_prompt = risk_context + enhanced_prompt
        
        logger.info(
            "RAG pre-fetch: %d results | sources: %s | model_1: %s | model_2: %s | "
            "assignment: Planner→%s, Verifier→%s, Controller→%s | prediction_window: %s - %s | risk_level: %s",
            rag_metadata.get("result_count", 0),
            rag_metadata.get("sources", []),
            model_1, model_2,
            assignment["planner_llm"], assignment["verifier_llm"], assignment["controller_llm"],
            prediction_start_date or "N/A",
            prediction_end_date or "N/A",
            risk_assessment.get("risk_level", "N/A") if risk_assessment else "N/A",
        )
        return {
            "messages": [],
            "market_data": market_data,
            "trade_prompt": enhanced_prompt,
            "token_pair": token_pair,
            "chain": chain,
            "rag_context": rag_context,
            "rag_metadata": rag_metadata,
            # Dual-model auto-assignment
            "model_1": model_1,
            "model_2": model_2,
            "planner_decision": {},
            "verifier_result": {},
            "controller_approval": False,
            "final_decision": {},
            "risk_score": risk_assessment.get("overall_score", 1.0) if risk_assessment else 1.0,
            "risk_assessment": risk_assessment,
        }

    async def run(
        self, prompt: str, token_pair: str, chain: str, market_data: dict,
        model_1: str = "glm-5.1",
        model_2: str = "grok-4.20",
        prediction_start_date: str | None = None,
        prediction_end_date: str | None = None,
        risk_assessment: dict | None = None,
    ) -> dict:
        initial_state = self._build_initial_state(
            prompt, token_pair, chain, market_data,
            model_1=model_1, model_2=model_2,
            prediction_start_date=prediction_start_date,
            prediction_end_date=prediction_end_date,
            risk_assessment=risk_assessment,
        )
        result = await self.graph.ainvoke(initial_state)
        return result

    def run_sync(
        self, prompt: str, token_pair: str, chain: str, market_data: dict,
        model_1: str = "glm-5.1",
        model_2: str = "grok-4.20",
        prediction_start_date: str | None = None,
        prediction_end_date: str | None = None,
        risk_assessment: dict | None = None,
    ) -> dict:
        initial_state = self._build_initial_state(
            prompt, token_pair, chain, market_data,
            model_1=model_1, model_2=model_2,
            prediction_start_date=prediction_start_date,
            prediction_end_date=prediction_end_date,
            risk_assessment=risk_assessment,
        )
        result = self.graph.invoke(initial_state)
        return result
