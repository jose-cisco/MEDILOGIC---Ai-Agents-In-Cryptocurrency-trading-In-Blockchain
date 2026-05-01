from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class ChainType(str, Enum):
    ETHEREUM = "ethereum"
    SOLANA = "solana"


class CloudLLMProvider(str, Enum):
    """Cloud provider models only — Ollama is reserved for backtesting.
    
    Model routing (direct provider connection):
    - glm-5.1: GLM reasoning model (io.net) - TEXT ONLY
    - grok-4.20-0309: xAI Grok 4.20 0309 Reasoning v1 - TEXT + IMAGE
    - grok-4.20-0309-v2: xAI Grok 4.20 0309 Reasoning v2 - TEXT + IMAGE
    - mimo-v2-pro: Xiaomi MiMo-V2-Pro reasoning model - TEXT ONLY
    - qwen-3.6-plus: Alibaba Qwen 3.6 Plus reasoning model - TEXT ONLY
    
    Image Input Support:
    - ONLY Grok 4.20 0309 (v1 and v2) support image input
    - Other models will ignore image_url if provided
    
    Each agent can independently use any of these models.
    """
    GLM_5_1 = "glm-5.1"
    GROK_4_20_0309 = "grok-4.20-0309"  # v1 - supports IMAGE INPUT
    GROK_4_20_0309_V2 = "grok-4.20-0309-v2"  # v2 - supports IMAGE INPUT
    MIMO_V2_PRO = "mimo-v2-pro"
    QWEN_3_6_PLUS = "qwen-3.6-plus"
    
    # Legacy aliases for backward compatibility
    GLM_5 = "glm-5.1"  # Alias to GLM-5.1
    GROK_4_20 = "grok-4.20-0309"  # Alias to Grok 4.20 0309 v1
    
    @classmethod
    def supports_image(cls, model_id: str) -> bool:
        """Check if a model supports image input.
        
        ONLY Grok 4.20 0309 (v1 and v2) support image input.
        All other models are TEXT ONLY.
        """
        return model_id in ("grok-4.20-0309", "grok-4.20-0309-v2")


class TradeRequest(BaseModel):
    prompt: str
    chain: ChainType = ChainType.ETHEREUM
    token_pair: str = "ETH/USDT"
    prediction_start_date: Optional[str] = None
    prediction_end_date: Optional[str] = None
    max_position_usd: float = 1000.0
    agent_id: str = "default-trader"
    
    # ─── Image Input (Grok 4.2 Only) ───────────────────────────────────────────
    # IMPORTANT: Image input is ONLY supported by Grok 4.20 0309 (v1 and v2).
    # If you provide an image_url with other models (glm-5.1, mimo-v2-pro, qwen-3.6-plus),
    # the image will be IGNORED and only text will be processed.
    # 
    # Supported image formats: JPEG, PNG, GIF, WebP
    # Image URL must be publicly accessible or base64 data URL.
    image_url: Optional[str] = Field(
        default=None,
        description="URL of image to analyze. ONLY WORKS WITH Grok 4.20 0309 (v1 or v2). "
                    "Other models will IGNORE this field. "
                    "Supported: JPEG, PNG, GIF, WebP. Can be HTTP URL or base64 data URL."
    )
    
    # ─── Single Model Selection ─────────────────────────────────────────────
    # User selects ONE model that is used by ALL agents.
    # This single model serves Planner, Verifier, Controller, Monitor, and Adjuster.
    # Available models: glm-5.1, grok-4.20-0309 (v1), grok-4.20-0309-v2, mimo-v2-pro, qwen-3.6-plus
    # Default: GLM-5.1 (good all-around for all agent roles)
    # Ollama is NOT available for live trading — only for backtesting.
    #
    # IMAGE SUPPORT: Only grok-4.20-0309 and grok-4.20-0309-v2 support image input!
    
    model: Optional[CloudLLMProvider] = Field(
        default=None,
        description="Single model used by ALL agents (Planner, Verifier, Controller, Monitor, Adjuster). "
                    "Options: glm-5.1, grok-4.20-0309 (v1), grok-4.20-0309-v2, mimo-v2-pro, qwen-3.6-plus. "
                    "Default: glm-5.1. "
                    "NOTE: Only grok-4.20-0309 and grok-4.20-0309-v2 support image input!"
    )
    
    # ─── Legacy Fields (Backward Compatibility) ─────────────────────────────
    # Legacy dual-model fields are kept for backward compatibility.
    # model_1 → All agents (same as 'model' field now)
    # model_2 → Also all agents (ignored if 'model' is set)
    model_1: Optional[CloudLLMProvider] = Field(
        default=None,
        description="Legacy: Same as 'model' field. Use 'model' instead."
    )
    model_2: Optional[CloudLLMProvider] = Field(
        default=None,
        description="Legacy: Ignored. Use 'model' for single model selection."
    )
    
    # ─── Agent Governance & DID ───────────────────────────────────────────────
    did: str = ""
    request_nonce: str = ""
    request_timestamp: int = 0
    agent_signature: str = ""
    
    def get_resolved_models(self) -> dict[str, str]:
        """
        Resolve model assignment for all agents.
        
        Priority:
        1. If 'model' is set, use it for ALL agents
        2. If model_1 is set (legacy), use it for ALL agents
        3. Otherwise, use default (GLM-5.1)
        
        Returns:
            Dict with same model for all agents
        """
        # Default model for all agents
        default_model = "glm-5.1"
        
        # Priority 1: New single 'model' field
        if self.model is not None:
            chosen_model = self.model.value
        # Priority 2: Legacy model_1 field
        elif self.model_1 is not None:
            chosen_model = self.model_1.value
        # Priority 3: Default
        else:
            chosen_model = default_model
        
        # Return same model for all agents
        return {
            "planner_model": chosen_model,
            "verifier_model": chosen_model,
            "controller_model": chosen_model,
            "monitor_model": chosen_model,
            "adjuster_model": chosen_model,
        }


