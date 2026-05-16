# AI Agent Trading System Manual

**Complete reference for understanding and operating the AI-powered blockchain trading platform**

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Authentication & Security](#authentication--security)
4. [Core Components](#core-components)
5. [Multi-Agent Trading Flow](#multi-agent-trading-flow)
6. [Risk Management System](#risk-management-system)
7. [Enhancement Roadmap](#enhancement-roadmap--next-generation-trading-architecture)
8. [Notification System](#notification-system)
9. [Escrow & Revenue System](#escrow--revenue-system)
10. [Identity Verification System](#identity-verification-system)
11. [Cloud Identity Store (AWS DynamoDB)](#cloud-identity-store-aws-dynamodb)
12. [Crypto Experience Priority System](#crypto-experience-priority-system)
13. [Device Ban & Abuse Detection System](#device-ban--abuse-detection-system)
14. [Mock Money Simulation](#mock-money-simulation)
15. [Cybersecurity Beware List Screening](#cybersecurity-beware-list-screening)
16. [API Reference](#api-reference)
16. [Frontend Components](#frontend-components)
17. [Configuration](#configuration)
18. [Installation Guide](#installation-guide)
19. [Safety Mechanisms](#safety-mechanisms)
20. [Troubleshooting](#troubleshooting)

---

## System Overview

The AI Agent Trading System is a multi-agent blockchain trading platform that combines:

- **Multi-Agent Architecture**: Planner, Verifier, Controller, Monitor, and Adjuster agents
- **Dual-Model Reasoning**: Two LLMs for consensus (Proof-of-Thought)
- **Risk Management**: Pre-execution risk assessment with dynamic position sizing
- **Hybrid RAG**: Knowledge retrieval for context-aware decisions
- **Blockchain Integration**: Ethereum and Solana support
- **Paper/Live Modes**: Simulation and real capital deployment
- **Two-Factor Authentication**: SMS-based 2FA for secure login
- **Identity Verification**: GitHub/LinkedIn OAuth required before trading (1-year minimum account age)
- **Mock Money Simulation**: Virtual crypto balances (BTC/ETH/SOL/USDT) in backtesting with fees and slippage
- **Modal GLM-5 Endpoint**: Serverless GPU inference for backtesting via Modal
- **Activity Notifications**: Email alerts for trades, profits, and account status
- **Automatic Theme**: Day/night mode based on user timezone
- **Trade Escrow**: Smart contract-based fund management with owner withdrawals

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React/Vite)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Trading  │ │  Risk    │ │Strategy │ │ Debate   │ │ Config/FAQ/etc   │   │
│  │Dashboard │ │Dashboard │ │  Page   │ │ Arena    │ │                  │   │
│  └────┬─────┘ └────┬─────┘ └────┬────┘ └────┬─────┘ └────────┬─────────┘   │
│       │            │            │            │                  │             │
│       └────────────┴────────────┴────────────┴──────────────────┘             │
│                                    │                                         │
│                           API_BASE /api/v1                                   │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (FastAPI)                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                           API LAYER                                     │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │ │
│  │  │ /trading │ │  /risk   │ │/backtest │ │/governance│ │ /knowledge  │  │ │
│  │  │ /execute │ │ /assess  │ │          │ │          │ │            │  │ │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘  │ │
│  │                                                                       │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │ │
│  │  │  /auth   │ │/notifications│ │ /escrow  │ │ /payments│ │ /security  │  │ │
│  │  │  2FA     │ │ newsletter  │ │ revenue  │ │  x402    │ │  vuln scan │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│         │                  │                  │                   │            │
│  ┌──────▼──────────────────▼──────────────────▼──────────────────▼──────────┐ │
│  │                      CORE SERVICES                                         │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────────┐   │ │
│  │  │ RiskEngine │  │ Orchestrator│  │ RAG System │  │ Blockchain Clients│   │ │
│  │  │            │  │ (Multi-     │  │ (Hybrid    │  │ (Ethereum/Solana) │   │
│  │  │            │  │  Agent)     │  │ Retrieval) │  │                  │   │ │
│  │  └────────────┘  └──────┬─────┘  └────────────┘  └──────────────────┘   │ │
│  └─────────────────────────┼───────────────────────────────────────────────┘ │
│                            │                                                  │
│  ┌─────────────────────────▼───────────────────────────────────────────────┐ │
│  │                      LLM PROVIDERS (OpenRouter)                          │ │
│  │  ┌────────────┐  ┌────────────────┐  ┌────────────┐  ┌──────────────┐   │ │
│  │  │  GLM-5.1   │  │ Grok 4.3 │  │MiMo-V2-Pro │  │Qwen 3.6 Plus │   │ │
│  │  │ (Reasoning)│  │  (Reasoning)   │  │ (Xiaomi)   │  │  (Alibaba)   │   │ │
│  │  └────────────┘  └────────────────┘  └────────────┘  └──────────────┘   │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      DATA STORAGE                                       │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │  │
│  │  │ Risk SQLite│  │ Knowledge  │  │ Governance │  │ On-Chain State   │  │  │
│  │  │ (History)  │  │ Base (Vec) │  │ (IPFS)     │  │ (Blockchain)     │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └──────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐ │
│  │ CoinGecko  │  │ OpenRouter │  │  Blockchain │  │  IPFS/Pinata        │ │
│  │ (Market    │  │ (LLM       │  │  Networks   │  │  (Governance        │ │
│  │  Data)     │  │  Provider) │  │  (ETH/SOL)   │  │  Storage)           │ │
│  └────────────┘  └────────────┘  └────────────┘  └──────────────────────┘ │
│  ┌────────────┐  ┌────────────┐                                            │
│  │ Twilio/SMS │  │ SendGrid   │  For 2FA and notifications                │
│  │ (2FA SMS)  │  │ (Email)    │                                            │
│  └────────────┘  └────────────┘                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Authentication & Security

### Two-Factor Authentication (2FA)

The system supports SMS-based Two-Factor Authentication for enhanced account security.

#### 2FA Flow

```
┌─────────────────────────────────────────────────────────────┐
│  SIGNUP                                                      │
│  1. User enters email, password                              │
│  2. Optional: Enter phone number for 2FA (E.164 format)     │
│  3. SMS verification code sent (if phone provided)           │
│  4. Account created with 2FA enabled                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  LOGIN (with 2FA)                                            │
│  1. User enters email + password                             │
│  2. System detects 2FA enabled                               │
│  3. 6-digit SMS code sent to phone                           │
│  4. User enters code on 2FA screen                           │
│  5. Code verified → User logged in                           │
└─────────────────────────────────────────────────────────────┘
```

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/signup` | POST | Register with optional phone for 2FA |
| `/api/v1/auth/login` | POST | Login (returns `requires_2fa: true` if enabled) |
| `/api/v1/auth/verify-2fa` | POST | Verify 6-digit SMS code |
| `/api/v1/auth/setup-2fa` | POST | Set up 2FA for existing account |
| `/api/v1/auth/disable-2fa` | POST | Disable 2FA |
| `/api/v1/auth/timezone` | GET | Get daytime status for auto theme |

### Automatic Day/Night Theme

The frontend automatically switches between light and dark themes based on the user's local time:

- **Daytime (6 AM - 6 PM)**: Light theme
- **Nighttime (6 PM - 6 AM)**: Dark theme

This is handled by `frontend/src/contexts/ThemeContext.jsx` which:
- Detects user timezone via browser API
- Calls `/api/v1/auth/timezone` for accurate detection
- Checks every minute for theme updates
- Allows manual toggle (disables auto mode)

---

## Core Components

### 1. Multi-Agent Orchestrator (`backend/app/agents/orchestrator.py`)

The orchestrator coordinates five specialized agents:

| Agent | Role | Default Model | Output |
|-------|------|----------------|--------|
| **Planner** | Market analysis & trade proposal | GLM-5.1 | action, confidence, risk_score, reasoning |
| **Verifier** | Security audit & risk adjustment | Grok 4.3 | approved, adjusted_risk_score, vulnerabilities |
| **Controller** | Final decision (PoT consensus) | GLM-5.1 | final_action, final_amount, pot_confidence |
| **Monitor** | Post-execution tracking | GLM-5.1 | tracking_mode, tp_sl_strategy |
| **Adjuster** | Reactive self-correction | GLM-5.1 | early_exit_conditions, parameter_shifts |

### Single Model Selection

**The user selects ONE model that is used by ALL agents.** This simplifies the interface while still providing powerful multi-agent reasoning:

```json
{
  "model": "glm-5.1"
}
```

All five agents (Planner, Verifier, Controller, Monitor, Adjuster) will use the same model, each with its own role-specific parameters auto-tuned by the system.

#### Available Models:

| Model | Description | Reasoning | Image Input |
|-------|-------------|-----------|-------------|
| `glm-5.1` | GLM-5.1 (Reasoning) | ✅ ON | ❌ NO |
| `grok-4.3` | Grok 4.3 (Reasoning) v1 | ✅ ON | ✅ **YES** |
| `grok-4.20-0309-v2` | Grok 4.20 0309 (Reasoning) v2 | ✅ ON | ✅ **YES** |
| `mimo-v2-pro` | MiMo-V2-Pro (Reasoning) | ✅ ON | ❌ NO |
| `qwen-3.6-plus` | Qwen 3.6 Plus (Reasoning) | ✅ ON | ❌ NO |

### Image Input Support

**⚠️ IMPORTANT: Image input is ONLY supported by Grok 4.3 (v1 and v2).**

If you provide an `image_url` with other models (glm-5.1, mimo-v2-pro, qwen-3.6-plus), the image will be **IGNORED** and only text will be processed.

#### Using Image Input

To use image input with Grok 4.3 models, include the `image_url` parameter in your trade request:

```json
{
  "prompt": "Analyze this chart pattern and predict the next price movement",
  "model": "grok-4.20-0309-v2",
  "image_url": "https://example.com/chart.png",
  "token_pair": "ETH/USDT",
  "chain": "ethereum"
}
```

#### Supported Image Formats

- **JPEG** (.jpg, .jpeg)
- **PNG** (.png)
- **GIF** (.gif)
- **WebP** (.webp)

#### Image URL Requirements

- Must be publicly accessible HTTP/HTTPS URL
- OR base64 data URL (e.g., `data:image/png;base64,...`)
- Maximum size: 20MB

#### Example: Base64 Image Input

```python
import base64

# Read and encode image
with open("chart.png", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()
    
image_url = f"data:image/png;base64,{image_data}"

# Use in request
response = requests.post(
    "/api/v1/trading/execute",
    json={
        "prompt": "Analyze this chart",
        "model": "grok-4.20-0309-v2",
        "image_url": image_url,
        "token_pair": "ETH/USDT"
    }
)
```

#### Default Model:

If no model is specified, the system uses **GLM-5.1** as the default for all agents.

#### Backward Compatibility:

Legacy dual-model fields (`model_1`, `model_2`) are still supported but deprecated. Use the single `model` field instead.

#### Auto-Tuned Parameters:

Even though all agents use the same model, each agent receives **different optimized parameters** based on its role:

| Agent | Temperature | Top_P | Max_Tokens | Reasoning |
|-------|-------------|-------|------------|-----------|
| Planner | 0.2-0.35 | 0.85-0.92 | 2048-6144 | ✅ ON |
| Verifier | 0.0-0.1 | 0.80-0.85 | 1536-3072 | ✅ ON |
| Controller | 0.0-0.05 | 0.75-0.82 | 1024-2048 | ✅ ON |
| Monitor | 0.0-0.1 | 0.80-0.85 | 1024-2048 | ✅ ON |
| Adjuster | 0.1-0.2 | 0.82-0.88 | 1536-3072 | ✅ ON |

### LLM Auto-Tune System (`backend/app/core/llm_auto_tune.py`)

The system includes an **LLM Auto-Tune System** that automatically configures optimal parameters for each agent based on task characteristics:

#### What It Detects:
- **Input Complexity**: Simple, Moderate, Complex (based on text length, technical terms, context size)
- **Risk Level**: Low, Medium, High (based on position size, leverage, volatility, live mode)
- **Task Type**: Market analysis, security audit, consensus, risk assessment, etc.

#### What It Configures:
| Parameter | Range | Purpose |
|-----------|-------|---------|
| `temperature` | 0.0 - 1.0 | Controls randomness/creativity |
| `top_p` | 0.1 - 1.0 | Nucleus sampling threshold |
| `max_tokens` | 256 - 8192 | Output length limit |
| `frequency_penalty` | 0.0 - 1.0 | Discourages repetition |
| `presence_penalty` | 0.0 - 1.0 | Encourages topic diversity |
| `reasoning` | True/False | Enables reasoning mode |

#### Pre-Optimized Profiles:

| Task Type | Temperature | Top_P | Max_Tokens | Reasoning |
|-----------|-------------|-------|------------|-----------|
| **Market Analysis** (Planner) | 0.2-0.35 | 0.85-0.92 | 2048-6144 | ✅ ON |
| **Security Audit** (Verifier) | 0.0-0.1 | 0.80-0.85 | 1536-3072 | ✅ ON |
| **Consensus** (Controller) | 0.0-0.05 | 0.75-0.82 | 1024-2048 | ✅ ON |
| **Risk Assessment** | 0.0-0.1 | 0.80-0.85 | 1024-2048 | ✅ ON |
| **RAG Synthesis** | 0.0-0.1 | 0.80-0.85 | 512-1024 | Optional |

#### Model-Specific Optimizations:

| Model | Temperature Multiplier | Top_P Multiplier | Notes |
|-------|----------------------|------------------|-------|
| GLM-5.1 | 0.9x | 1.0x | Handles complex tasks well |
| Grok 4.3 v1 | 0.85x | 0.95x | Excellent for security/verification |
| Grok 4.3 v2 | 0.85x | 0.95x | Latest xAI reasoning model |
| MiMo-V2-Pro | 0.9x | 1.0x | Xiaomi's reasoning model |
| Qwen 3.6 Plus | 0.95x | 1.0x | Alibaba's reasoning model |

#### Usage:

```python
from app.core.llm import get_auto_tuned_llm

# Auto-tuned LLM for any agent
llm = get_auto_tuned_llm(
    agent_role="planner",
    model_id="glm-5.1",
    input_text="Analyze ETH/USDT market conditions...",
    market_data={"position_size_usd": 5000, "leverage": 2.0, "volatility": 0.03},
    is_live=True,
)

# Or use role-specific functions
from app.core.llm import (
    get_auto_tuned_planner_llm,
    get_auto_tuned_verifier_llm,
    get_auto_tuned_controller_llm,
)

planner_llm = get_auto_tuned_planner_llm(model_id="glm-5.1", is_live=True)
verifier_llm = get_auto_tuned_verifier_llm(model_id="grok-4.3", is_live=True)
```

The system automatically:
1. Detects input complexity from text length and technical indicators
2. Detects risk level from market data
3. Applies task-specific parameter profiles
4. Adjusts for model-specific characteristics
5. Tightens parameters in high-risk/live trading situations

### 2. Risk Engine (`backend/app/risk/risk_engine.py`)

Multi-factor risk assessment before any execution:

```python
# Risk components with weights
volatility_risk = assess_volatility(market_data) * 0.30
drawdown_risk = assess_drawdown(market_data) * 0.25
liquidity_risk = assess_liquidity(market_data) * 0.25
onchain_risk = assess_onchain(onchain_data) * 0.20

overall_score = volatility_risk + drawdown_risk + liquidity_risk + onchain_risk
```

### 3. Authentication System (`backend/app/api/auth.py`)

Full authentication with:
- Email/password signup and login
- Email verification
- Password reset
- Two-Factor Authentication (2FA) via SMS
- Newsletter subscription
- JWT token management

### 4. Notification System (`backend/app/api/notifications.py`)

Activity-based notifications sent to user's Gmail/Hotmail:
- Newsletter emails
- Trade execution alerts
- Profit/loss notifications
- Security alerts
- Account status emails
- Daily/weekly reports


## Multi-Agent Trading Flow

### Current Pipeline (Classic Mode)

The system uses a linear agent pipeline where each agent processes sequentially:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Planner  │───▶│ Verifier │───▶│Controller│───▶│ Monitor │───▶│ Adjuster│
│(model_1) │    │(model_2) │    │(model_1) │    │(model_1) │    │(model_2)│
└──────────┘    └──────────┘    └────┬─────┘    └──────────┘    └──────────┘
                                     │
                              ┌──────┴──────┐
                              │  approved?  │
                              └──────┬──────┘
                               Yes ↙     ↘ No
                          ┌────────┐  ┌────────┐
                          │Execute │  │ Reject │
                          └────────┘  └────────┘
```

#### Agent Responsibilities

| Step | Agent | Model | Input | Output |
|------|-------|-------|-------|--------|
| 1 | **Planner** | model_1 | Market data + RAG context | Trade action, confidence, risk_score, reasoning |
| 2 | **Verifier** | model_2 | Planner decision + RAG context | approved, adjusted_risk_score, vulnerabilities |
| 3 | **Controller** | model_1 | Planner + Verifier + RAG summary | Final go/no-go (Proof-of-Thought consensus) |
| 4 | **Monitor** | model_1 | Final decision | Tracking mode, TP/SL strategy |
| 5 | **Adjuster** | model_2 | Monitoring strategy | Early exit conditions, parameter shifts |

#### State Schema

The `AgentState` TypedDict carries all data through the graph:

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    market_data: dict
    trade_prompt: str
    token_pair: str
    chain: str
    rag_context: str
    rag_metadata: dict
    model_1: str                    # Planner + Controller
    model_2: str                    # Verifier
    planner_decision: dict
    verifier_result: dict
    controller_approval: bool
    final_decision: dict
    risk_score: float
    monitoring_strategy: dict
    adjustment_logic: dict
```

#### Conditional Routing

The graph uses a single conditional edge at the Controller node:

```python
def should_execute(state: AgentState) -> Literal["execute", "reject"]:
    return "execute" if state.get("controller_approval", False) else "reject"
```

---

## Risk Management System

### Pre-Execution Risk Assessment

Before any trade execution, the Risk Engine (`backend/app/risk/risk_engine.py`) performs a multi-factor assessment:

```python
# Weighted risk components
volatility_risk = assess_volatility(market_data) * 0.30
drawdown_risk = assess_drawdown(market_data) * 0.25
liquidity_risk = assess_liquidity(market_data) * 0.25
onchain_risk = assess_onchain(onchain_data) * 0.20

overall_score = volatility_risk + drawdown_risk + liquidity_risk + onchain_risk
```

### Risk Levels

| Level | Score Range | Action |
|-------|-------------|--------|
| LOW | 0–25 | Full execution allowed |
| MEDIUM | 26–50 | Execution with caution |
| HIGH | 51–75 | Reduced position size |
| CRITICAL | 76–100 | Execution blocked |

### Risk API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/trading/risk/assess` | POST | Assess trade risk |
| `/api/v1/trading/risk/metrics` | GET | Get risk metrics |
| `/api/v1/trading/risk/calibrate` | GET | Calibrate risk weights |

### Risk Storage

All risk assessments are persisted to SQLite via `backend/app/risk/risk_storage.py` for historical analysis and calibration.

---

## Enhancement Roadmap — Next-Generation Trading Architecture

> This section documents planned enhancements to evolve the current linear pipeline into a more sophisticated multi-agent system, based on established AI agent research patterns (Park et al. 2023, Du et al. 2023, Liang et al. 2023) and LangGraph best practices.

### Current vs. Target Architecture

| Feature | Current State | Target State | Priority |
|---------|--------------|--------------|----------|
| **Agent Pipeline** | Linear: Planner→Verifier→Controller→Monitor→Adjust | Debate: Analysts→Bull/Bear Debate→Synthesis→Trader→Risk Debate→Portfolio Decision | 🔴 High |
| **Agent Roles** | 5 agents (Planner, Verifier, Controller, Monitor, Adjuster) | 12+ agents (4 Crypto Analysts, Bull/Bear Researchers, Research Synthesizer, Trader, 3 Risk Debators, Portfolio Manager) | 🔴 High |
| **Decision Mechanism** | Proof-of-Thought (PoT) single-pass consensus | Multi-round adversarial debate with opposing viewpoints | 🔴 High |
| **Structured Output** | JSON parsing with fallback dicts | Pydantic-validated models (TraderProposal, PortfolioDecision) | 🔴 High |
| **Tool-Calling** | None (agents use injected market data) | `llm.bind_tools()` + ToolNode for live on-demand data fetching | 🟡 Medium |
| **Data Tools** | CoinGecko (via API routes only) | Crypto-native tools: CoinGecko, DeFiLlama, CryptoCompare, LunarCrush, Dune Analytics | 🟡 Medium |
| **Rating System** | 3-tier (buy/sell/hold) | 5-tier: Strong Buy / Buy / Hold / Sell / Strong Sell | 🔴 High |
| **Signal Processing** | Not present | Automated rating extraction from Portfolio Manager decisions | 🔴 High |
| **Investment Debate** | Not present | Bull vs Bear researcher debate with configurable rounds | 🟡 Medium |
| **Risk Debate** | Single-pass risk engine scoring | Aggressive vs Conservative vs Neutral debator rounds | 🟡 Medium |
| **Trading Memory** | Not present | Persistent decision log with outcome tracking and reflection | 🟡 Medium |
| **Reflection** | Not present | LLM-generated reflection on past decisions for continuous improvement | 🟢 Low |
| **Conditional Routing** | Single should_execute() edge | Per-analyst tool-call routing + debate round counting + risk debate cycling | 🟡 Medium |
| **Checkpoint/Resume** | Not present | SqliteSaver-based graph state persistence for crash recovery | 🟢 Low |

### Enhancement 1: Multi-Agent Debate Architecture

**Strategy**: Replace the linear pipeline with an adversarial debate architecture where opposing agents argue for and against investment decisions. This approach is grounded in multi-agent debate research showing that opposing viewpoints produce more robust decisions than single-pass consensus (Du et al., 2023 "Improving Factuality and Reasoning in Language Models through Multiagent Debate").

**Planned Flow**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ANALYST PHASE                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐             │
│  │  Market  │  │Sentiment │  │  News    │  │  On-Chain /      │             │
│  │ Analyst  │  │ Analyst  │  │ Analyst  │  │  Fundamentals    │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────────────┘             │
│       │              │              │              │                          │
│       └──────────────┴──────────────┴──────────────┘                          │
│                             │                                               │
│                     Analyst Reports                                         │
└─────────────────────────────┼───────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────────────┐
│                     INVESTMENT DEBATE PHASE                                 │
│                                                                             │
│   ┌──────────────┐          ┌──────────────┐                                │
│   │    Bull      │◀───▶    │    Bear      │  (max_debate_rounds)           │
│   │  Researcher  │  Debate │  Researcher  │                                │
│   └──────┬───────┘         └──────┬───────┘                                │
│          │                        │                                         │
│          └────────────┬───────────┘                                         │
│                        │                                                     │
│               ┌────────▼────────┐                                           │
│               │    Research     │                                           │
│               │   Synthesizer   │                                           │
│               └────────┬────────┘                                           │
└────────────────────────┼────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────────────────┐
│                      TRADING PHASE                                          │
│               ┌────────────────┐                                           │
│               │     Trader     │  (structured proposal)                    │
│               └───────┬────────┘                                           │
└───────────────────────┼────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────────────────┐
│                      RISK DEBATE PHASE                                      │
│                                                                             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│   │  Aggressive  │  │ Conservative │  │   Neutral    │  (max_risk_rounds)  │
│   │   Debator    │◀─▶│   Debator    │◀─▶│   Debator   │                     │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                     │
│          └─────────────────┼─────────────────┘                              │
│                      │                                                      │
│            ┌─────────▼──────────┐                                           │
│            │  Portfolio Manager │  (5-tier rating decision)                │
│            └────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Advantage Over Current System**: The adversarial debate forces the system to consider both bullish and bearish evidence, reducing confirmation bias that can occur in a single-pass pipeline.

### Enhancement 2: Crypto-Native Data Tools with Tool-Calling

**Strategy**: Equip each analyst with LangChain `@tool` functions that fetch live data on-demand via `llm.bind_tools()` + LangGraph `ToolNode`. This is superior to pre-fetching all data at the API layer because:
1. Agents only fetch data they actually need (cost efficient)
2. Agents can make multiple tool calls in sequence (depth of analysis)
3. The graph conditionally routes to tool nodes only when needed

**Planned Crypto-Native Tool Sets**:

| Analyst | Tools | Data Sources |
|---------|-------|-------------|
| **Market Analyst** | `get_crypto_price_data()`, `get_technical_indicators()`, `get_dex_liquidity()` | CoinGecko API, DEX Screener |
| **Sentiment Analyst** | `get_social_sentiment()`, `get_whale_alerts()`, `get_fear_greed_index()` | LunarCrush API, Whale Alert, Alternative.me |
| **News Analyst** | `get_crypto_news()`, `get_global_crypto_news()`, `get_regulatory_updates()` | CryptoCompare API, CoinGecko News |
| **On-Chain Analyst** | `get_on_chain_metrics()`, `get_tokenomics()`, `get_defi_protocols()`, `get_protocol_security()` | DeFiLlama API, Dune Analytics, CoinGecko |

**Technical Indicators** (computed client-side from CoinGecko OHLCV):
- RSI (14-period), MACD, Bollinger Bands
- SMA (20/50/200), EMA (12/26)
- ATR (volatility), VWMA (volume-weighted)

**Conditional Routing for Tool-Calling**:
```python
def should_continue_market(state: AgentState) -> str:
    # Route to ToolNode if agent makes tool calls, otherwise proceed
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools_market"    # Execute tool calls
    return "msg_clear_market"    # Proceed to next analyst
```

### Enhancement 3: 5-Tier Portfolio Rating System

**Strategy**: Expand from 3 actions (buy/sell/hold) to a 5-tier rating system that captures conviction levels, inspired by institutional portfolio management practices.

| Rating | Meaning | Position Action |
|--------|---------|----------------|
| **Strong Buy** | High conviction bullish | Enter full position |
| **Buy** | Moderate conviction bullish | Enter half position |
| **Hold** | Neutral / wait | Maintain current position |
| **Sell** | Moderate conviction bearish | Exit half position |
| **Strong Sell** | High conviction bearish | Exit full position |

**Signal Processing**: Extract the rating from the Portfolio Manager's structured output using regex patterns:
```python
RATING_PATTERNS = [
    (r"strong\s*buy", "Strong Buy"),
    (r"buy|overweight|long", "Buy"),
    (r"hold|neutral|maintain", "Hold"),
    (r"sell|underweight|short", "Sell"),
    (r"strong\s*sell", "Strong Sell"),
]
```

### Enhancement 4: Structured Output with Pydantic Validation

**Strategy**: Replace free-form JSON parsing with Pydantic-validated models that enforce typed agent outputs, reducing parse errors and enabling downstream type checking.

```python
from pydantic import BaseModel, Field
from enum import Enum

class RatingTier(str, Enum):
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"

class TraderProposal(BaseModel):
    # Structured output from the Trader agent
    token_pair: str = Field(description="Trading pair analyzed")
    action: str = Field(description="Proposed action: buy/sell/hold")
    quantity: float = Field(description="Proposed trade quantity")
    reasoning: str = Field(description="Detailed reasoning for the proposal")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level")

class PortfolioDecision(BaseModel):
    # Structured output from the Portfolio Manager
    rating: RatingTier = Field(description="5-tier portfolio rating")
    reasoning: str = Field(description="Detailed reasoning for the rating")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level")
    position_adjustment: str = Field(description="Suggested position change")
```

### Enhancement 5: Risk Debate Agents

**Strategy**: Replace the single-pass risk scoring with a 3-agent adversarial debate that evaluates the Trader's proposal from different risk perspectives.

| Agent | Perspective | Risk Tolerance |
|-------|------------|----------------|
| **Aggressive Debator** | Maximizes return potential | High risk tolerance, favors leverage and concentrated positions |
| **Conservative Debator** | Prioritizes capital preservation | Low risk tolerance, favors diversification and stop-losses |
| **Neutral Debator** | Balanced risk-reward assessment | Moderate risk tolerance, weighs both upside and downside |

**Debate Flow**:
```
Trader Proposal → Aggressive → Conservative → Neutral → (cycle for max_risk_rounds) → Portfolio Manager
```

**State Tracking**:
```python
class RiskDebateState(TypedDict):
    aggressive_history: str    # Aggressive debator's arguments
    conservative_history: str  # Conservative debator's arguments
    neutral_history: str      # Neutral debator's arguments
    latest_speaker: str       # Who spoke last (for routing)
    count: int                 # Current round count
```

### Enhancement 6: Trading Memory Log with Reflection

**Strategy**: Implement an append-only decision log that persists across trading sessions, enabling the system to learn from past decisions.

**Two-Phase System**:
- **Phase A (Decision Time)**: `store_decision()` records the token pair, action, reasoning, confidence, and market conditions
- **Phase B (Outcome Resolution)**: `update_with_outcome()` resolves pending entries with actual returns after the holding period

**Memory Context Injection**:
```python
# Before each new analysis, inject past context
past_context = memory_log.get_past_context(
    ticker="ETH/USDT",
    n_same=5,     # Last 5 decisions for same pair
    n_cross=3,   # Last 3 decisions for other pairs (cross-market lessons)
)
```

**Reflection**: After each trading session, an LLM generates a reflection on the decision quality, stored alongside the decision for future reference.

### Enhancement 7: Checkpoint/Resume System

**Strategy**: Use LangGraph's `SqliteSaver` to persist graph state per token pair, enabling crash recovery for long-running debate graphs.

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Each token pair gets a deterministic thread ID
def thread_id(token_pair: str, trade_date: str) -> str:
    return f"{token_pair}_{trade_date}"

# Graph recompiled with checkpointer when enabled
checkpointer = SqliteSaver.from_conn_string("./data/checkpoints.db")
compiled_graph = workflow.compile(checkpointer=checkpointer)
```

### Enhancement 8: Debate State Schema

**Strategy**: Extend the current `AgentState` with debate-specific fields to support the multi-agent debate architecture.

```python
class InvestDebateState(TypedDict):
    # Tracks the Bull/Bear investment debate
    bull_history: str       # Bull researcher's arguments
    bear_history: str       # Bear researcher's arguments
    history: str            # Full debate history
    current_response: str   # Latest response
    count: int               # Current round count

class EnhancedAgentState(MessagesState):
    # Extended state for the debate architecture
    # Existing fields
    token_pair: str
    chain: str
    model_1: str
    model_2: str

    # Analyst reports
    market_report: str
    sentiment_report: str
    news_report: str
    onchain_report: str

    # Investment debate
    investment_debate_state: InvestDebateState
    investment_plan: str

    # Trading
    trader_investment_plan: str

    # Risk debate
    risk_debate_state: RiskDebateState
    final_trade_decision: str

    # Memory
    past_context: str        # Injected from TradingMemoryLog
```

### Implementation Priority Summary

| Phase | Features | Timeline |
|-------|----------|----------|
| **Phase 1** | Structured Output + 5-Tier Rating + Signal Processing | 1–2 weeks |
| **Phase 2** | Multi-Agent Debate Architecture + Debate State Schema | 2–3 weeks |
| **Phase 3** | Crypto-Native Data Tools + Tool-Calling + Conditional Routing | 2–3 weeks |
| **Phase 4** | Risk Debate Agents + Trading Memory Log | 2–3 weeks |
| **Phase 5** | Checkpoint/Resume + Reflection | 1–2 weeks |

---

## Notification System

### User Notification Preferences

Users can configure which notifications they receive:

| Preference | Description |
|------------|-------------|
| `newsletter_enabled` | Newsletter updates |
| `trading_updates` | Trade execution notifications |
| `profit_alerts` | Profit/loss notifications |
| `security_alerts` | Account security notifications |
| `system_updates` | Maintenance and feature updates |
| `daily_summary` | Daily trading summary email |
| `weekly_report` | Weekly performance report |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/notifications/preferences` | GET | Get user preferences |
| `/api/v1/notifications/preferences` | POST | Set user preferences |
| `/api/v1/notifications/send-activity` | POST | Send activity notification |
| `/api/v1/notifications/send-account-status` | POST | Send account status email |
| `/api/v1/notifications/send-daily-summary` | POST | Send daily summary |
| `/api/v1/notifications/send-weekly-report` | POST | Send weekly report |
| `/api/v1/notifications/history` | GET | Get notification history |
| `/api/v1/notifications/mark-read` | POST | Mark notification as read |
| `/api/v1/notifications/broadcast` | POST | Broadcast to all users (admin) |

### Email Templates

The system includes professional HTML email templates for:
- Newsletter with header/footer
- Profit alerts (green themed)
- Loss alerts (red themed with risk reminder)
- Security alerts (blue themed)
- Daily summary with stats grid
- Account status with verification info

### Frontend Page

Access at `/notifications` to:
- Toggle notification preferences
- Request account status email
- Request daily summary
- View notification history
- Mark notifications as read

---

## Escrow & Revenue System

### Trade Escrow Smart Contract

The system includes a Solidity smart contract (`contracts/TradeEscrow.sol`) for secure fund management:

#### Features
- **Fund Deposits**: Users deposit funds for trading
- **Trade Execution**: AI agent executes trades from escrow
- **Profit Collection**: Profits automatically added to escrow
- **Owner Withdrawals**: Contract owner can withdraw revenue share

#### Contract Functions

| Function | Description |
|----------|-------------|
| `deposit()` | Deposit ETH to escrow |
| `executeTrade()` | Execute trade from escrow (agent only) |
| `collectProfit()` | Add trading profits to escrow |
| `withdraw()` | Owner withdraws funds |
| `getBalance()` | Get escrow balance |

#### Backend API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/escrow/deposit` | POST | Deposit to escrow |
| `/api/v1/escrow/execute-trade` | POST | Execute trade from escrow |
| `/api/v1/escrow/withdraw` | POST | Owner withdraw funds |
| `/api/v1/escrow/balance` | GET | Get escrow balance |
| `/api/v1/escrow/history` | GET | Get transaction history |

#### Frontend Dashboard

Access at `/escrow` to:
- View escrow balance
- Deposit funds
- View transaction history
- Owner: Withdraw revenue share

---

## Identity Verification System

### Overview

The Identity Verification System requires all users to verify their identity through **GitHub** or **LinkedIn** OAuth before they can trade. This blocks hackers, bots, and malicious actors from accessing the trading system.

**Key principle:** Unverified users CANNOT trade — no exceptions. Every trading endpoint enforces this gate.

### Identity Derivation Policy

**User profiles are derived EXCLUSIVELY from their GitHub and LinkedIn accounts.** Users cannot set a custom username, alias, or display name in this system. Their identity is the combination of their verified OAuth provider profiles.

| Scenario | Display Name |
|----------|-------------|
| GitHub only | `GitHub Display Name` or `@github_username` |
| LinkedIn only | `LinkedIn Display Name` or `linkedin_username` |
| Both (dual) | `GitHub Name / LinkedIn Name` |

The system stores each provider's username and display name separately (`github_username`, `linkedin_username`, `github_display_name`, `linkedin_display_name`). The combined `display_name` is auto-derived from these — **no custom aliases are allowed**.

This ensures every user's identity is traceable to a real, verified external profile, preventing impersonation and alias-based evasion.

### Verification Requirements

Users must meet **all** of the following criteria to pass verification:

| Requirement | GitHub | LinkedIn |
|-------------|--------|----------|
| Account age | ≥ 1 year (365 days) | ≥ 1 year (365 days) |
| Public repos | ≥ 3 | N/A |
| Connections | N/A | ≥ 10 |
| Profile completeness | Bio or display name required | Verified email + profile completeness |

**Accounts less than 1 year old are automatically rejected** — this prevents freshly-created accounts from passing verification, blocking hackers who create disposable accounts.

### Verification Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│  1. User clicks "Verify with GitHub" or "Verify with LinkedIn"          │
│  2. OAuth redirect to provider → User authorizes                         │
│  3. Provider returns authorization code                                   │
│  4. Backend exchanges code for access token                               │
│  5. Backend fetches public profile data (token used once, then discarded)│
│  6. Profile validated against minimum requirements                        │
│  7. Verification status stored in user record                            │
│  8. User can now trade                                                    │
└──────────────────────────────────────────────────────────────────────────┘
```

### Security Measures

- **Access tokens are NEVER stored** — used once to fetch profile, then discarded
- **Only verification status + provider username are persisted**
- **Rate-limited** to 5 verification attempts per email per hour
- **Creator details are masked** in API responses — internal admin accounts show as `"verified"` provider with `***` username
- **All verification events are logged** via the security event system

### Protected Endpoints

The following endpoints require identity verification. Unverified users receive **HTTP 403** with a detailed error message.

| Endpoint | Method | Protection |
|----------|--------|------------|
| `/api/v1/trading/execute` | POST | Inline verification gate |
| `/api/v1/dex/swap/ethereum` | POST | `Depends(require_verified_identity)` |
| `/api/v1/dex/swap/solana` | POST | `Depends(require_verified_identity)` |
| `/api/v1/paper-trading/session/start` | POST | `Depends(require_verified_identity)` |
| `/api/v1/paper-trading/order` | POST | `Depends(require_verified_identity)` |
| `/api/v1/escrow/deposit` | POST | `Depends(require_verified_identity)` |
| `/api/v1/escrow/withdraw` | POST | `Depends(require_verified_identity)` |
| `/api/v1/escrow/withdraw-all` | POST | `Depends(require_verified_identity)` |
| `/api/v1/escrow/record-trade` | POST | `Depends(require_verified_identity)` |

### Identity Verification API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/identity/status` | GET | Check verification status |
| `/api/v1/identity/requirements` | GET | Get verification requirements |
| `/api/v1/identity/github/auth-url` | GET | Get GitHub OAuth redirect URL |
| `/api/v1/identity/github/verify` | POST | Complete GitHub verification |
| `/api/v1/identity/linkedin/auth-url` | GET | Get LinkedIn OAuth redirect URL |
| `/api/v1/identity/linkedin/verify` | POST | Complete LinkedIn verification |

### Frontend Integration

The `AuthPage.jsx` includes an "Verify Identity" view with:
- GitHub OAuth button (redirects to GitHub authorization)
- LinkedIn OAuth button (redirects to LinkedIn authorization)
- Verification status display
- Warning message for unverified users
- Link from login form to verification page

---

## Cloud Identity Store (AWS DynamoDB)

### Overview

The Cloud Identity Store provides **serverless, military-grade persistent storage** for verified user identity records using AWS DynamoDB. This is the strongest security available for real trading — identity data must survive server restarts, deployments, and scale horizontally.

**Key principle:** The in-memory `_verification_db` is a local cache. DynamoDB is the source of truth. On startup, cloud records are pulled into the local cache. Every write is synced to DynamoDB in real-time.

### Security Architecture

| Layer | Protection | Details |
|-------|-----------|---------|
| **Encryption at rest** | AWS KMS (Customer Managed Key) | AES-256 encryption with customer-controlled KMS key |
| **Encryption in transit** | TLS 1.2+ | All DynamoDB API calls encrypted via HTTPS |
| **Access control** | IAM least-privilege | Only `dynamodb:PutItem`, `GetItem`, `Query`, `Scan` on the identity table |
| **Data durability** | 99.999999999% (11 nines) | DynamoDB replicates across 3 AZs |
| **Backup** | Point-in-Time Recovery (PITR) | Restore to any second in the last 35 days |
| **Auto-expiry** | DynamoDB TTL | Unverified records auto-expire after 30 days |
| **Audit** | CloudTrail | All DynamoDB API calls logged for compliance |

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│  Application Startup                                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  sync_cloud_on_startup() → pull_to_local()                    │ │
│  │  Loads all DynamoDB records into _verification_db cache        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Write Path (store_verification)                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  1. Write to local _verification_db (instant)                 │ │
│  │  2. cloud_store.put_identity() → DynamoDB PutItem (async)     │ │
│  │  3. If DynamoDB fails → local record still valid (cache)      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Read Path (is_user_verified / get_user_verification)                │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  1. Check local _verification_db first (fast)                  │ │
│  │  2. If not found → cloud_store.get_identity() (DynamoDB)      │ │
│  │  3. Cache result locally for subsequent reads                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### DynamoDB Table Schema

| Attribute | Type | Description |
|-----------|------|-------------|
| `email` (PK) | String | User email — partition key |
| `provider` | String | `"github"` / `"linkedin"` / `"dual"` / `"creator"` |
| `provider_username` | String | Primary provider username |
| `display_name` | String | Auto-derived from GitHub + LinkedIn (no custom aliases) |
| `github_username` | String | GitHub username (identity from provider only) |
| `linkedin_username` | String | LinkedIn username (identity from provider only) |
| `github_display_name` | String | GitHub display name |
| `linkedin_display_name` | String | LinkedIn display name |
| `verified` | Boolean | Whether identity is verified |
| `verified_at` | String | ISO 8601 timestamp of verification |
| `reputation_score` | Number | Verification reputation score |
| `crypto_priority` | String | `"veteran"` / `"experienced"` / `"rookie"` / `"no_experience"` |
| `crypto_estimated_years` | Number | Estimated years of crypto experience |
| `crypto_can_trade` | Boolean | Whether user has sufficient crypto experience |
| `crypto_signals_json` | String | JSON-serialized list of experience signals |
| `dual_verified` | Boolean | Whether both GitHub + LinkedIn are verified |
| `providers_json` | String | JSON-serialized list of verified providers |
| `updated_at` | String | Last update timestamp |
| `ttl` | Number | Unix epoch expiry time (unverified records only) |

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DYNAMODB_ENABLED` | `false` | Enable DynamoDB cloud storage |
| `DYNAMODB_TABLE_NAME` | `ai-trading-identity-verification` | DynamoDB table name |
| `DYNAMODB_REGION` | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | `""` | AWS access key (leave empty for IAM role) |
| `AWS_SECRET_ACCESS_KEY` | `""` | AWS secret key (leave empty for IAM role) |
| `DYNAMODB_KMS_KEY_ID` | `""` | KMS CMK for encryption at rest (empty = AWS-owned key) |
| `DYNAMODB_PITR_ENABLED` | `true` | Enable Point-in-Time Recovery |
| `DYNAMODB_TTL_DAYS_UNVERIFIED` | `30` | Auto-expire unverified records after N days |

### Deployment Best Practices

1. **Production:** Use IAM roles (EC2 instance profile, ECS task role, or Lambda execution role) — **never hardcode AWS keys**
2. **KMS:** Create a Customer Managed Key (CMK) and set `DYNAMODB_KMS_KEY_ID` for customer-controlled encryption
3. **IAM Policy:** Restrict to only the identity table with least-privilege actions:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "dynamodb:PutItem",
       "dynamodb:GetItem",
       "dynamodb:UpdateItem",
       "dynamodb:Query",
       "dynamodb:Scan"
     ],
     "Resource": "arn:aws:dynamodb:*:*:table/ai-trading-identity-verification"
   }
   ```
4. **PITR:** Always enabled in production — protects against accidental data loss
5. **CloudTrail:** Enable DynamoDB data plane logging for audit compliance
6. **VPC Endpoint:** Use DynamoDB VPC endpoint to keep traffic off the public internet

### Fallback Behavior

When `DYNAMODB_ENABLED=false` (default), the system uses the in-memory `_verification_db` dict as both cache and source of truth. This is suitable for development and testing but **not for production** — identity records are lost on server restart.

When DynamoDB is enabled but temporarily unavailable (network error, throttling), the system gracefully degrades:
- **Writes:** Local record is still stored; DynamoDB sync fails silently with a warning log
- **Reads:** Local cache is used; DynamoDB lookup is skipped
- **Startup:** If DynamoDB pull fails, the system starts with an empty local cache

---

## Crypto Experience Priority System

### Overview

The Crypto Experience Priority System assesses users' cryptocurrency expertise based on their GitHub repositories, LinkedIn positions, and web presence. Users are assigned a priority level that determines their trading access — users with insufficient crypto experience are **blocked from trading**.

**Key principle:** Identity verification proves *who* you are; crypto experience determines *whether you can trade*. Both must pass.

### Priority Levels

| Priority | Badge | Experience | Trading Access |
|----------|-------|-----------|----------------|
| **Veteran** | ⭐ | > 5 years | Full access — Priority 1 |
| **Experienced** | 🏅 | 3–5 years | Full access — Priority 2 |
| **Rookie** | 🌱 | 2–3 years | Limited access — Priority 3 |
| **Blocked** | 🚫 | < 2 years | **No trading access** |

### Assessment Sources

The system evaluates crypto experience from three independent sources:

1. **GitHub Crypto Repositories** — Scans public repos for crypto-related keywords (bitcoin, ethereum, defi, web3, nft, uniswap, smart-contract, etc.)
   - Each crypto repo contributes +0.5 years estimated experience
   - Bio containing crypto keywords contributes +1.0 years
   - GitHub account age contributes up to +0.5 years

2. **LinkedIn Crypto Positions** — Checks job titles and companies for crypto-related roles
   - Crypto-related role (e.g. "Blockchain Developer") contributes +1.5 years
   - Crypto company (e.g. Binance, Coinbase, Consensys) contributes +2.0 years

3. **Web Presence Search** — DuckDuckGo HTML search for crypto-related mentions
   - Press articles mentioning the user + crypto contribute +0.3 years each
   - YouTube/TikTok channels with crypto content contribute +0.3 years each
   - Personal websites with crypto content contribute +0.3 years each

### Dual Verification Bonus

Users who verify with **both** GitHub and LinkedIn receive a +1.0 year bonus to their estimated experience, rewarding verified multi-platform identity.

### Scoring Algorithm

```
estimated_years = sum_of_all_signals
if dual_verified:
    estimated_years += 1.0

if estimated_years > 5.0:
    priority = VETERAN
elif estimated_years >= 3.0:
    priority = EXPERIENCED
elif estimated_years >= 2.0:
    priority = ROOKIE
else:
    priority = NO_EXPERIENCE  # BLOCKED from trading
```

### Crypto Experience API

The crypto experience data is returned as part of the identity verification endpoints:

| Field | Type | Description |
|-------|------|-------------|
| `crypto_priority` | string | One of: `veteran`, `experienced`, `rookie`, `no_experience` |
| `crypto_estimated_years` | float | Estimated years of crypto experience |
| `crypto_can_trade` | bool | Whether the user is allowed to trade |
| `crypto_signals` | list | Breakdown of experience signals detected |
| `dual_verified` | bool | Whether both GitHub and LinkedIn are verified |

### Frontend Display

The `AuthPage.jsx` displays crypto experience after verification:
- **Priority badge** — ⭐ Veteran, 🏅 Experienced, 🌱 Rookie, or 🚫 Blocked
- **Dual verified badge** — 🔗 Dual Verified indicator
- **Estimated years** — "Estimated: X.X years crypto experience"
- **Signal breakdown** — List of detected experience signals

---

## Device Ban & Abuse Detection System

### Overview

The Device Ban & Abuse Detection System protects the platform from hazardous users who cause traffic jams, DDoS attacks, brute force attempts, or other abusive behavior. Devices are identified by **browser fingerprint hashes** and **persistent device UUIDs**, and banned devices are blocked at the middleware level.

**Key principle:** Abusive devices are automatically detected and banned. When one device is banned, ALL associated devices (same email, same fingerprint) are also blocked.

### Device Identification

Devices are identified through two mechanisms:

1. **Device UUID** — Client-generated UUID stored in `localStorage`, sent as `X-Device-ID` header
2. **Browser Fingerprint Hash** — SHA-256 hash of browser attributes (User-Agent, screen resolution, timezone, platform, language), sent as `X-Device-Fingerprint` header

The fingerprint hash ensures that even if a user clears their localStorage (generating a new UUID), the browser fingerprint will still identify the device.

### Auto-Detection Thresholds

The system automatically detects and bans abusive behavior:

| Abuse Type | Threshold | Auto-Ban Duration |
|------------|-----------|-------------------|
| **DDoS / Traffic Jam** | > 60 requests/minute | 1 hour temporary ban |
| **Brute Force** | > 10 failed auth attempts / 5 min | 24 hour temporary ban |
| **Verification Abuse** | > 20 failed verification attempts / hour | Permanent ban |
| **Trading Abuse** | > 30 trades/minute | Logged + flagged |

### Ban Severity Levels

| Severity | Description |
|----------|-------------|
| **Warning** | First offense — logged, not blocked |
| **Temporary** | Blocked for a specified duration (hours) |
| **Permanent** | Blocked forever — all associated devices blocked |

### Ban Cascade

When a device is banned, the system automatically bans:

1. **The device itself** — Added to active bans list
2. **The device fingerprint** — Any device with the same fingerprint hash is blocked
3. **The user email** — All devices associated with the email are blocked
4. **All same-fingerprint devices** — Multiple browser profiles on the same physical device

This prevents banned users from simply creating new accounts or clearing their localStorage.

### Ban Reasons

| Reason | Code | Trigger |
|--------|------|---------|
| DDoS Attack | `ddos_attack` | Auto: excessive API requests |
| Brute Force | `brute_force` | Auto: excessive failed auth |
| Verification Abuse | `verification_abuse` | Auto: excessive failed verification |
| Trading Abuse | `trading_abuse` | Auto: excessive rapid trades |
| Manipulation | `manipulation` | Admin: market manipulation |
| Fraud | `fraud` | Admin: fraudulent activity |
| Admin Ban | `admin_ban` | Admin: manual ban |
| Account Compromise | `account_compromise` | Admin: account takeover detected |

### Device Ban API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/device/register` | POST | Register device (returns 403 if banned) |
| `/api/v1/device/status` | GET | Check ban status |
| `/api/v1/device/ban` | POST | Admin: Ban device/email/fingerprint |
| `/api/v1/device/unban` | POST | Admin: Unban device |
| `/api/v1/device/bans` | GET | Admin: List all active bans |
| `/api/v1/device/incidents` | GET | Admin: List abuse incidents |

### Middleware Flow

Every API request passes through the `device_ban_middleware`:

```
Request → Check X-Device-ID / X-Device-Fingerprint headers
        → Skip for health/docs endpoints
        → Register/update device record
        → Auto-detect abuse (rate limits)
        → Check if device/fingerprint/email is banned
        → If banned → HTTP 403 with ban reason
        → If allowed → Continue to endpoint
```

### Frontend Integration

The `DeviceContext.jsx` provides:
- **Persistent device UUID** — Generated once, stored in `localStorage`
- **Browser fingerprint hash** — SHA-256 via Web Crypto API
- **Ban status checking** — On mount and after login
- **Device registration** — Automatic after successful login
- **Device headers** — `X-Device-ID`, `X-Device-Fingerprint`, `X-User-Email` included in API requests
- **Ban overlay** — Full-screen blocked message if device is banned

---

## Mock Money Simulation

### Overview

The Mock Money Simulation adds virtual cryptocurrency trading to the backtesting engine. Users can see how their strategies would perform with simulated crypto balances. **No fees or slippage are applied** — the simulation is pure, showing exactly how earnings would happen without any virtual costs.

**All balances are simulated — no real funds are used. No fees, no slippage — pure simulation.**

### How It Works

When a backtest runs, a `MockMoneyAccount` is created with initial virtual balances:

| Asset | Default Initial Balance |
|-------|------------------------|
| USDT | $100,000 |
| BTC | 0.5 ₿ |
| ETH | 5.0 Ξ |
| SOL | 50.0 ◎ |

As the backtest engine generates trade decisions, the mock money account:
1. **Executes virtual trades** — buys/sells at backtest prices with NO fees or slippage
2. **Tracks all balances** — USDT, BTC, ETH, SOL
3. **Computes P&L** — absolute ($), percentage (%) — no fees deducted

### Mock Money Display

The `BacktestPage.jsx` shows a "Mock Money Simulation" card with:

- **Balances grid** — USDT, BTC, ETH, SOL with icons
- **Portfolio metrics** — Total value, P&L ($), P&L (%) — no fees applied
- **Trade log table** — Each simulated trade with side, symbol, quantity, price, fee
- **Disclaimer banner** — "⚠️ ALL BALANCES ARE SIMULATED" warning

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `MOCK_MONEY_INITIAL_USD` | 100000 | Initial USDT balance |
| `MOCK_MONEY_INITIAL_BTC` | 0.5 | Initial BTC balance |
| `MOCK_MONEY_INITIAL_ETH` | 5.0 | Initial ETH balance |
| `MOCK_MONEY_INITIAL_SOL` | 50.0 | Initial SOL balance |
| `MOCK_MONEY_FEE_PCT` | 0.0 | Always 0 — no fees in simulation |
| `MOCK_MONEY_SLIPPAGE_PCT` | 0.0 | Always 0 — no slippage in simulation |

### Modal GLM-5 Endpoint

Backtesting can optionally route through **Modal serverless GPU infrastructure** for high-performance inference:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODAL_API_KEY` | (empty) | Modal API key for GLM-5 endpoint |
| `MODAL_BASE_URL` | `https://modal.com/glm-5-endpoint` | Modal serverless endpoint URL |
| `MODAL_MODEL` | `glm-5` | Model identifier on Modal |
| `BACKTEST_USE_MODAL` | `false` | Enable Modal for backtesting |

When `MODAL_API_KEY` is set and `BACKTEST_USE_MODAL=true`, the backtest LLM provider routes through Modal's serverless infrastructure instead of the default Ollama/OpenRouter path.

---

## Cybersecurity Beware List Screening

### Overview

During identity verification, every user is automatically screened against multiple public cybersecurity threat databases and sanctions lists. This prevents known malicious actors, sanctioned individuals, and crypto scammers from accessing the platform.

**This is a HARD BLOCK — if a user matches ANY beware list, verification is rejected.**

### Checked Sources

| Source | Type | Severity | API |
|--------|------|----------|-----|
| OFAC SDN (US Treasury) | Government sanctions | Critical | Public (no key) |
| Interpol Red Notices | International fugitives | Critical | Public (no key) |
| EU Consolidated Sanctions | Regional sanctions | Critical | Public (no key) |
| Known Threat Actor Aliases | FBI/DOJ public intel | Critical–High | Local database |
| CryptoScamDB | Crypto scam addresses | High | Public API |
| Web Threat Intelligence | Search-based detection | Medium | SerpAPI (optional) |

### How It Works

1. User completes GitHub or LinkedIn OAuth verification
2. Profile passes identity validation (account age, completeness)
3. **Cybersecurity beware list screening runs automatically:**
   - Fast local check against known threat actor aliases (FBI Cyber Most Wanted, DOJ, public intel)
   - If no critical match found locally, API checks run in parallel:
     - OFAC SDN search by name
     - Interpol Red Notice search by name
     - EU Consolidated Sanctions search
     - CryptoScamDB check by username
     - Web search for threat-related mentions (if SERPAPI_KEY configured)
4. If ANY match found → verification is **REJECTED** with a hard block
5. Match details are logged via the security event system
6. Results are cached for 24 hours

### Match Severity

| Severity | Description | Action |
|----------|-------------|--------|
| **Critical** | Match on OFAC, Interpol, or government sanctions | Immediate rejection — hard block |
| **High** | Match on known threat actor alias or CryptoScamDB | Immediate rejection — hard block |
| **Medium** | Web search found threat-related mention | Rejection — manual review required |

### Caching

- Beware list results are cached in memory for **24 hours** per user
- Cache key: normalized display name + username
- Avoids repeated API calls for the same user across verification attempts
- Cache can be cleared via `cybersecurity_beware.clear_cache()`

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SERPAPI_KEY` | (empty) | SerpAPI key for web threat intelligence search (optional) |
| `SEARCH_API_KEY` | (empty) | Alternative search API key (optional) |

> **Note:** Web threat intelligence search is optional. All other checks (OFAC, Interpol, EU, CryptoScamDB, known aliases) work without any API keys.

### API Response

The `/api/v1/identity/status` endpoint includes beware list screening results:

```json
{
  "beware_list_clean": true,
  "beware_list_matches": []
}
```

If a match is found:

```json
{
  "beware_list_clean": false,
  "beware_list_matches": [
    {
      "source": "OFAC SDN (US Treasury Sanctions)",
      "matched_name": "John Doe",
      "match_type": "exact",
      "severity": "critical",
      "details": "Found on US Treasury sanctions list. Entity ID: 12345"
    }
  ]
}
```

---

## API Reference

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/signup` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login (returns requires_2fa if enabled) |
| `/api/v1/auth/verify-2fa` | POST | Verify 2FA code |
| `/api/v1/auth/setup-2fa` | POST | Set up 2FA |
| `/api/v1/auth/forgot-password` | POST | Request password reset |
| `/api/v1/auth/reset-password` | POST | Reset password with token |
| `/api/v1/auth/profile` | GET | Get user profile |
| `/api/v1/auth/timezone` | GET | Get timezone/daytime status |

### Trading Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/trading/execute` | POST | Execute a trade (**requires identity verification**) |
| `/api/v1/trading/analyze` | POST | Get market analysis |
| `/api/v1/trading/risk/assess` | POST | Assess trade risk |

### Identity Verification Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/identity/status` | GET | Check verification status |
| `/api/v1/identity/requirements` | GET | Get verification requirements |
| `/api/v1/identity/github/auth-url` | GET | Get GitHub OAuth redirect URL |
| `/api/v1/identity/github/verify` | POST | Complete GitHub verification |
| `/api/v1/identity/linkedin/auth-url` | GET | Get LinkedIn OAuth redirect URL |
| `/api/v1/identity/linkedin/verify` | POST | Complete LinkedIn verification |

### DEX Swap Endpoints (**requires identity verification**)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/dex/swap/ethereum` | POST | Execute Ethereum DEX swap |
| `/api/v1/dex/swap/solana` | POST | Execute Solana DEX swap |

### Paper Trading Endpoints (**requires identity verification**)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/paper-trading/session/start` | POST | Start paper trading session |
| `/api/v1/paper-trading/session/stop` | POST | Stop paper trading session |
| `/api/v1/paper-trading/order` | POST | Submit paper trading order |

### Notification Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/notifications/preferences` | GET/POST | Get/set preferences |
| `/api/v1/notifications/send-activity` | POST | Send activity notification |
| `/api/v1/notifications/send-account-status` | POST | Send account status |
| `/api/v1/notifications/history` | GET | Get notification history |

### Escrow Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/escrow/deposit` | POST | Deposit to escrow |
| `/api/v1/escrow/withdraw` | POST | Owner withdraw |
| `/api/v1/escrow/balance` | GET | Get balance |
| `/api/v1/escrow/history` | GET | Get history |

### Device Ban Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/device/register` | POST | Register device (returns 403 if banned) |
| `/api/v1/device/status` | GET | Check device ban status |
| `/api/v1/device/ban` | POST | Admin: Ban device/email/fingerprint |
| `/api/v1/device/unban` | POST | Admin: Unban device |
| `/api/v1/device/bans` | GET | Admin: List all active bans |
| `/api/v1/device/incidents` | GET | Admin: List abuse incidents |

---

## Frontend Components

### Page Structure

```
App.jsx
├── AuthPage.jsx (/login)
│   ├── Signup Form
│   ├── Login Form
│   ├── 2FA Verification Screen
│   ├── Identity Verification (GitHub/LinkedIn)
│   ├── Crypto Experience Priority Display
│   └── Password Reset
├── TradingDashboard.jsx (/)
│   ├── Model Selection (dual-model)
│   ├── Chain Selection (ethereum/solana)
│   ├── Prompt Input
│   └── Result Display
├── BacktestPage.jsx (/backtest)
│   ├── Mock Money Simulation Display
│   └── Virtual Balance Cards (BTC/ETH/SOL/USDT)
│   └── Crypto Priority Badge (⭐🏅🌱🚫)
├── RiskDashboardPage.jsx (/risk)
├── EscrowDashboard.jsx (/escrow)
├── NotificationsPage.jsx (/notifications)
├── StrategyPage.jsx (/strategy)
├── DebateArenaPage.jsx (/debate)
├── ConfigPage.jsx (/config)
├── SecurityPage.jsx (/security)
├── GovernancePage.jsx (/governance)
├── KnowledgePage.jsx (/knowledge)
├── PaymentsPage.jsx (/payments)
└── FAQPage.jsx (/faq)
```

### Contexts

| Context | File | Purpose |
|---------|------|---------|
| `AuthContext` | `contexts/AuthContext.jsx` | User authentication, 2FA |
| `ThemeContext` | `contexts/ThemeContext.jsx` | Auto day/night theme |
| `AppModeContext` | `contexts/AppModeContext.jsx` | Paper/Live trading mode |
| `WalletContext` | `contexts/WalletContext.jsx` | Web3 wallet connection |
| `DeviceContext` | `contexts/DeviceContext.jsx` | Device fingerprinting, ban detection |

---

## Configuration

### Backend Environment Variables

```bash
# Trading Mode
TRADING_MODE=paper              # "paper" or "live"
LIVE_TRADING_ENABLED=false      # Must be true for live

# LLM Configuration
OPENROUTER_API_KEY=sk-xxx      # OpenRouter API key
DEFAULT_MODEL_1=glm-5.1        # Planner + Controller
DEFAULT_MODEL_2=grok-4.3      # Verifier

# Authentication
JWT_SECRET=your-secret-key     # JWT signing key
TWILIO_ACCOUNT_SID=xxx          # Twilio for SMS 2FA
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+xxx

# Email Notifications
SENDGRID_API_KEY=xxx           # SendGrid for emails
EMAIL_FROM=noreply@yourdomain.com

# Identity Verification
IDENTITY_VERIFICATION_REQUIRED=true  # Require GitHub/LinkedIn verification for trading
GITHUB_CLIENT_ID=xxx                 # GitHub OAuth app client ID
GITHUB_CLIENT_SECRET=xxx             # GitHub OAuth app client secret
LINKEDIN_CLIENT_ID=xxx               # LinkedIn OAuth app client ID
LINKEDIN_CLIENT_SECRET=xxx           # LinkedIn OAuth app client secret
IDENTITY_MIN_ACCOUNT_AGE_DAYS=365    # Minimum account age (1 year)
IDENTITY_MIN_GITHUB_REPOS=3          # Minimum GitHub public repos
IDENTITY_MIN_LINKEDIN_CONNECTIONS=10 # Minimum LinkedIn connections

# AWS DynamoDB — Cloud Identity Store (Serverless, KMS-encrypted)
DYNAMODB_ENABLED=false               # Enable DynamoDB cloud storage (requires AWS credentials)
DYNAMODB_TABLE_NAME=ai-trading-identity-verification
DYNAMODB_REGION=us-east-1            # AWS region
AWS_ACCESS_KEY_ID=                   # Leave empty to use IAM role
AWS_SECRET_ACCESS_KEY=               # Leave empty to use IAM role
DYNAMODB_KMS_KEY_ID=                 # KMS CMK for encryption at rest (empty = AWS-owned key)
DYNAMODB_PITR_ENABLED=true          # Point-in-Time Recovery
DYNAMODB_TTL_DAYS_UNVERIFIED=30     # Auto-expire unverified records

# Crypto Experience Priority
# (No additional config — uses GitHub/LinkedIn tokens from identity verification)
# Priority levels: veteran (>5yr), experienced (3-5yr), rookie (2-3yr), blocked (<2yr)
# Users with <2yr crypto experience are blocked from trading

# Device Ban & Abuse Detection
# (No additional config — auto-detection thresholds are built-in)
# Rate limits: 60 req/min, 10 failed auth/5min, 20 failed verify/hr, 30 trades/min

# Mock Money Simulation (Backtesting)
MOCK_MONEY_INITIAL_USD=100000        # Initial USDT balance
MOCK_MONEY_INITIAL_BTC=0.5           # Initial BTC balance
MOCK_MONEY_INITIAL_ETH=5.0           # Initial ETH balance
MOCK_MONEY_INITIAL_SOL=50.0          # Initial SOL balance
MOCK_MONEY_FEE_PCT=0.0               # Always 0 — no fees in simulation
MOCK_MONEY_SLIPPAGE_PCT=0.0           # Always 0 — no slippage in simulation

# Modal GLM-5 Endpoint (Backtesting)
MODAL_API_KEY=                       # Modal API key (optional)
MODAL_BASE_URL=https://modal.com/glm-5-endpoint
BACKTEST_USE_MODAL=false             # Route backtests through Modal

# Risk System
RISK_STORAGE_PATH=./data/risk_history.db

# Live Mode Safeguards
LIVE_GUARD_SECRET=xxx           # HMAC signature key
LIVE_GUARD_MAX_SKEW_SECONDS=300

# x402 Payments
X402_ENABLED=false
X402_RECIPIENT_ADDRESS=0x...
```

### Frontend Environment Variables

```bash
VITE_API_BASE=/api/v1          # Backend API base URL
```

---

## Installation Guide

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | `brew install python@3.11` |
| Node.js | 20+ | `brew install node` |
| Git | Latest | `brew install git` |
| Foundry | Latest | `curl -L https://foundry.paradigm.xyz \| bash` |

### Quick Start

```bash
# 1. Clone and start
git clone <your-repo-url>
cd "AI Agent In Blockchain Trading"
chmod +x start.sh
./start.sh

# 2. Access the application
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup

```bash
# Backend
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## Safety Mechanisms

### 1. Pre-Execution Risk Check
- CRITICAL risk (76+) blocks execution immediately
- HIGH risk (51-75) reduces position size
- All assessments logged to SQLite

### 2. Two-Factor Authentication
- SMS-based 2FA for login
- 6-digit verification code
- 5-minute expiration
- Required for sensitive operations

### 3. Multi-Agent Consensus
- Planner proposes, Verifier audits
- Controller makes final decision (PoT)
- Both models must agree for execution

### 4. Fail-Closed Design
- Missing data → Block execution
- API failures → Block execution
- Invalid 2FA → Block access
- CRITICAL risk → Block execution
- Unverified identity → Block all trading

### 5. Identity Verification Gate
- GitHub or LinkedIn OAuth required before trading
- Accounts must be ≥ 1 year old (365 days) to pass verification
- Freshly-created accounts are automatically rejected
- 9 trading endpoints enforce verification (HTTP 403 if unverified)
- Rate-limited to 5 verification attempts per email per hour
- Access tokens never stored — used once then discarded
- Creator/admin details are masked in API responses

### 6. Crypto Experience Priority Gate
- Users are assessed for crypto experience from GitHub repos, LinkedIn roles, and web presence
- Users with < 2 years estimated crypto experience are **BLOCKED from trading**
- Dual verification (both GitHub + LinkedIn) grants +1.0 year experience bonus
- Priority levels: ⭐ Veteran (>5yr), 🏅 Experienced (3-5yr), 🌱 Rookie (2-3yr), 🚫 Blocked (<2yr)
- Experience signals: crypto repos, crypto job roles, crypto companies, web mentions

### 7. Device Ban & Abuse Detection
- All API requests pass through device ban middleware
- Devices identified by browser fingerprint hash + persistent UUID
- Auto-detection: DDoS (>60 req/min), brute force (>10 failed auth/5min), verification abuse (>20/hr)
- Ban cascade: banning one device also bans same fingerprint, same email, all associated devices
- Temporary bans (1-24 hours) for rate abuse; permanent bans for severe violations
- Frontend displays full-screen ban overlay if device is blocked

### 8. Cloud Identity Store (DynamoDB) Data Protection
- Identity records encrypted at rest with AWS KMS (AES-256)
- Point-in-Time Recovery (PITR) protects against accidental data loss
- Unverified records auto-expire via DynamoDB TTL (30 days default)
- IAM least-privilege policies restrict access to identity table only
- Graceful degradation: if DynamoDB is unavailable, local cache is used
- Verified records never expire — only unverified records auto-expire

### 9. Mock Money Safety
- All backtest mock money balances are SIMULATED — no real funds
- Prominent disclaimer banner in UI: "⚠️ ALL BALANCES ARE SIMULATED"
- **No fees or slippage** — pure simulation with zero virtual costs, showing exact earnings
- Mock money data is clearly separated from real portfolio data

### 10. Cybersecurity Beware List Screening
- Every user identity is checked against public cybersecurity threat databases during verification
- Sources: OFAC SDN (US Treasury), Interpol Red Notices, EU Sanctions, CryptoScamDB, known threat actor aliases
- Hard block: if a user matches ANY beware list, verification is rejected regardless of other checks
- Results are cached for 24 hours to avoid repeated lookups
- Match severity levels: critical (sanctions/wanted), high (known threat actor), medium (web intelligence)
- Critical matches (OFAC, Interpol) cause immediate rejection; medium matches trigger manual review

---

## Troubleshooting

### Common Issues

#### "CRITICAL RISK BLOCKED"
**Cause:** Risk score exceeds 75
**Solution:** Check market conditions. High volatility or low liquidity may trigger this.

#### "2FA code expired"
**Cause:** More than 5 minutes passed since code was sent
**Solution:** Request a new code by logging in again

#### "TRADING BLOCKED: Identity verification required"
**Cause:** User has not verified identity via GitHub or LinkedIn
**Solution:** Visit the Verify Identity page and complete GitHub or LinkedIn OAuth verification. Your account must be at least 1 year old.

#### "Identity verification failed: Account too new"
**Cause:** GitHub or LinkedIn account is less than 1 year old
**Solution:** Only accounts that have existed for ≥ 365 days can pass verification. This prevents freshly-created accounts from accessing the trading system.

#### "TRADING BLOCKED: Insufficient crypto experience"
**Cause:** User's estimated crypto experience is less than 2 years
**Solution:** Connect both GitHub and LinkedIn for dual verification bonus. Ensure your GitHub has public crypto-related repositories and your LinkedIn lists crypto-related roles or companies.

#### "ACCESS BLOCKED: Device banned"
**Cause:** The device has been banned due to abusive behavior (DDoS, brute force, verification abuse)
**Solution:** Temporary bans expire automatically (1-24 hours). Permanent bans require admin intervention. Contact support if you believe this is an error.

#### "Device fingerprint banned"
**Cause:** The browser fingerprint matches a previously banned device
**Solution:** This occurs when the same physical device was previously banned. Contact support to resolve.

#### "Email notifications not received"
**Cause:** Email provider configuration missing
**Solution:** Configure SendGrid/AWS SES in backend/.env

#### Risk Dashboard shows no data
**Cause:** SQLite database empty or inaccessible
**Solution:** Execute some trades first, check data directory permissions

#### "DynamoDB cloud identity sync failed"
**Cause:** AWS credentials misconfigured or DynamoDB table doesn't exist
**Solution:** Verify `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` or use IAM role; ensure `DYNAMODB_ENABLED=true`; table auto-creates on first use if IAM permissions allow

#### "IDENTITY BLOCKED: Matches on cybersecurity sanctions/threat lists"
**Cause:** User's name or username matches entries on OFAC, Interpol, EU sanctions, CryptoScamDB, or known threat actor aliases
**Solution:** This is a hard block for platform safety. If you believe this is a false positive (e.g., a common name match), contact support for manual review. The beware list screening checks public government sanctions and cybersecurity threat databases.

#### "Identity records lost after server restart"
**Cause:** `DYNAMODB_ENABLED=false` — identity records only stored in memory
**Solution:** Set `DYNAMODB_ENABLED=true` and configure AWS credentials; identity records will persist in DynamoDB across restarts

---

## File Reference

### Backend Structure

```
backend/app/
├── api/
│   ├── auth.py              # Authentication + 2FA
│   ├── notifications.py      # Email notifications
│   ├── escrow.py            # Escrow management (identity verified)
│   ├── trading.py           # Trade execution (identity verified)
│   ├── backtest.py          # Backtesting + mock money
│   ├── identity.py          # Identity verification API
│   ├── device_ban.py        # Device ban management API
│   ├── dex.py               # DEX swaps (identity verified)
│   ├── paper_trading.py     # Paper trading (identity verified)
│   └── routes.py            # API route registration
├── agents/
│   ├── orchestrator.py      # Multi-agent coordination
│   └── trading_graph.py     # Agent definitions
├── backtesting/
│   ├── engine.py            # Backtesting engine + mock money
│   ├── mock_money.py        # Mock money simulation (BTC/ETH/SOL/USDT)
│   └── paper_trading.py     # Paper trading engine
├── risk/
│   ├── risk_engine.py       # Risk assessment
│   ├── risk_storage.py      # SQLite persistence
│   └── risk_metrics.py      # Metrics & calibration
├── rag/
│   └── knowledge_base.py    # Hybrid RAG
├── blockchain/
│   ├── ethereum.py          # ETH client
│   ├── solana.py            # SOL client
│   └── dex_executor.py      # DEX calls
└── core/
    ├── config.py            # Settings (Modal, mock money, identity)
    ├── llm.py               # LLM provider (incl. Modal GLM-5)
    ├── identity_verification.py  # GitHub/LinkedIn OAuth + crypto priority + DynamoDB sync
    ├── cloud_identity_store.py   # AWS DynamoDB cloud identity store (KMS-encrypted)
    ├── crypto_experience.py # Crypto experience assessment (GitHub/LinkedIn/Web)
    ├── cybersecurity_beware.py  # Cybersecurity beware list screening (OFAC/Interpol/EU/CryptoScamDB)
    ├── device_ban.py        # Device ban & abuse detection middleware
    └── auth.py               # Authentication middleware
```

### Frontend Structure

```
frontend/src/
├── App.jsx                   # Main app + routing
├── pages/
│   ├── AuthPage.jsx          # Login/Signup/2FA/Identity Verification
│   ├── BacktestPage.jsx      # Backtesting + Mock Money Display
│   ├── NotificationsPage.jsx # Notification preferences
│   ├── EscrowDashboard.jsx   # Escrow management
│   ├── TradingDashboard.jsx  # Main trading UI
│   └── ...
├── contexts/
│   ├── AuthContext.jsx       # Authentication state
│   ├── ThemeContext.jsx      # Auto day/night theme
│   ├── AppModeContext.jsx    # Paper/Live mode
│   ├── WalletContext.jsx     # Web3 wallet
│   └── DeviceContext.jsx     # Device fingerprinting + ban detection
└── components/
    └── WalletConnectButton.jsx
```

### Smart Contracts

```
contracts/
├── TradeEscrow.sol           # Fund escrow contract
├── MABCGovernance.sol        # Multi-agent governance
├── IdentityRegistry.sol      # Agent identity
└── test/
    └── TradeEscrow.t.sol     # Escrow tests
```

---

## Support

For issues or questions:
1. Check logs in backend console
2. Review `risk_metadata` in API responses
3. See `install.md` for detailed setup instructions
4. See `RISK_REFERENCE.md` for risk system details