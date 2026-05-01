"""
LLM Auto-Tune System
====================
Allows LLMs to self-configure optimal parameters based on task characteristics.

The system analyzes:
- Task type (analysis, security, consensus, generation)
- Input complexity (simple, moderate, complex)
- Risk level (low, medium, high)
- Required precision (factual, creative, balanced)

Then automatically selects optimal:
- temperature (0.0 - 1.0)
- top_p (0.1 - 1.0)
- max_tokens (256 - 8192)
- frequency_penalty (0.0 - 1.0)
- presence_penalty (0.0 - 1.0)
"""
import logging
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task type classification."""
    MARKET_ANALYSIS = "market_analysis"
    SECURITY_AUDIT = "security_audit"
    CONSENSUS = "consensus"
    TRADE_DECISION = "trade_decision"
    RISK_ASSESSMENT = "risk_assessment"
    RAG_SYNTHESIS = "rag_synthesis"
    VULNERABILITY_SCAN = "vulnerability_scan"
    GOVERNANCE_REVIEW = "governance_review"
    CODE_GENERATION = "code_generation"
    SUMMARY = "summary"


class ComplexityLevel(Enum):
    """Input complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class RiskLevel(Enum):
    """Risk level for the task."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PrecisionMode(Enum):
    """Required precision mode."""
    FACTUAL = "factual"      # Need precise, accurate outputs
    BALANCED = "balanced"    # Balance between accuracy and creativity
    CREATIVE = "creative"    # Allow more creative exploration


@dataclass
class LLMParameters:
    """Optimized LLM parameters."""
    temperature: float
    top_p: float
    max_tokens: int
    frequency_penalty: float
    presence_penalty: float
    reasoning: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "reasoning": self.reasoning,
        }


# ─── Pre-optimized parameter profiles by task type ───────────────────────────

TASK_PROFILES: Dict[TaskType, Dict[ComplexityLevel, LLMParameters]] = {
    # PLANNER: Market analysis needs moderate creativity to explore scenarios
    TaskType.MARKET_ANALYSIS: {
        ComplexityLevel.SIMPLE: LLMParameters(
            temperature=0.2, top_p=0.85, max_tokens=2048,
            frequency_penalty=0.1, presence_penalty=0.1, reasoning=True
        ),
        ComplexityLevel.MODERATE: LLMParameters(
            temperature=0.3, top_p=0.90, max_tokens=4096,
            frequency_penalty=0.15, presence_penalty=0.15, reasoning=True
        ),
        ComplexityLevel.COMPLEX: LLMParameters(
            temperature=0.35, top_p=0.92, max_tokens=6144,
            frequency_penalty=0.2, presence_penalty=0.2, reasoning=True
        ),
    },
    
    # VERIFIER: Security audits need low temperature for precision
    TaskType.SECURITY_AUDIT: {
        ComplexityLevel.SIMPLE: LLMParameters(
            temperature=0.0, top_p=0.80, max_tokens=1536,
            frequency_penalty=0.2, presence_penalty=0.2, reasoning=True
        ),
        ComplexityLevel.MODERATE: LLMParameters(
            temperature=0.05, top_p=0.82, max_tokens=2048,
            frequency_penalty=0.25, presence_penalty=0.25, reasoning=True
        ),
        ComplexityLevel.COMPLEX: LLMParameters(
            temperature=0.1, top_p=0.85, max_tokens=3072,
            frequency_penalty=0.3, presence_penalty=0.3, reasoning=True
        ),
    },
    
    # CONTROLLER: Consensus needs very low temperature for deterministic decisions
    TaskType.CONSENSUS: {
        ComplexityLevel.SIMPLE: LLMParameters(
            temperature=0.0, top_p=0.75, max_tokens=1024,
            frequency_penalty=0.0, presence_penalty=0.0, reasoning=True
        ),
        ComplexityLevel.MODERATE: LLMParameters(
            temperature=0.0, top_p=0.80, max_tokens=1536,
            frequency_penalty=0.1, presence_penalty=0.1, reasoning=True
        ),
        ComplexityLevel.COMPLEX: LLMParameters(
            temperature=0.05, top_p=0.82, max_tokens=2048,
            frequency_penalty=0.15, presence_penalty=0.15, reasoning=True
        ),
    },
    
    # TRADE_DECISION: Final decisions need precision
    TaskType.TRADE_DECISION: {
        ComplexityLevel.SIMPLE: LLMParameters(
            temperature=0.1, top_p=0.82, max_tokens=1536,
            frequency_penalty=0.1, presence_penalty=0.1, reasoning=True
        ),
        ComplexityLevel.MODERATE: LLMParameters(
            temperature=0.15, top_p=0.85, max_tokens=2048,
            frequency_penalty=0.15, presence_penalty=0.15, reasoning=True
        ),
        ComplexityLevel.COMPLEX: LLMParameters(
            temperature=0.2, top_p=0.88, max_tokens=3072,
            frequency_penalty=0.2, presence_penalty=0.2, reasoning=True
        ),
    },
    
    # RISK_ASSESSMENT: Risk needs precision and consistency
    TaskType.RISK_ASSESSMENT: {
        ComplexityLevel.SIMPLE: LLMParameters(
            temperature=0.0, top_p=0.80, max_tokens=1024,
            frequency_penalty=0.3, presence_penalty=0.2, reasoning=True
        ),
        ComplexityLevel.MODERATE: LLMParameters(
            temperature=0.05, top_p=0.82, max_tokens=1536,
            frequency_penalty=0.3, presence_penalty=0.25, reasoning=True
        ),
        ComplexityLevel.COMPLEX: LLMParameters(
            temperature=0.1, top_p=0.85, max_tokens=2048,
            frequency_penalty=0.35, presence_penalty=0.3, reasoning=True
        ),
    },
    
    # RAG_SYNTHESIS: Needs factual accuracy
    TaskType.RAG_SYNTHESIS: {
        ComplexityLevel.SIMPLE: LLMParameters(
            temperature=0.0, top_p=0.80, max_tokens=512,
            frequency_penalty=0.3, presence_penalty=0.2, reasoning=False
        ),
        ComplexityLevel.MODERATE: LLMParameters(
            temperature=0.05, top_p=0.82, max_tokens=768,
            frequency_penalty=0.35, presence_penalty=0.25, reasoning=False
        ),
        ComplexityLevel.COMPLEX: LLMParameters(
            temperature=0.1, top_p=0.85, max_tokens=1024,
            frequency_penalty=0.4, presence_penalty=0.3, reasoning=True
        ),
    },
    
    # VULNERABILITY_SCAN: Security needs very low temperature
    TaskType.VULNERABILITY_SCAN: {
        ComplexityLevel.SIMPLE: LLMParameters(
            temperature=0.0, top_p=0.75, max_tokens=2048,
            frequency_penalty=0.2, presence_penalty=0.2, reasoning=True
        ),
        ComplexityLevel.MODERATE: LLMParameters(
            temperature=0.0, top_p=0.78, max_tokens=3072,
            frequency_penalty=0.25, presence_penalty=0.25, reasoning=True
        ),
        ComplexityLevel.COMPLEX: LLMParameters(
            temperature=0.05, top_p=0.80, max_tokens=4096,
            frequency_penalty=0.3, presence_penalty=0.3, reasoning=True
        ),
    },
    
    # GOVERNANCE_REVIEW: Balanced approach
    TaskType.GOVERNANCE_REVIEW: {
        ComplexityLevel.SIMPLE: LLMParameters(
            temperature=0.15, top_p=0.82, max_tokens=1024,
            frequency_penalty=0.2, presence_penalty=0.2, reasoning=True
        ),
        ComplexityLevel.MODERATE: LLMParameters(
            temperature=0.2, top_p=0.85, max_tokens=1536,
            frequency_penalty=0.25, presence_penalty=0.25, reasoning=True
        ),
        ComplexityLevel.COMPLEX: LLMParameters(
            temperature=0.25, top_p=0.88, max_tokens=2048,
            frequency_penalty=0.3, presence_penalty=0.3, reasoning=True
        ),
    },
    
    # CODE_GENERATION: Needs precision but some creativity
    TaskType.CODE_GENERATION: {
        ComplexityLevel.SIMPLE: LLMParameters(
            temperature=0.2, top_p=0.85, max_tokens=2048,
            frequency_penalty=0.0, presence_penalty=0.0, reasoning=True
        ),
        ComplexityLevel.MODERATE: LLMParameters(
            temperature=0.25, top_p=0.88, max_tokens=4096,
            frequency_penalty=0.05, presence_penalty=0.05, reasoning=True
        ),
        ComplexityLevel.COMPLEX: LLMParameters(
            temperature=0.3, top_p=0.90, max_tokens=6144,
            frequency_penalty=0.1, presence_penalty=0.1, reasoning=True
        ),
    },
    
    # SUMMARY: Concise, factual
    TaskType.SUMMARY: {
        ComplexityLevel.SIMPLE: LLMParameters(
            temperature=0.0, top_p=0.75, max_tokens=256,
            frequency_penalty=0.4, presence_penalty=0.3, reasoning=False
        ),
        ComplexityLevel.MODERATE: LLMParameters(
            temperature=0.05, top_p=0.78, max_tokens=384,
            frequency_penalty=0.45, presence_penalty=0.35, reasoning=False
        ),
        ComplexityLevel.COMPLEX: LLMParameters(
            temperature=0.1, top_p=0.80, max_tokens=512,
            frequency_penalty=0.5, presence_penalty=0.4, reasoning=False
        ),
    },
}


# ─── Risk-based parameter adjustments ───────────────────────────────────────

RISK_ADJUSTMENTS = {
    RiskLevel.LOW: {"temperature_delta": 0.05, "top_p_delta": 0.02},
    RiskLevel.MEDIUM: {"temperature_delta": 0.0, "top_p_delta": 0.0},
    RiskLevel.HIGH: {"temperature_delta": -0.1, "top_p_delta": -0.05},
}


# ─── Model-specific optimizations ────────────────────────────────────────────

MODEL_SPECIFIC_TUNING = {
    # GLM-5.1: Good at reasoning, handles complex tasks well
    "glm-5.1": {
        "temperature_multiplier": 0.9,  # Slightly lower temp for GLM
        "top_p_multiplier": 1.0,
        "reasoning_optimal": True,
    },
    # Grok 4.20 0309: Excellent for security and verification
    "grok-4.20-0309": {
        "temperature_multiplier": 0.85,  # Lower temp for precision
        "top_p_multiplier": 0.95,
        "reasoning_optimal": True,
    },
    # MiMo-V2-Pro: Xiaomi's reasoning model
    "mimo-v2-pro": {
        "temperature_multiplier": 0.9,
        "top_p_multiplier": 1.0,
        "reasoning_optimal": True,
    },
    # Qwen 3.6 Plus: Alibaba's reasoning model
    "qwen-3.6-plus": {
        "temperature_multiplier": 0.95,
        "top_p_multiplier": 1.0,
        "reasoning_optimal": True,
    },
}


class LLMAutoTuner:
    """
    Auto-tunes LLM parameters based on task characteristics.
    
    Usage:
        tuner = LLMAutoTuner()
        params = tuner.get_optimal_params(
            task_type=TaskType.SECURITY_AUDIT,
            model_id="grok-4.20-0309",
            complexity=ComplexityLevel.COMPLEX,
            risk_level=RiskLevel.HIGH,
        )
    """
    
    def __init__(self):
        self._optimization_history: List[Dict] = []
        self._performance_metrics: Dict[str, Dict] = {}
    
    def detect_complexity(self, input_text: str, context_size: int = 0) -> ComplexityLevel:
        """
        Automatically detect input complexity.
        
        Factors:
        - Text length
        - Number of distinct concepts
        - Presence of technical terms
        - Context size from RAG
        """
        text_len = len(input_text)
        word_count = len(input_text.split())
        
        # Simple heuristics
        technical_indicators = [
            'contract', 'function', 'security', 'vulnerability', 'exploit',
            'algorithm', 'optimization', 'protocol', 'mechanism', 'architecture',
            'impermanent loss', 'slippage', 'liquidity', 'volatility', 'arbitrage'
        ]
        
        technical_count = sum(1 for term in technical_indicators if term.lower() in input_text.lower())
        
        # Calculate complexity score
        score = 0
        if text_len > 2000:
            score += 2
        elif text_len > 500:
            score += 1
        
        if word_count > 500:
            score += 2
        elif word_count > 150:
            score += 1
        
        if technical_count > 5:
            score += 2
        elif technical_count > 2:
            score += 1
        
        if context_size > 5:
            score += 1
        
        # Determine complexity level
        if score >= 5:
            return ComplexityLevel.COMPLEX
        elif score >= 2:
            return ComplexityLevel.MODERATE
        return ComplexityLevel.SIMPLE
    
    def detect_risk_level(
        self,
        position_size_usd: float = 0,
        leverage: float = 1.0,
        volatility: float = 0.0,
        is_live: bool = False,
    ) -> RiskLevel:
        """
        Detect risk level based on trading parameters.
        """
        score = 0
        
        # Position size risk
        if position_size_usd > 10000:
            score += 2
        elif position_size_usd > 1000:
            score += 1
        
        # Leverage risk
        if leverage > 10:
            score += 2
        elif leverage > 3:
            score += 1
        
        # Volatility risk
        if volatility > 0.1:  # 10% daily volatility
            score += 2
        elif volatility > 0.05:
            score += 1
        
        # Live mode adds risk
        if is_live:
            score += 1
        
        if score >= 4:
            return RiskLevel.HIGH
        elif score >= 2:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
    
    def get_optimal_params(
        self,
        task_type: TaskType,
        model_id: str,
        complexity: Optional[ComplexityLevel] = None,
        risk_level: Optional[RiskLevel] = None,
        input_text: Optional[str] = None,
        position_size_usd: float = 0,
        leverage: float = 1.0,
        volatility: float = 0.0,
        is_live: bool = False,
        custom_overrides: Optional[Dict[str, Any]] = None,
    ) -> LLMParameters:
        """
        Get optimal parameters for the given task and model.
        
        Args:
            task_type: Type of task being performed
            model_id: LLM model identifier
            complexity: Input complexity (auto-detected if None)
            risk_level: Risk level (auto-detected if None)
            input_text: Input text for complexity detection
            position_size_usd: Position size in USD
            leverage: Trading leverage
            volatility: Market volatility
            is_live: Whether in live trading mode
            custom_overrides: Custom parameter overrides
        
        Returns:
            Optimized LLMParameters
        """
        # Auto-detect complexity if not provided
        if complexity is None and input_text:
            complexity = self.detect_complexity(input_text)
        elif complexity is None:
            complexity = ComplexityLevel.MODERATE
        
        # Auto-detect risk level if not provided
        if risk_level is None:
            risk_level = self.detect_risk_level(
                position_size_usd, leverage, volatility, is_live
            )
        
        # Get base parameters for task and complexity
        base_params = TASK_PROFILES.get(task_type, TASK_PROFILES[TaskType.TRADE_DECISION])
        params = base_params.get(complexity, base_params[ComplexityLevel.MODERATE])
        
        # Apply risk adjustments
        risk_adj = RISK_ADJUSTMENTS.get(risk_level, RISK_ADJUSTMENTS[RiskLevel.MEDIUM])
        temperature = max(0.0, params.temperature + risk_adj["temperature_delta"])
        top_p = max(0.1, min(1.0, params.top_p + risk_adj["top_p_delta"]))
        
        # Apply model-specific tuning
        model_tuning = MODEL_SPECIFIC_TUNING.get(model_id, {})
        temp_mult = model_tuning.get("temperature_multiplier", 1.0)
        top_p_mult = model_tuning.get("top_p_multiplier", 1.0)
        
        temperature = temperature * temp_mult
        top_p = top_p * top_p_mult
        
        # Ensure bounds
        temperature = max(0.0, min(1.0, temperature))
        top_p = max(0.1, min(1.0, top_p))
        
        # Create final parameters
        final_params = LLMParameters(
            temperature=round(temperature, 3),
            top_p=round(top_p, 3),
            max_tokens=params.max_tokens,
            frequency_penalty=params.frequency_penalty,
            presence_penalty=params.presence_penalty,
            reasoning=params.reasoning,
        )
        
        # Apply custom overrides
        if custom_overrides:
            for key, value in custom_overrides.items():
                if hasattr(final_params, key):
                    setattr(final_params, key, value)
        
        # Log optimization
        logger.info(
            f"Auto-tuned parameters for {task_type.value} | "
            f"Model: {model_id} | "
            f"Complexity: {complexity.value} | "
            f"Risk: {risk_level.value} | "
            f"temp={final_params.temperature}, top_p={final_params.top_p}, "
            f"max_tokens={final_params.max_tokens}"
        )
        
        return final_params
    
    def get_agent_params(
        self,
        agent_role: str,
        model_id: str,
        input_text: str = "",
        market_data: Optional[Dict] = None,
        is_live: bool = False,
    ) -> LLMParameters:
        """
        Get optimized parameters for a specific agent role.
        
        Args:
            agent_role: 'planner', 'verifier', 'controller', 'monitor', 'adjuster'
            model_id: LLM model identifier
            input_text: Input text for analysis
            market_data: Market data for risk detection
            is_live: Whether in live trading mode
        
        Returns:
            Optimized LLMParameters
        """
        # Map agent roles to task types
        agent_task_map = {
            "planner": TaskType.MARKET_ANALYSIS,
            "verifier": TaskType.SECURITY_AUDIT,
            "controller": TaskType.CONSENSUS,
            "monitor": TaskType.RISK_ASSESSMENT,
            "adjuster": TaskType.TRADE_DECISION,
            "rag": TaskType.RAG_SYNTHESIS,
            "vulnerability_scanner": TaskType.VULNERABILITY_SCAN,
            "governance": TaskType.GOVERNANCE_REVIEW,
        }
        
        task_type = agent_task_map.get(agent_role.lower(), TaskType.TRADE_DECISION)
        
        # Extract risk parameters from market data
        position_size = 0
        leverage = 1.0
        volatility = 0.0
        
        if market_data:
            position_size = market_data.get("position_size_usd", 0)
            leverage = market_data.get("leverage", 1.0)
            volatility = market_data.get("volatility", 0.0)
        
        return self.get_optimal_params(
            task_type=task_type,
            model_id=model_id,
            input_text=input_text,
            position_size_usd=position_size,
            leverage=leverage,
            volatility=volatility,
            is_live=is_live,
        )
    
    def record_performance(
        self,
        model_id: str,
        params: LLMParameters,
        task_type: TaskType,
        success: bool,
        latency_ms: float,
        quality_score: Optional[float] = None,
    ):
        """
        Record performance metrics for future optimization.
        
        Args:
            model_id: Model identifier
            params: Parameters used
            task_type: Task type
            success: Whether the task succeeded
            latency_ms: Latency in milliseconds
            quality_score: Optional quality score (0.0 - 1.0)
        """
        record = {
            "model_id": model_id,
            "params": params.to_dict(),
            "task_type": task_type.value,
            "success": success,
            "latency_ms": latency_ms,
            "quality_score": quality_score,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._optimization_history.append(record)
        
        # Update performance metrics
        if model_id not in self._performance_metrics:
            self._performance_metrics[model_id] = {
                "total_calls": 0,
                "successful_calls": 0,
                "avg_latency_ms": 0,
                "avg_quality": 0,
            }
        
        metrics = self._performance_metrics[model_id]
        metrics["total_calls"] += 1
        if success:
            metrics["successful_calls"] += 1
        metrics["avg_latency_ms"] = (
            (metrics["avg_latency_ms"] * (metrics["total_calls"] - 1) + latency_ms)
            / metrics["total_calls"]
        )
        
        if quality_score is not None:
            metrics["avg_quality"] = (
                (metrics["avg_quality"] * (metrics["total_calls"] - 1) + quality_score)
                / metrics["total_calls"]
            )
    
    def get_performance_report(self, model_id: Optional[str] = None) -> Dict:
        """Get performance metrics for a model or all models."""
        if model_id:
            return self._performance_metrics.get(model_id, {})
        return self._performance_metrics


# ─── Singleton instance ─────────────────────────────────────────────────────

_auto_tuner: Optional[LLMAutoTuner] = None


def get_auto_tuner() -> LLMAutoTuner:
    """Get or create the auto-tuner singleton."""
    global _auto_tuner
    if _auto_tuner is None:
        _auto_tuner = LLMAutoTuner()
    return _auto_tuner


# ─── Convenience functions ───────────────────────────────────────────────────

def auto_tune_planner(model_id: str, input_text: str = "", market_data: Optional[Dict] = None, is_live: bool = False) -> LLMParameters:
    """Get optimized parameters for Planner agent."""
    return get_auto_tuner().get_agent_params("planner", model_id, input_text, market_data, is_live)


def auto_tune_verifier(model_id: str, input_text: str = "", market_data: Optional[Dict] = None, is_live: bool = False) -> LLMParameters:
    """Get optimized parameters for Verifier agent."""
    return get_auto_tuner().get_agent_params("verifier", model_id, input_text, market_data, is_live)


def auto_tune_controller(model_id: str, input_text: str = "", market_data: Optional[Dict] = None, is_live: bool = False) -> LLMParameters:
    """Get optimized parameters for Controller agent."""
    return get_auto_tuner().get_agent_params("controller", model_id, input_text, market_data, is_live)


def auto_tune_monitor(model_id: str, input_text: str = "", market_data: Optional[Dict] = None, is_live: bool = False) -> LLMParameters:
    """Get optimized parameters for Monitor agent."""
    return get_auto_tuner().get_agent_params("monitor", model_id, input_text, market_data, is_live)


def auto_tune_adjuster(model_id: str, input_text: str = "", market_data: Optional[Dict] = None, is_live: bool = False) -> LLMParameters:
    """Get optimized parameters for Adjuster agent."""
    return get_auto_tuner().get_agent_params("adjuster", model_id, input_text, market_data, is_live)


# ─── Import for type hints ───────────────────────────────────────────────────

from datetime import datetime
from typing import List