class TradeDecision(BaseModel):
    action: TradeAction
    token_pair: str
    amount: float
    reasoning: str
    confidence: float
    risk_score: float
    # Dual-LLM graph extended fields
    market_regime: Optional[str] = None
    indicators_used: list[str] = Field(default_factory=list)
    rag_sources_cited: list[str] = Field(default_factory=list)
    pot_confidence: Optional[float] = None


class AgentTrace(BaseModel):
    """Multi-agent execution trace for transparency."""
    planner_decision: Optional[dict[str, Any]] = Field(
        default=None,
        description="Planner agent output: action, confidence, risk_score, reasoning",
    )
    verifier_result: Optional[dict[str, Any]] = Field(
        default=None,
        description="Verifier agent output: approved, adjusted_risk_score, vulnerabilities",
    )
    final_decision: Optional[dict[str, Any]] = Field(
        default=None,
        description="Controller agent output: final_action, final_amount, pot_confidence",
    )
    monitoring_strategy: Optional[dict[str, Any]] = Field(
        default=None,
        description="Monitor agent output: tracking_mode, tp_sl_strategy, alert_thresholds",
    )
    adjustment_logic: Optional[dict[str, Any]] = Field(
        default=None,
        description="Adjuster agent output: early_exit_conditions, parameter_shifts",
    )


class TradeResult(BaseModel):
    success: bool
    tx_hash: Optional[str] = None
    action: TradeAction
    token_pair: str
    amount: float
    price: float
    reasoning: str
    confidence: float
    timestamp: str
    # RAG metadata surfaced from hybrid retrieval
    rag_metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Hybrid RAG retrieval metadata: sources, rrf_scores, summary, result_count",
    )
    governance_metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Agent governance checks, semantic signal score, and audit event hash",
    )
    x402_metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="x402 payment protocol metadata: payment_required, payment_verified, tx_hash, amount, resource",
    )
    # Multi-agent trace for transparency
    agent_trace: Optional[AgentTrace] = Field(
        default=None,
        description="Multi-agent execution trace: planner, verifier, controller, monitor, adjuster outputs",
    )
    # Risk assessment metadata
    risk_metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Risk assessment: overall_score, risk_level, component scores, recommendations",
    )


class BacktestRequest(BaseModel):
    strategy: str
    token_pair: str = "ETH/USDT"
    start_date: str
    end_date: str
    initial_capital: float = 10000.0
    chain: ChainType = ChainType.ETHEREUM


class BacktestResult(BaseModel):
    strategy: str
    token_pair: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    winning_trades: int = 0
    losing_trades: int = 0
    avg_trade_return_pct: float = 0.0
    profit_factor: float = 0.0
    data_source: str = "synthetic"
    trades: list
    # RAG metadata surfaced from hybrid retrieval (same as trading)
    rag_metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Hybrid RAG retrieval metadata for backtesting: sources, rrf_scores, summary, result_count",
    )
    x402_metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="x402 payment metadata — backtesting is ALWAYS exempt from x402 payments",
    )


class AgentStatus(BaseModel):
    agent_name: str
    status: str
    last_action: Optional[str] = None
    total_decisions: int = 0
    successful_trades: int = 0


