from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Local fallback ──────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "glm-5"
    # Backtesting should always run on Ollama cloud/local endpoint.
    BACKTEST_OLLAMA_BASE_URL: str = ""
    BACKTEST_OLLAMA_MODEL: str = "glm-5.1"
    BACKTEST_FORCE_OLLAMA_CLOUD: bool = True
    BACKTEST_DATASET_PATH: str = "./data/backtest_dataset.jsonl"

    # ── io.net — GLM-5.1 Reasoning (Planner / Controller) ──────────────────
    IONET_API_KEY: str = ""
    IONET_BASE_URL: str = "https://api.intelligence.io.solutions/api/v1"
    # Correct model slug on io.net for GLM-5.1 Reasoning
    IONET_MODEL: str = "THUDM/GLM-Z1-32B-0414"

    # ── x.ai — Grok 4.20 Reasoning (Verifier) ──────────────────────────────
    XAI_API_KEY: str = ""
    XAI_BASE_URL: str = "https://api.x.ai/v1"
    # Grok 4.20 Beta Reasoning model (March 2025 release)
    # Docs: https://docs.x.ai/developers/models/grok-4.20-beta-0309-reasoning
    # Available variants:
    #   - grok-4.20-beta-0309-reasoning (v1 - specific version)
    #   - grok-4.20-0309-v2-reasoning (v2 reasoning variant, enhanced)
    #   - grok-4.20-reasoning-latest (always updated)
    #   - grok-4.20-beta-latest-reasoning (latest beta with reasoning)
    XAI_MODEL_V1: str = "grok-4.20-beta-0309-reasoning"  # v1
    XAI_MODEL_V2: str = "grok-4.20-0309-v2-reasoning"   # v2 (default)
    XAI_MODEL: str = "grok-4.20-0309-v2-reasoning"      # Default to v2

    # ── Xiaomi — MiMo-V2-Pro Reasoning ──────────────────────────────────────
    XIAOMI_API_KEY: str = ""
    XIAOMI_BASE_URL: str = "https://api.xiaomi.ai/v1"
    XIAOMI_MODEL: str = "mimo-v2-pro"

    # ── Alibaba Cloud — Qwen 3.6 Plus Reasoning ─────────────────────────────
    ALIBABA_API_KEY: str = ""
    ALIBABA_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ALIBABA_MODEL: str = "qwen-3.6-plus"

    # ── OpenRouter — Advanced Models & Reasoning ──────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # Specific model IDs for high-reasoning tasks
    # Provider routing via OpenRouter:
    #   - glm-5.1 → io.net (reasoning ON)
    #   - glm-5 → DeepInfra (reasoning ON)
    #   - grok-4.20 → xAI (reasoning ON)
    #   - minimax-m2.7 → Together (reasoning OFF)
    # 
    # Grok 4.20 model IDs (xAI via OpenRouter):
    #   - x-ai/grok-4.20-beta-0309-reasoning (specific version, March 2025)
    #   - x-ai/grok-4.20-reasoning-latest (always updated)
    # Docs: https://docs.x.ai/developers/models/grok-4.20-beta-0309-reasoning
    GLM_5_1_MODEL: str = "z-ai/glm-5.1"
    GLM_5_MODEL: str = "z-ai/glm-5"
    GROK_4_20_MA_MODEL: str = "x-ai/grok-4.20-beta-0309-reasoning"
    MINIMAX_M2_7_MODEL: str = "minimax/minimax-m2.7"

    # ── Claw402 — x402-native multi-model provider ──────────────────────────
    # No account, no API key — wallet pays per request via x402 on Base.
    # Supported: GPT-5.4, Claude Opus, DeepSeek, Qwen, Grok, Gemini, Kimi, 15+ models
    # Docs: https://claw402.com
    CLAW402_BASE_URL: str = "https://api.claw402.com/v1"
    # Default model — user can override per request via model_1/model_2
    CLAW402_MODEL: str = "claude-opus-4-5"
    # Wallet private key for signing x402 USDC payments on Base
    # WARNING: keep this secret, use a dedicated hot wallet with minimal funds
    CLAW402_WALLET_PRIVATE_KEY: str = ""
    # Base mainnet USDC contract (same as X402_USDC_ADDRESS default)
    CLAW402_USDC_ADDRESS: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

    # ── Provider selection ──────────────────────────────────────────────────
    # "ionet" | "xai" | "claw402" | "openrouter" | "ollama"
    LLM_PROVIDER: str = "ollama"

    # ── Per-role LLM tuning ────────────────────────────────────────────────
    # Planner (GLM-5.1): needs moderate creativity for market analysis
    PLANNER_TEMPERATURE: float = 0.3
    PLANNER_TOP_P: float = 0.92
    PLANNER_MAX_TOKENS: int = 4096
    PLANNER_FREQUENCY_PENALTY: float = 0.0
    PLANNER_PRESENCE_PENALTY: float = 0.0

    # Verifier (Grok 4.20): must be deterministic for security checks
    VERIFIER_TEMPERATURE: float = 0.0
    VERIFIER_TOP_P: float = 0.85
    VERIFIER_MAX_TOKENS: int = 2048
    VERIFIER_FREQUENCY_PENALTY: float = 0.0
    VERIFIER_PRESENCE_PENALTY: float = 0.0

    # Controller (GLM-5.1): deterministic for safety-critical go/no-go
    CONTROLLER_TEMPERATURE: float = 0.0
    CONTROLLER_TOP_P: float = 0.85
    CONTROLLER_MAX_TOKENS: int = 2048
    CONTROLLER_FREQUENCY_PENALTY: float = 0.0
    CONTROLLER_PRESENCE_PENALTY: float = 0.0

    # RAG Summarizer (GLM-5.1): neutral factual synthesis
    RAG_TEMPERATURE: float = 0.0
    RAG_TOP_P: float = 0.85
    RAG_MAX_TOKENS: int = 1024
    RAG_FREQUENCY_PENALTY: float = 0.3
    RAG_PRESENCE_PENALTY: float = 0.2

    # Backtest (Ollama): moderate creativity for strategy simulation
    BACKTEST_TEMPERATURE: float = 0.15
    BACKTEST_TOP_P: float = 0.90
    BACKTEST_MAX_TOKENS: int = 4096
    BACKTEST_FREQUENCY_PENALTY: float = 0.0
    BACKTEST_PRESENCE_PENALTY: float = 0.0

    # Ollama fallback defaults
    OLLAMA_TEMPERATURE: float = 0.1
    OLLAMA_TOP_P: float = 0.90
    OLLAMA_MAX_TOKENS: int = 2048

    # ── Trading safety mode ────────────────────────────────────────────────
    # "paper" (default, safe simulation) | "live" (real order execution path)
    TRADING_MODE: str = "paper"
    LIVE_TRADING_ENABLED: bool = False
    # Mandatory phrase to prevent accidental live activation.
    LIVE_TRADING_CONFIRMATION: str = ""
    # Second-level live safeguard: HMAC request signing headers.
    LIVE_GUARD_SECRET: str = ""
    LIVE_GUARD_MAX_SKEW_SECONDS: int = 120
    LIVE_REQUIRE_AGENT_SIGNATURE: bool = True
    LIVE_MAX_MARKET_DATA_AGE_SECONDS: int = 180
    LIVE_CIRCUIT_BREAKER_RISK_THRESHOLD: float = 0.75
    LIVE_CIRCUIT_BREAKER_VOLATILITY_PCT: float = 0.08
    ENABLE_AGENT_GOVERNANCE: bool = True
    # Blocks prompts that contain too many semantic coordination cues.
    SEMANTIC_SIGNAL_BLOCK_THRESHOLD: int = 2

    # ── Blockchain RPC ──────────────────────────────────────────────────────
    ETHEREUM_RPC_URL: str = ""
    SOLANA_RPC_URL: str = ""
    BILL_REGISTRY_ADDRESS: str = ""
    IDENTITY_REGISTRY_ADDRESS: str = ""
    ACTIVITY_LOGGER_ADDRESS: str = ""
    POLICY_ENFORCER_ADDRESS: str = ""
    DISPUTE_RESOLVER_ADDRESS: str = ""
    ONCHAIN_AUDIT_ENABLED: bool = False

    # ── x402 Payment Protocol ────────────────────────────────────────────────
    # HTTP 402 Payment Required for pay-per-use API access (USDC on Base/L2).
    # Backtesting is ALWAYS exempt from x402 — it simulates crypto behavior
    # without real capital deployment; charging would distort evaluation.
    X402_ENABLED: bool = False
    X402_TESTNET: bool = True  # True = Sepolia/Base Sepolia (accept any tx_hash)
    X402_RECIPIENT_ADDRESS: str = ""  # Wallet address to receive USDC payments
    X402_CHAIN_ID: int = 8453  # Base mainnet (8453); Base Sepolia testnet (84532)
    X402_USDC_ADDRESS: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Base USDC
    X402_PRICE_TRADE_EXECUTE: float = 0.01    # $0.01 per trade execution
    X402_PRICE_TRADE_ANALYZE: float = 0.005   # $0.005 per market analysis
    X402_PRICE_KNOWLEDGE_ENHANCED: float = 0.002  # $0.002 per enhanced RAG query
    X402_PRICE_KNOWLEDGE_HYBRID: float = 0.001   # $0.001 per hybrid query
    X402_PRICE_GOVERNANCE_POLICY: float = 0.001   # $0.001 per policy check

    # ── IPFS — Off-Chain Data Storage ────────────────────────────────────────
    IPFS_ENABLED: bool = False
    IPFS_API_URL: str = "http://localhost:5001"
    IPFS_GATEWAY_URL: str = "https://ipfs.io"
    IPFS_PINNING_SERVICE: str = "local"  # "local" | "pinata" | "web3storage"
    PINATA_JWT: str = ""
    WEB3_STORAGE_TOKEN: str = ""

    # ── EAAC — Ethereum AI Agent Coordinate Or ───────────────────────────────
    EAAC_ENABLED: bool = True
    DATA_RECORDER_ADDRESS: str = ""

    # ── Vulnerability Scanner ────────────────────────────────────────────────
    VULN_SCAN_ENABLED: bool = True
    VULN_SCAN_RISK_THRESHOLD: float = 0.6
    VULN_SCAN_MIN_ENSEMBLE_CONFIDENCE: float = 0.7
    VULN_SCAN_ON_DEPLOY: bool = True  # Auto-scan before contract deployment
    ETHERSCAN_API_KEY: str = ""  # Used by /scan/address to fetch verified source code

    # ── DEX Execution ───────────────────────────────────────────────────────
    DEX_SLIPPAGE_TOLERANCE: float = 0.005  # 0.5% default
    DEX_GAS_PRIORITY: str = "medium"  # "low" | "medium" | "high"
    DEX_DEADLINE_SECONDS: int = 300  # 5 minutes default

    # ── mABC Governance ───────────────────────────────────────────────────────
    MABC_ENABLED: bool = True
    MABC_VOTING_PERIOD_SECONDS: int = 259200  # 3 days
    MABC_QUORUM_NUMERATOR: int = 4  # 4%
    MABC_QUORUM_DENOMINATOR: int = 100
    MABC_TIMELOCK_DELAY_SECONDS: int = 86400  # 1 day
    MABC_PROPOSAL_THRESHOLD: float = 100.0

    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./trading.db"

    # ── API Authentication ──────────────────────────────────────────────────
    API_KEYS: str = ""  # comma-separated list; empty = no auth (local dev)
    
    # ── Security Settings ─────────────────────────────────────────────────────
    JWT_SECRET: str = ""  # Secret key for JWT signing (generate with: openssl rand -hex 32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    CORS_ORIGINS: str = ""  # comma-separated allowed origins (empty = allow all)
    ALLOWED_HOSTS: str = ""  # comma-separated allowed hosts for TrustedHostMiddleware
    
    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 5  # Max failed login attempts before lockout
    RATE_LIMIT_LOCKOUT_MINUTES: int = 15  # Lockout duration in minutes
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60  # General API rate limit
    
    # ── Password Security ─────────────────────────────────────────────────────
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBER: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False
    PASSWORD_BREACH_CHECK_ENABLED: bool = True  # Check against haveibeenpwned

    # ── Observability ───────────────────────────────────────────────────────
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ── RAG / ChromaDB ──────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    RAG_COLLECTION_NAME: str = "market_knowledge"
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200

    # Hybrid-retrieval tuning (semantic + lexical)
    RAG_MAX_RESULTS: int = 15          # total results after fusion
    RAG_SEMANTIC_TOP_K: int = 25       # candidates from ChromaDB vector search
    RAG_LEXICAL_TOP_K: int = 25        # candidates from BM25 keyword search
    RAG_SEMANTIC_WEIGHT: float = 0.65  # weight in Reciprocal Rank Fusion
    RAG_LEXICAL_WEIGHT: float = 0.35
    RAG_RRF_K: int = 60               # RRF constant (higher → smoother)

    # Governance policy updates should be controlled by configured multisig signers.
    GOVERNANCE_SIGNERS: str = ""
    GOVERNANCE_MULTISIG_THRESHOLD: int = 2

    class Config:
        env_file = ".env"

    def validate_runtime(self) -> None:
        """
        Strict runtime guardrails for production and live-trading readiness.
        Raises ValueError when settings are unsafe or inconsistent.
        
        Dual-model auto-assignment: user selects 2 cloud models (model_1, model_2).
        Agents auto-assign: model_1 → Planner+Controller, model_2 → Verifier.
        Ollama is NOT available for trading — only for backtesting.
        """
        valid_modes = {"paper", "live"}
        if self.TRADING_MODE not in valid_modes:
            raise ValueError(
                f"Invalid TRADING_MODE='{self.TRADING_MODE}'. Must be one of: {sorted(valid_modes)}"
            )

        # If user explicitly selects ionet/xai provider, corresponding API key must exist.
        if self.LLM_PROVIDER == "ionet" and not self.IONET_API_KEY:
            raise ValueError("LLM_PROVIDER=ionet requires IONET_API_KEY.")
        if self.LLM_PROVIDER == "xai" and not self.XAI_API_KEY:
            raise ValueError("LLM_PROVIDER=xai requires XAI_API_KEY.")

        # Real deployment profile: live mode must have at least one cloud key
        # (user can select same model for both to use only 1 API key).
        if self.TRADING_MODE == "live":
            if not self.LIVE_TRADING_ENABLED:
                raise ValueError(
                    "TRADING_MODE=live requires LIVE_TRADING_ENABLED=true."
                )
            if self.LIVE_TRADING_CONFIRMATION != "I_UNDERSTAND_LIVE_TRADING_RISK":
                raise ValueError(
                    "TRADING_MODE=live requires LIVE_TRADING_CONFIRMATION="
                    "I_UNDERSTAND_LIVE_TRADING_RISK."
                )
            # At least one cloud API key is required for live trading.
            # Ollama is NOT allowed for live trading — only for backtesting.
            if not self.IONET_API_KEY and not self.XAI_API_KEY:
                raise ValueError(
                    "TRADING_MODE=live requires at least one cloud API key "
                    "(IONET_API_KEY for GLM-5.1 and/or XAI_API_KEY for Grok 4.20). "
                    "Ollama is not available for live trading — only for backtesting."
                )
            if not self.LIVE_GUARD_SECRET:
                raise ValueError(
                    "TRADING_MODE=live requires LIVE_GUARD_SECRET for signed header verification."
                )
            if self.LIVE_GUARD_MAX_SKEW_SECONDS <= 0:
                raise ValueError("LIVE_GUARD_MAX_SKEW_SECONDS must be > 0.")
            if self.LIVE_MAX_MARKET_DATA_AGE_SECONDS <= 0:
                raise ValueError("LIVE_MAX_MARKET_DATA_AGE_SECONDS must be > 0.")
            if not (0.0 < self.LIVE_CIRCUIT_BREAKER_RISK_THRESHOLD <= 1.0):
                raise ValueError("LIVE_CIRCUIT_BREAKER_RISK_THRESHOLD must be in (0, 1].")
            if not (0.0 < self.LIVE_CIRCUIT_BREAKER_VOLATILITY_PCT <= 1.0):
                raise ValueError("LIVE_CIRCUIT_BREAKER_VOLATILITY_PCT must be in (0, 1].")

        if self.BACKTEST_FORCE_OLLAMA_CLOUD:
            base_url = (self.BACKTEST_OLLAMA_BASE_URL or self.OLLAMA_BASE_URL).strip().lower()
            if not base_url.startswith("http"):
                raise ValueError("Backtest Ollama endpoint must be an HTTP(S) URL.")

        # x402 payment protocol validation
        if self.X402_ENABLED:
            if not self.X402_RECIPIENT_ADDRESS:
                raise ValueError(
                    "X402_ENABLED=true requires X402_RECIPIENT_ADDRESS (wallet to receive USDC)."
                )
            if not self.X402_RECIPIENT_ADDRESS.startswith("0x") or len(self.X402_RECIPIENT_ADDRESS) != 42:
                raise ValueError("X402_RECIPIENT_ADDRESS must be a valid Ethereum address (0x...).")
            if self.X402_CHAIN_ID <= 0:
                raise ValueError("X402_CHAIN_ID must be a positive integer.")
            if not self.X402_USDC_ADDRESS:
                raise ValueError("X402_ENABLED=true requires X402_USDC_ADDRESS (USDC contract on target chain).")
            # Validate pricing is non-negative
            for attr in (
                "X402_PRICE_TRADE_EXECUTE", "X402_PRICE_TRADE_ANALYZE",
                "X402_PRICE_KNOWLEDGE_ENHANCED", "X402_PRICE_KNOWLEDGE_HYBRID",
                "X402_PRICE_GOVERNANCE_POLICY",
            ):
                val = getattr(self, attr, -1)
                if val < 0:
                    raise ValueError(f"{attr} must be >= 0.")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
