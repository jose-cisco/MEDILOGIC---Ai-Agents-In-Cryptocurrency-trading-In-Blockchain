# AI Agent Blockchain Trading — Install, Implement & Deploy Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Local Development)](#quick-start-local-development)
3. [Configuration](#configuration)
4. [Architecture Overview](#architecture-overview)
5. [Frontend Pages & Features](#frontend-pages--features)
6. [LLM Provider Selection](#llm-provider-selection)
7. [Model Circles (Trading vs Backtesting)](#model-circles-trading-vs-backtesting)
8. [OpenRouter Integration](#openrouter-integration)
9. [x402 Payment Protocol](#x402-payment-protocol)
10. [Claw402 Provider (Pay-Per-LLM)](#claw402-provider-pay-per-llm)
11. [Docker Deployment](#docker-deployment)
12. [Free Public Deployment (Cloudflare Tunnel)](#free-public-deployment-cloudflare-tunnel)
13. [API Reference](#api-reference)
14. [Smart Contracts (Foundry)](#smart-contracts-foundry)
15. [Project Structure](#project-structure)
16. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | `brew install python@3.11` |
| Node.js | 20+ | `brew install node` |
| Git | Latest | `brew install git` |
| Cloudflare Tunnel | Latest | `brew install cloudflared` |
| Foundry (for contracts) | Latest | `curl -L https://foundry.paradigm.xyz \| bash` |

---

## Quick Start (Local Development)

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd "AI Agent In Blockchain Trading"
```

### 2. Run the Simplified Startup Script

We provide an automated start script that will check prerequisites, set up the backend virtual environment, install dependencies, and start both the backend FastAPI server and the frontend Vite server.

```bash
# Make the script executable
chmod +x start.sh

# Run the full stack
./start.sh
```

Alternatively, you can choose to deploy the components manually:

### 3. Manual Backend Setup (Alternative)

```bash
cd backend

# Create virtual environment with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env from example
cp .env.example .env
# Edit .env with your API keys (see Configuration section)

# Run the backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Manual Frontend Setup (Alternative)

```bash
cd frontend

# Install dependencies
npm install

# Run the dev server
npm run dev
```

### 5. Access the Application

Once running, the app will be available at:
- **Frontend**: http://localhost:5173 (or http://localhost:3000 depending on Vite config)
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 4. VS Code Python Interpreter

Select the correct Python interpreter in VS Code:
1. Press `Cmd+Shift+P` → "Python: Select Interpreter"
2. Choose `backend/.venv/bin/python3`

---

## Configuration

All configuration is done via environment variables in `backend/.env`:

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TRADING_MODE` | `paper` | `paper` for simulation, `live` for real trading |
| `LIVE_TRADING_ENABLED` | `false` | Must be `true` for live mode |
| `LLM_PROVIDER` | `ollama` | `ollama`, `openrouter`, `claw402`, or `ionet` |

### LLM Provider Keys

| Variable | Description |
|----------|-------------|
| `OLLAMA_BASE_URL` | Local Ollama endpoint (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | Ollama model name (default: `glm-5`) |
| `OPENROUTER_API_KEY` | OpenRouter API key for reasoning models |
| `IONET_API_KEY` | io.net API key for GLM-5.1 Reasoning |
| `XAI_API_KEY` | x.ai API key for Grok 4.20 Reasoning |

### OpenRouter Configuration

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key (required for reasoning models) |
| `OPENROUTER_BASE_URL` | OpenRouter API URL (default: `https://openrouter.ai/api/v1`) |

### Claw402 Configuration (Pay-Per-LLM via USDC on Base)

| Variable | Description |
|----------|-------------|
| `CLAW402_BASE_URL` | Claw402 API endpoint |
| `CLAW402_MODEL` | Default Claw402 model (e.g., `claude-opus-4-5`) |
| `CLAW402_WALLET_PRIVATE_KEY` | Hot wallet private key for USDC payments |
| `CLAW402_USDC_ADDRESS` | USDC contract address on Base |

### Blockchain (Optional)

| Variable | Description |
|----------|-------------|
| `ETHEREUM_RPC_URL` | Ethereum RPC endpoint (Alchemy/Infura) |
| `SOLANA_RPC_URL` | Solana RPC endpoint |
| `ETHERSCAN_API_KEY` | Etherscan API key for contract source fetching |

### x402 Payment Protocol

| Variable | Default | Description |
|----------|---------|-------------|
| `X402_ENABLED` | `false` | Enable pay-per-use API access |
| `X402_TESTNET` | `true` | Use testnet for payments |
| `X402_RECIPIENT_ADDRESS` | — | Wallet to receive USDC payments |
| `X402_USDC_ADDRESS` | — | USDC contract address |
| `X402_CHAIN_ID` | `8453` | Chain ID (Base mainnet) |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite)                    │
│                    http://localhost:5173                        │
│                                                                 │
│  Pages: Dashboard | Config | Debate Arena | Backtest |          │
│         Security | Governance | Knowledge | Payments |          │
│         Strategy | FAQ | Agent Status                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Vite Proxy │  /api → localhost:8000
                    └──────┬──────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend (Port 8000)                    │
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  │ 🧠 Planner Agent    │  │ 🛡️ Verifier Agent   │  │ ⚖️ Controller Agent  │
│  │                     │  │                     │  │                     │
│  │ • Market analysis   │  │ • Security checks   │  │ • PoT consensus      │
│  │ • RAG context       │  │ • Risk validation   │  │ • Final approval     │
│  │ • Trade decision    │  │ • Vulnerability     │  │ • Execution params   │
│  │ • Risk assessment   │  │   detection         │  │ • Reject/Execute     │
│  │ • Action proposal   │  │ • Ensemble analysis │  │ • Conflict resolution│
│  └──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘
│             │                        │                        │          │
│             └────────────────────────┼────────────────────────┘          │
│                                      │                                    │
│                          ┌───────────▼───────────┐                        │
│                          │  LangGraph Orchestrator │                        │
│                          │  (Proof-of-Thought)    │                        │
│                          └───────────┬───────────┘                        │
│                                      │                                    │
│                   ┌──────────────────┼──────────────────┐                 │
│                   │                  │                  │                  │
│            ┌──────▼──────┐    ┌──────▼──────┐    ┌─────▼──────┐          │
│            │ Hybrid RAG  │    │ Governance  │    │ x402       │          │
│            │ (ChromaDB + │    │ Agent       │    │ Payment    │          │
│            │  BM25 + RRF)│    │ Checks      │    │ Protocol   │          │
│            └─────────────┘    └─────────────┘    └────────────┘          │
│                                                                          │
│            ┌──────▼──────┐    ┌──────▼──────┐    ┌─────▼──────┐          │
│            │ Monitor     │    │ Adjuster    │    │ EAAC        │          │
│            │ Agent       │    │ Agent       │    │ Attestation │          │
│            └─────────────┘    └─────────────┘    └────────────┘          │
│                                                                           │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐      │
│  │ Ethereum     │ │ Solana       │ │ Backtesting     │      │
│  │ Client       │ │ Client       │ │ Engine (Safe)   │      │
│  └─────────────┘ └─────────────┘ └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Complete 6-Stage Agent Lifecycle

The system follows a complete "Perceive → Act → Monitor → Adjust" lifecycle:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COMPLETE AGENT LIFECYCLE                          │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                     ┌─────────────────┐
                     │  1. PERCEIVE    │  Market Data + Hybrid RAG Context
                     └────────┬────────┘
                              │
                              ▼
          ┌────────────────────────────────────────┐
          │         2. 🧠 PLANNER AGENT              │
          │  • Perceives market conditions         │
          │  • Plans optimal trading strategy      │
          │  • Reasons through indicators          │
          │  • Proposes trade decision            │
          └───────────────────┬────────────────────┘
                              │
                              ▼
          ┌────────────────────────────────────────┐
          │         3. 🛡️ VERIFIER AGENT            │
          │  • Independent security review          │
          │  • Ensemble vulnerability check         │
          │  • Risk score adjustment                │
          │  • Approve/Reject with reasons         │
          └───────────────────┬────────────────────┘
                              │
                              ▼
          ┌────────────────────────────────────────┐
          │         4. ⚖️ CONTROLLER AGENT          │
          │  • Proof-of-Thought consensus           │
          │  • Weighs planner vs verifier           │
          │  • Final go/no-go decision              │
          │  • Sets execution parameters            │
          └───────────────────┬────────────────────┘
                              │
                     ┌────────┴────────┐
                     ▼                 ▼
              ┌──────────┐      ┌──────────┐
              │ EXECUTE  │      │ REJECT   │
              │  Trade   │      │  Trade   │
              └─────┬────┘      └──────────┘
                    │
                    ▼
          ┌────────────────────────────────────────┐
          │         5. 🔭 MONITOR AGENT              │
          │  • Observability strategy               │
          │  • Trailing stop-loss logic             │
          │  • Volume-divergence alerts             │
          │  • Position health checks               │
          └───────────────────┬────────────────────┘
                              │
                              ▼
          ┌────────────────────────────────────────┐
          │         6. ⚡ ADJUSTER AGENT             │
          │  • Reactive self-correction            │
          │  • Early exit conditions               │
          │  • Parameter shifts (tighten SL)       │
          │  • Risk mitigation actions             │
          └────────────────────────────────────────┘
```

### Agent Roles and Responsibilities

| Agent | Role | Key Responsibilities | Outputs |
|-------|------|---------------------|---------|
| 🧠 **Planner** | Market Analyst & Strategist | Analyzes market data, retrieves RAG context, evaluates trading conditions, proposes actions | `{action, amount, confidence, risk_score, market_regime, indicators_used, rag_sources_cited}` |
| 🛡️ **Verifier** | Security & Risk Validator | Independent security analysis, vulnerability detection (Ensemble LLM), risk validation, cross-checks planner decisions | `{approved, adjusted_risk_score, vulnerabilities_found, ensemble_scores, rag_cross_validation}` |
| ⚖️ **Controller** | Consensus & Execution Manager | Proof-of-Thought consensus between planner and verifier, resolves conflicts, generates execution parameters | `{approved, final_action, final_amount, execution_parameters, pot_confidence}` |
| 🔭 **Monitor** | Position Guardian | Observability strategy, trailing stop-loss, volume divergence alerts, position health checks | `{monitoring_strategy, trailing_stop_pct, alert_thresholds, health_check_interval}` |
| ⚡ **Adjuster** | Reactive Self-Correction | Early exit conditions, parameter shifts, risk mitigation, auto-tuning | `{adjustment_type, new_parameters, trigger_conditions, confidence_adjustment}` |

---

## Frontend Pages & Features

The frontend provides a complete professional trading interface with the following pages:

### Navigation Menu

```
Dashboard | Risk Dashboard | Escrow & Revenue | Notifications | Strategy | Debate Arena | Config | Security | Governance | Knowledge | Payments | FAQ
```

### 1. Trading Dashboard (`/`)

**Features:**
- **Paper/Live Mode Toggle**: Switch between simulation and real trading with visual "High-Stakes" UI (red pulsing background for live mode)
- **Dual-Model Selection**: Choose model_1 and model_2 for ensemble trading
- **AI Chain-of-Thought**: Structured reasoning display (Market State → RAG Integration → Risk Check → Decision)
- **Account Equity Curve**: Real-time performance visualization
- **Positions Snapshot**: Active positions table
- **x402 Wallet Simulation**: Sign & Retry flow for payment authorization

### 2. Config Page (`/config`)

**Features:**
- **AI Models Panel**: View active models with provider badges (OpenRouter, Claw402)
- **Exchanges Hub**: Manage API connections for Binance, Bybit, etc.
- **Current Traders**: List of active bot instances with lifecycle controls (Start/Stop/Edit)

### 3. Debate Arena (`/debate-arena`)

**Features:**
- **Proof-of-Thought Battle**: Live visualization of Planner vs Verifier debate
- **6-Stage Lifecycle Display**: Perceive → Plan → Verify → Act → Monitor → Adjust
- **Consensus Meter**: Visual indicator of agreement level
- **Argument Cards**: Detailed reasoning from each agent

### 4. Backtest Page (`/backtest`)

**Features:**
- **Zero-Cost Simulation Mode**: Badge confirming local-only execution
- **Local-Only Models**: Restricted to Ollama models (GLM-5, GLM-5.1, MiniMax M2.7)
- **Strategy Selection**: Momentum, Mean Reversion, Breakout templates
- **Historical Performance Charts**: PnL, drawdown, win rate visualization

> ⚠️ **Backtesting is FREE**: Only local Ollama models are allowed. Cloud providers (OpenRouter, Claw402) are blocked during backtesting to prevent any costs.

### 5. Security Hub (`/security`)

**Features:**
- **Contract Scanner**: Paste Solidity source code for vulnerability analysis
- **Contract Address Scan**: Fetch verified source from Etherscan (Ethereum, BSC, Polygon, Arbitrum, Base, Optimism)
- **Ensemble Consensus Display**: Shows which agent (🧠 GLM, 🛡️ Grok) verified each vulnerability
- **Scan History**: Historical vulnerability reports

### 6. Governance Page (`/governance`)

**Features:**
- **DAO Dashboard**: Interactive governance interface
- **Active Proposals**: View and vote on policy changes
- **Vote Casting**: For/Against/Abstain buttons
- **Proposal Creation**: Broadcast new proposals to the network
- **Activity Logs**: Real-time feed of "Proof-of-Thought" consensus events

### 7. Knowledge Base (`/knowledge`)

**Features:**
- **Tabbed Ingestion Panel**:
  - Tab 1: JSON/Text input
  - Tab 2: Drag-and-drop file upload (PDF/TXT)
- **Collection Stats**: Document count, chunk count, embedding model info
- **Hybrid Search Tester**: Test Semantic + BM25 + RRF retrieval

### 8. Payments Page (`/payments`)

**Features:**
- **Traditional vs x402 Comparison**: Side-by-side flow comparison
- **Interactive 5-Step Timeline**: Click through the x402 payment flow
- **Live 402 Fetch**: Button to fetch actual payment requirements
- **Payment Verifier**: Test tx_hash + chain verification
- **Claw402 Provider Panel**: Live catalogue of 15+ models with pricing
- **OpenRouter Provider Panel**: Dynamic model discovery with live pricing

### 9. Strategy Page (`/strategy`)

**Features:**
- **Strategy Templates**: Momentum Scalper, Mean Reversion, Breakout
- **Rule Builder**: Set entry/exit conditions (e.g., RSI < 30)
- **Global Parameters**: Position sizing, slippage tolerance

### 10. FAQ Page (`/faq`)

**Features:**
- **Interactive Cards**: Click to expand explanations
- **Topics**:
  - Proof-of-Thought (PoT) Consensus
  - x402 Payment Protocol
  - DAO Governance
  - Hybrid RAG System
  - Zero-Cost Backtesting

### 11. Agent Status (`/status`)

**Features:**
- **Agent Health**: Status of all agents (Planner, Verifier, Controller, Monitor, Adjuster)
- **System Metrics**: Memory, CPU, connection status
- **LLM Provider Status**: Which providers are configured and available

### 12. Authentication (`/login`)

**Features:**
- **Email Signup**: Register with Gmail, Hotmail, or any email provider
- **Two-Factor Authentication (2FA)**: Optional SMS verification via phone number (E.164 format)
- **Email Verification**: Confirm email address before accessing trading features
- **Password Requirements**: 8+ chars, uppercase, lowercase, number
- **Password Reset**: Forgot password flow with email token
- **Newsletter Subscription**: Opt-in for trading updates during signup
- **Automatic Theme Detection**: Day/night mode based on user timezone

### 13. Notifications (`/notifications`)

**Features:**
- **Notification Preferences**: Toggle trading updates, profit alerts, security alerts, system updates
- **Daily Summary**: Opt-in for daily trading performance emails
- **Weekly Report**: Weekly performance summary sent to Gmail/Hotmail
- **Account Status Email**: Request email showing verification status, 2FA status, last login
- **Notification History**: View past notifications with read/unread status
- **Quick Actions**: Send account status, send daily summary, mark all as read

### 14. Escrow & Revenue (`/escrow`)

**Features:**
- **Fund Deposits**: Deposit ETH to escrow for trading
- **Balance Display**: View current escrow balance
- **Transaction History**: View all deposits, trades, and withdrawals
- **Owner Withdrawals**: Contract owner can withdraw revenue share
- **Smart Contract Integration**: Secure fund management via TradeEscrow.sol
- **Real-time Updates**: Live balance updates after transactions

---

## LLM Provider Selection

### Using Ollama (Free, Local — Backtesting Only)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull glm-5
ollama pull glm-5.1
ollama pull minimax-m2.7

# Set in .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=glm-5
```

> ⚠️ **Ollama is ONLY for backtesting** — It cannot be used for live trading.

### Using OpenRouter (Reasoning Models — Trading)

OpenRouter provides access to high-reasoning models with enforced `reasoning: True` parameter:

```bash
# Set in .env
OPENROUTER_API_KEY=your_openrouter_api_key
LLM_PROVIDER=openrouter
```

**Available Models via OpenRouter:**

| Model ID | Provider | Reasoning Enforced | Best For |
|----------|----------|-------------------|----------|
| `z-ai/glm-5.1` | GLM | ✅ Yes | Planner & Controller |
| `x-ai/grok-4.20-0309-reasoning` | xAI | ✅ Yes | Verifier |
| `xiaomi/mimo-v2-pro` | Xiaomi | ✅ Yes | Reasoning tasks |
| `alibaba/qwen-3.6-plus` | Alibaba Cloud | ✅ Yes | Reasoning tasks |

### Using Claw402 (Pay-Per-LLM via USDC)

No accounts. No API keys. One wallet, every model:

```bash
# Set in .env
CLAW402_WALLET_PRIVATE_KEY=0x<your_hot_wallet_key>
CLAW402_MODEL=claude-opus-4-5
LLM_PROVIDER=claw402
```

**Claw402 Models (15+ models, Base network):**
- GPT-5.4, Claude Opus 4.5, DeepSeek R2
- Qwen, Grok, Gemini, Kimi K2

---

## Model Circles (Trading vs Backtesting)

### Trading Circle (Cloud Providers)

**Allowed models:**
- `z-ai/glm-5.1` (OpenRouter, reasoning enforced)
- `x-ai/grok-4.20-0309-reasoning` (OpenRouter, reasoning enforced)
- `xiaomi/mimo-v2-pro` (OpenRouter, reasoning enforced)
- `alibaba/qwen-3.6-plus` (OpenRouter, reasoning enforced)
- Claw402 models (pay-per-use via USDC)

> ⚠️ **Only these 4 OpenRouter models are supported for trading** — Other models are blocked.

### Backtesting Circle (Local Ollama)

**Allowed models:**
- `glm-5.1` (Ollama)

> ⚠️ **Only GLM-5.1 is available for backtesting** — Cloud reasoning models are blocked to prevent costs.

---

## OpenRouter Integration

### Reasoning Parameter Enforcement

The system automatically enforces the `reasoning: True` parameter for specific models:

```python
# backend/app/core/llm.py
REASONING_MODELS = {
    "z-ai/glm-5.1": True,
    "z-ai/glm-5": True,
    "x-ai/grok-4.20-multi-agent": True,
}
```

When these models are selected, the LLM factory automatically includes the reasoning parameter in every request.

### Dynamic Provider Discovery

The backend fetches live pricing from OpenRouter API:

```bash
# Endpoint
GET /api/v1/payments/providers/openrouter

# Returns
{
  "models": [
    {
      "id": "z-ai/glm-5.1",
      "name": "GLM-5.1",
      "pricing": {
        "prompt": "0.55",
        "completion": "0.55"
      },
      "context_length": 128000,
      "reasoning_enforced": true
    },
    ...
  ]
}
```

### Zero-Cost Backtesting Safety

The LLM factory includes a strict safety check:

```python
# backend/app/core/llm.py
from contextvars import ContextVar

is_backtest_mode: ContextVar[bool] = ContextVar("is_backtest_mode", default=False)

def _get_cloud_llm(model_id: str, ...):
    if is_backtest_mode.get():
        raise RuntimeError(
            f"Cloud model '{model_id}' blocked in backtest mode. "
            "Backtesting is restricted to local Ollama models only."
        )
```

---

## x402 Payment Protocol

### How x402 Works

**Traditional flow:** register account → buy credits → get API key → manage quota → rotate keys

**x402 flow:** Request → 402 (here's the price) → wallet signs USDC → retry → done

### Implementation Layers

| Layer | File | What it does |
|-------|------|--------------|
| **Config** | `config.py` | All `X402_*` env vars — pricing, wallet, chain, testnet flag |
| **Core Service** | `x402.py` | `build_402_response()` → `verify_payment_header()` → `_verify_onchain_payment()` |
| **Middleware** | `auth.py` | Intercepts every request → checks `X-Payment` header → returns 402 or passes through |
| **API Integration** | `trading.py`, `knowledge.py`, `governance.py` | Attach `x402_metadata` receipt to all responses |
| **Mainnet verification** | `x402.py` | Reads real USDC `Transfer` event logs from blockchain |

### 5-Step x402 Flow

1. **Initial Request**: User sends unauthenticated request
2. **402 Response**: Server responds with price, payment address, expiry
3. **Wallet Signature**: User signs USDC transfer
4. **Retry with X-Payment Header**: Include signed payment header
5. **Verification**: Server verifies on-chain transaction

### Frontend Simulation

The Trading Dashboard includes a simulated x402 wallet flow:
- When payment is required, UI prompts for signature
- Click "Sign & Retry" to simulate wallet interaction
- Generates mock transaction hash
- Automatically retries trade with verified payment

---

## Claw402 Provider (Pay-Per-LLM)

### Overview

**No accounts. No API keys. No prepaid credits. One wallet, every model.**

Claw402 runs on Base network and provides access to 15+ models from major providers.

### Supported Models

| Provider | Models |
|----------|--------|
| OpenAI | GPT-5.4 |
| Anthropic | Claude Opus 4.5 |
| DeepSeek | DeepSeek R2 |
| Alibaba | Qwen |
| xAI | Grok |
| Google | Gemini |
| Moonshot | Kimi K2 |

### Backend Transport

The `claw402_transport.py` module handles automatic payment:

```python
# backend/app/core/claw402_transport.py
class Claw402Transport(httpx.AsyncBaseTransport):
    """
    Custom httpx transport that:
    1. Intercepts 402 responses
    2. Submits real USDC on Base via web3.py
    3. Retries with X-Payment header
    
    Includes $1.00 safety ceiling per request
    """
```

---

## Docker Deployment

### Build and Run with Docker Compose

```bash
# From project root
docker-compose up --build

# Services:
# - Frontend: http://localhost:3000
# - Backend:  http://localhost:8000 (via gateway on 8080)
# - Gateway:   http://localhost:8080
# - Ollama:    internal only
```

### Environment Variables for Docker

Create a `.env` file in the project root:

```env
TRADING_MODE=paper
LIVE_TRADING_ENABLED=false
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=glm-5
```

---

## Free Public Deployment (Cloudflare Tunnel)

For exposing your local development server to the internet without cost:

### 1. Start Backend and Frontend

```bash
# Terminal 1: Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev -- --host 0.0.0.0

# Terminal 3: Cloudflare Tunnel (free, no account needed)
cloudflared tunnel --url http://localhost:5173
```

### 2. Get Your Public URL

Cloudflare will output a URL like:
```
https://your-unique-name.trycloudflare.com
```

This URL is temporary and changes on restart.

---

## API Reference

### Trading

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/trading/execute` | POST | Execute a trade (paper mode) |
| `/api/v1/trading/execute-live` | POST | Execute a trade (live mode) |
| `/api/v1/trading/analyze` | POST | Get market analysis for a token pair |

**Trade Request Body:**
```json
{
  "prompt": "Buy ETH when RSI is oversold",
  "chain": "ethereum",
  "token_pair": "ETH/USDT",
  "max_position_usd": 1000,
  "agent_id": "default-trader",
  "model_1": "z-ai/glm-5.1",
  "model_2": "x-ai/grok-4.20-multi-agent"
}
```

### Backtesting

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/backtest/run` | POST | Run LLM-driven backtest (Ollama only) |
| `/api/v1/backtest/run-rules` | POST | Run rules-based backtest |
| `/api/v1/backtest/strategies` | GET | List available strategies |

### Knowledge (RAG)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/knowledge/stats` | GET | Get collection statistics |
| `/api/v1/knowledge/add` | POST | Add text/JSON documents |
| `/api/v1/knowledge/upload` | POST | Upload PDF/TXT files (multipart) |
| `/api/v1/knowledge/hybrid-query` | POST | Hybrid semantic + BM25 search |

### Security (Vulnerability Scanning)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/vulnerability/scan` | POST | Scan Solidity source code |
| `/api/v1/vulnerability/scan/address` | POST | Scan by contract address (Etherscan) |
| `/api/v1/vulnerability/history` | GET | Get scan history |

### Governance

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/governance/status` | GET | Get governance status |
| `/api/v1/governance/logs` | GET | Get activity logs |
| `/api/v1/governance/propose` | POST | Create new proposal |
| `/api/v1/governance/vote` | POST | Cast vote on proposal |

### Payments

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/payments/status` | GET | Get x402 status |
| `/api/v1/payments/verify` | POST | Verify x402 payment |
| `/api/v1/payments/requirement/{resource}` | GET | Get payment requirement |
| `/api/v1/payments/providers/claw402` | GET | Get Claw402 model catalogue |
| `/api/v1/payments/providers/openrouter` | GET | Get OpenRouter models with live pricing |

### Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/status/agents` | GET | Agent status |
| `/api/v1/status/blockchain` | GET | Blockchain connection status |
| `/api/v1/status/system` | GET | System info and configuration |
| `/api/v1/status/llm-providers` | GET | Available LLM models |

---

## Smart Contracts (Foundry)

```bash
cd contracts

# Install Foundry
curl -L https://foundry.paradigm.com | bash

# Build contracts
forge build

# Run tests
forge test

# Deploy (requires RPC URL)
forge create --rpc-url $ETHEREUM_RPC_URL --private-key $PRIVATE_KEY contracts/MABCGovernance.sol
```

### Available Contracts

| Contract | Purpose |
|----------|---------|
| `MABCGovernance.sol` | Multi-Agent Blockchain Coordination voting |
| `IdentityRegistry.sol` | Agent identity management |
| `PolicyEnforcer.sol` | Governance policy enforcement |
| `VerificationAgent.sol` | Verification agent contract |
| `DataRecorder.sol` | On-chain data recording |
| `ActivityLogger.sol` | Activity logging |
| `BillRegistry.sol` | Payment billing registry |
| `DisputeResolver.sol` | Dispute resolution |
| `IncentiveManagement.sol` | Incentive management |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── orchestrator.py      # Trading orchestrator
│   │   │   └── trading_graph.py     # LangGraph multi-agent pipeline (6 stages)
│   │   ├── api/
│   │   │   ├── trading.py           # Trade execution endpoints
│   │   │   ├── backtest.py          # Backtesting endpoints (zero-cost enforced)
│   │   │   ├── status.py            # System status & LLM providers
│   │   │   ├── governance.py        # Governance checks
│   │   │   ├── knowledge.py         # RAG knowledge base + file upload
│   │   │   ├── payments.py          # x402 payment protocol + provider discovery
│   │   │   ├── vuln_scan.py         # Vulnerability scanning
│   │   │   ├── mabc.py              # Multi-Agent Blockchain Coordination
│   │   │   ├── eaac.py              # Ethereum AI Agent Coordination
│   │   │   └── routes.py            # API route registration
│   │   ├── backtesting/
│   │   │   ├── engine.py            # Backtesting engine
│   │   │   └── engine_safe.py       # Safe backtesting wrapper
│   │   ├── blockchain/
│   │   │   ├── dex_executor.py      # DEX execution
│   │   │   ├── ethereum.py          # Ethereum client
│   │   │   └── solana.py            # Solana client
│   │   ├── core/
│   │   │   ├── config.py            # Settings & validation
│   │   │   ├── llm.py               # LLM provider routing + reasoning enforcement
│   │   │   ├── auth.py              # API key middleware + x402
│   │   │   ├── x402.py              # x402 payment service
│   │   │   ├── claw402_transport.py # Claw402 auto-pay transport
│   │   │   ├── eaac.py              # EAAC attestation
│   │   │   └── vulnerability_scanner.py  # Ensemble LLM scanner
│   │   ├── governance/
│   │   │   ├── agent_governance.py  # Multi-agent governance
│   │   │   └── mabc_voting.py       # MABC voting logic
│   │   ├── rag/
│   │   │   └── knowledge_base.py    # Hybrid RAG (semantic + BM25 + RRF)
│   │   └── schemas/
│   │       └── models.py            # Pydantic models
│   ├── .env                          # Environment config
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── TradingDashboard.jsx  # Main trading UI + Paper/Live toggle
│   │   │   ├── BacktestPage.jsx       # Backtesting UI (zero-cost)
│   │   │   ├── AgentStatus.jsx        # Agent status UI
│   │   │   ├── ConfigPage.jsx         # Config & trader management
│   │   │   ├── DebateArenaPage.jsx    # Proof-of-Thought visualization
│   │   │   ├── SecurityPage.jsx       # Vulnerability scanner
│   │   │   ├── GovernancePage.jsx     # DAO dashboard
│   │   │   ├── KnowledgePage.jsx      # RAG manager + file upload
│   │   │   ├── PaymentsPage.jsx       # x402 + provider panels
│   │   │   ├── StrategyPage.jsx       # Strategy rule builder
│   │   │   └── FAQPage.jsx            # Educational FAQ
│   │   ├── contexts/
│   │   │   └── ThemeContext.jsx       # Theme context
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── vite.config.js
│   └── Dockerfile
├── contracts/                         # Solidity smart contracts
├── gateway/
│   └── nginx.conf                    # Reverse proxy config
├── docker-compose.yml
├── start.sh                           # Startup script
├── startup_check.sh                   # Startup verification
└── install.md                         # This file
```

---

## Troubleshooting

### Python Version Issues

If you see `pydantic-core` build failures, ensure you're using Python 3.11:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.14 is **not supported** due to PyO3 compatibility issues.

### FastAPI Import Error

If `import fastapi could not be resolved`:
1. Activate the virtual environment: `source backend/.venv/bin/activate`
2. In VS Code: `Cmd+Shift+P` → "Python: Select Interpreter" → choose `backend/.venv/bin/python3`

### Ollama Connection Refused

```bash
# Start Ollama
ollama serve

# Pull the models
ollama pull glm-5:cloud 
ollama pull glm-5.1:cloud 
ollama pull minimax-m2.7:cloud 
```

### Cloudflare Tunnel Not Working

```bash
# Install cloudflared
brew install cloudflared

# Start tunnel
cloudflared tunnel --url http://localhost:5173
```

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 5173
lsof -ti:5173 | xargs kill -9
```

### Governance Page Syntax Error

If you see `Invalid character. ':' expected` in GovernancePage.jsx:
- Ensure there are no Python-style `#` comments (use `//` instead)
- Check for proper JSX syntax

---

## Summary of Key Features

### Frontend-Backend Integration

| Page | Route | Backend Endpoints |
|------|-------|-------------------|
| **Trading Dashboard** | `/` | `/trading/execute`, `/trading/analyze` |
| **Config** | `/config` | `/status/agents`, `/traders` |
| **Debate Arena** | `/debate-arena` | `/eaac/consensus` |
| **Backtest** | `/backtest` | `/backtest/run`, `/backtest/run-rules` |
| **Security** | `/security` | `/vulnerability/scan`, `/vulnerability/scan/address` |
| **Governance** | `/governance` | `/governance/status`, `/governance/vote`, `/governance/propose` |
| **Knowledge** | `/knowledge` | `/knowledge/stats`, `/knowledge/add`, `/knowledge/upload` |
| **Payments** | `/payments` | `/payments/status`, `/payments/providers/claw402`, `/payments/providers/openrouter` |
| **Strategy** | `/strategy` | `/backtest/strategies` |
| **FAQ** | `/faq` | Static content |
| **Agent Status** | `/status` | `/status/agents`, `/status/system` |

### Model Restrictions

| Mode | Allowed Models | Provider |
|------|----------------|----------|
| **Trading (Cloud)** | `z-ai/glm-5.1`, `x-ai/grok-4.20-0309-reasoning`, `xiaomi/mimo-v2-pro`, `alibaba/qwen-3.6-plus` | OpenRouter |
| **Trading (Pay-Per-Use)** | 15+ models (GPT-5.4, Claude Opus, DeepSeek R2, etc.) | Claw402 |
| **Backtesting (Local)** | `glm-5.1` | Ollama |

### Zero-Cost Guarantees

- **Backtesting is always free** — Cloud providers are blocked at the LLM factory level
- **x402 exempted for backtesting** — No payment prompts during simulations
- **Reasoning parameters enforced** — GLM-5.1, Grok 4.20 0309, MiMo-V2-Pro, and Qwen 3.6 Plus always use `reasoning: True`

---

## LLM Auto-Tune System

The system includes an **LLM Auto-Tune System** that automatically configures optimal parameters for each agent based on task characteristics.

### What It Detects Automatically:

| Factor | Detection Method | Effect |
|--------|-----------------|--------|
| **Input Complexity** | Text length, technical terms, context size | Adjusts max_tokens, temperature |
| **Risk Level** | Position size, leverage, volatility, live mode | Tightens parameters for high risk |
| **Task Type** | Agent role (planner, verifier, controller) | Applies role-specific profiles |
| **Model Characteristics** | Model-specific optimizations | Adjusts multipliers per model |

### What It Configures:

| Parameter | Range | Effect |
|-----------|-------|--------|
| `temperature` | 0.0 - 1.0 | Lower = more deterministic, Higher = more creative |
| `top_p` | 0.1 - 1.0 | Nucleus sampling threshold |
| `max_tokens` | 256 - 8192 | Output length limit |
| `frequency_penalty` | 0.0 - 1.0 | Discourages repetition |
| `presence_penalty` | 0.0 - 1.0 | Encourages topic diversity |
| `reasoning` | True/False | Enables extended reasoning mode |

### Pre-Optimized Task Profiles:

| Agent | Task Type | Temperature | Top_P | Max_Tokens | Reasoning |
|-------|-----------|-------------|-------|------------|-----------|
| Planner | Market Analysis | 0.2-0.35 | 0.85-0.92 | 2048-6144 | ✅ ON |
| Verifier | Security Audit | 0.0-0.1 | 0.80-0.85 | 1536-3072 | ✅ ON |
| Controller | Consensus | 0.0-0.05 | 0.75-0.82 | 1024-2048 | ✅ ON |
| Monitor | Risk Assessment | 0.0-0.1 | 0.80-0.85 | 1024-2048 | ✅ ON |
| Adjuster | Trade Decision | 0.1-0.2 | 0.82-0.88 | 1536-3072 | ✅ ON |

### Model-Specific Optimizations:

| Model | Temp Multiplier | Top_P Multiplier | Best For |
|-------|----------------|------------------|----------|
| GLM-5.1 | 0.9x | 1.0x | Market analysis, complex reasoning |
| Grok 4.20 0309 | 0.85x | 0.95x | Security audits, verification |
| MiMo-V2-Pro | 0.9x | 1.0x | General reasoning tasks |
| Qwen 3.6 Plus | 0.95x | 1.0x | Balanced reasoning tasks |

### Usage Examples:

```python
# Method 1: Use auto-tuned getters (Recommended)
from app.core.llm import get_auto_tuned_llm

llm = get_auto_tuned_llm(
    agent_role="planner",
    model_id="glm-5.1",
    input_text="Analyze ETH/USDT market conditions...",
    market_data={"position_size_usd": 5000, "leverage": 2.0},
    is_live=True,
)

# Method 2: Role-specific auto-tuned getters
from app.core.llm import (
    get_auto_tuned_planner_llm,
    get_auto_tuned_verifier_llm,
    get_auto_tuned_controller_llm,
)

# Planner with auto-tuned params
planner = get_auto_tuned_planner_llm(
    model_id="glm-5.1",
    input_text="Complex market analysis text...",
    is_live=True,
)

# Verifier with auto-tuned params (lower temperature for precision)
verifier = get_auto_tuned_verifier_llm(
    model_id="grok-4.20-0309",
    input_text="Security audit text...",
    is_live=True,
)

# Controller with auto-tuned params (very low temperature for consensus)
controller = get_auto_tuned_controller_llm(
    model_id="glm-5.1",
    is_live=True,
)
```

### Risk-Based Adjustments:

| Risk Level | Temperature Delta | Top_P Delta | When Applied |
|------------|------------------|-------------|--------------|
| LOW | +0.05 | +0.02 | Small positions, low volatility |
| MEDIUM | 0.0 | 0.0 | Normal conditions |
| HIGH | -0.1 | -0.05 | Large positions, high volatility, live mode |

### Automatic Complexity Detection:

The system analyzes input text for:
- **Text length**: >500 chars adds 1 point, >2000 adds 2 points
- **Word count**: >150 words adds 1 point, >500 adds 2 points
- **Technical terms**: >2 terms adds 1 point, >5 adds 2 points
- **Context size**: >5 RAG chunks adds 1 point

Score ≥5 → COMPLEX, Score ≥2 → MODERATE, Score <2 → SIMPLE

---

## Quick Reference Commands

```bash
# Start backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# Start frontend
cd frontend && npm run dev

# Run backtests (zero-cost, local only)
curl -X POST http://localhost:8000/api/v1/backtest/run -d '{"model": "glm-5.1"}'

# Scan a contract by address (Ethereum)
curl -X POST http://localhost:8000/api/v1/vulnerability/scan/address \
  -d '{"address": "0x...", "chain": "ethereum"}'

# Upload documents to knowledge base
curl -X POST http://localhost:8000/api/v1/knowledge/upload \
  -F "files=@document.pdf" -F "source_label=my-docs"

# Get OpenRouter live pricing
curl http://localhost:8000/api/v1/payments/providers/openrouter