class RiskAssessRequest(BaseModel):
    """Request schema for risk assessment endpoint."""
    # Required fields
    price: float = Field(..., gt=0, description="Current price in USD")
    volume_24h: float = Field(..., gt=0, description="24-hour trading volume in USD")
    
    # Optional market data
    token_pair: str = Field(default="ETH/USDT", description="Trading pair symbol")
    chain: str = Field(default="ethereum", description="Blockchain network")
    position_size_usd: float = Field(default=1000.0, ge=0, description="Proposed position size")
    portfolio_value_usd: Optional[float] = Field(default=None, ge=0, description="Total portfolio value")
    volatility_24h: Optional[float] = Field(default=None, ge=0, description="24h annualized volatility %")
    price_change_24h: Optional[float] = Field(default=None, description="24h price change %")
    rsi_14: Optional[float] = Field(default=None, ge=0, le=100, description="14-period RSI")
    macd_signal: Optional[str] = Field(default=None, description="MACD signal: bullish/bearish/neutral")
    sma_7: Optional[float] = Field(default=None, ge=0, description="7-period SMA")
    sma_14: Optional[float] = Field(default=None, ge=0, description="14-period SMA")
    sma_30: Optional[float] = Field(default=None, ge=0, description="30-period SMA")
    tvl: Optional[float] = Field(default=None, ge=0, description="Total Value Locked (DeFi)")
    liquidity_depth: Optional[float] = Field(default=None, ge=0, description="Order book depth in USD")
    slippage_estimate: Optional[float] = Field(default=None, ge=0, description="Expected slippage %")
    
    # On-chain data (optional)
    contract_verified: bool = Field(default=True, description="Contract is verified")
    audit_status: Optional[str] = Field(default=None, description="Audit status: audited/unaudited/pending")
    contract_age_days: Optional[int] = Field(default=None, ge=0, description="Contract age in days")
    exploit_history: bool = Field(default=False, description="History of exploits")
    governance_decentralized: bool = Field(default=True, description="Governance is decentralized")
    multisig_threshold: Optional[int] = Field(default=None, ge=1, description="Multisig threshold")


class RiskAssessResult(BaseModel):
    """Response schema for risk assessment."""
    overall_score: float = Field(..., ge=0, le=100, description="Overall risk score 0-100")
    risk_level: str = Field(..., description="Risk level: low/moderate/high/critical")
    volatility_risk: float = Field(..., ge=0, le=100, description="Volatility risk score")
    drawdown_risk: float = Field(..., ge=0, le=100, description="Drawdown risk score")
    liquidity_risk: float = Field(..., ge=0, le=100, description="Liquidity risk score")
    onchain_risk: float = Field(..., ge=0, le=100, description="On-chain risk score")
    factors: dict[str, Any] = Field(default_factory=dict, description="Risk factor breakdown")
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations")
    timestamp: str = Field(..., description="Assessment timestamp ISO format")


class RiskMetricsResult(BaseModel):
    """Response schema for risk metrics dashboard."""
    total_trades: int = Field(..., description="Total number of trades")
    winning_trades: int = Field(..., description="Number of winning trades")
    losing_trades: int = Field(..., description="Number of losing trades")
    win_rate: float = Field(..., ge=0, le=1, description="Win rate (0.0 to 1.0)")
    avg_risk_score: float = Field(..., ge=0, le=100, description="Average risk score")
    sharpe_ratio: Optional[float] = Field(default=None, description="Sharpe ratio (annualized)")
    max_drawdown: float = Field(..., ge=0, le=1, description="Maximum drawdown (0.0 to 1.0)")
    risk_adjusted_return: Optional[float] = Field(default=None, description="Risk-adjusted return")
    win_rate_by_level: dict[str, float] = Field(default_factory=dict, description="Win rate by risk level")
    avg_position_multiplier: float = Field(..., ge=0, le=1, description="Average position multiplier")
    blocked_trades: int = Field(..., description="Number of blocked trades (CRITICAL risk)")
    period_days: int = Field(..., description="Analysis period in days")


class RiskCalibrationResult(BaseModel):
    """Response schema for risk calibration suggestions."""
    current_weights: dict[str, float] = Field(..., description="Current risk component weights")
    suggested_weights: dict[str, float] = Field(..., description="Suggested weight adjustments")
    average_component_scores: dict[str, float] = Field(default_factory=dict, description="Average scores by component")
    reasoning: list[str] = Field(default_factory=list, description="Explanation for suggestions")
