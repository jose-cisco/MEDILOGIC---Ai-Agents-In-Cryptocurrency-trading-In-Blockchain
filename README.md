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
7. [Notification System](#notification-system)
8. [Escrow & Revenue System](#escrow--revenue-system)
9. [API Reference](#api-reference)
10. [Frontend Components](#frontend-components)
11. [Configuration](#configuration)
12. [Installation Guide](#installation-guide)
13. [Safety Mechanisms](#safety-mechanisms)
14. [Troubleshooting](#troubleshooting)

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
│  │  │  GLM-5.1   │  │ Grok 4.20 0309 │  │MiMo-V2-Pro │  │Qwen 3.6 Plus │   │ │
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
| **Verifier** | Security audit & risk adjustment | Grok 4.20 0309 | approved, adjusted_risk_score, vulnerabilities |
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
| `grok-4.20-0309` | Grok 4.20 0309 (Reasoning) v1 | ✅ ON | ✅ **YES** |
| `grok-4.20-0309-v2` | Grok 4.20 0309 (Reasoning) v2 | ✅ ON | ✅ **YES** |
| `mimo-v2-pro` | MiMo-V2-Pro (Reasoning) | ✅ ON | ❌ NO |
| `qwen-3.6-plus` | Qwen 3.6 Plus (Reasoning) | ✅ ON | ❌ NO |

### Image Input Support

**⚠️ IMPORTANT: Image input is ONLY supported by Grok 4.20 0309 (v1 and v2).**

If you provide an `image_url` with other models (glm-5.1, mimo-v2-pro, qwen-3.6-plus), the image will be **IGNORED** and only text will be processed.

#### Using Image Input

To use image input with Grok 4.20 0309 models, include the `image_url` parameter in your trade request:

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
| Grok 4.20 0309 v1 | 0.85x | 0.95x | Excellent for security/verification |
| Grok 4.20 0309 v2 | 0.85x | 0.95x | Latest xAI reasoning model |
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
verifier_llm = get_auto_tuned_verifier_llm(model_id="grok-4.20-0309", is_live=True)
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
| `/api/v1/trading/execute` | POST | Execute a trade |
| `/api/v1/trading/analyze` | POST | Get market analysis |
| `/api/v1/trading/risk/assess` | POST | Assess trade risk |

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

---

## Frontend Components

### Page Structure

```
App.jsx
├── AuthPage.jsx (/login)
│   ├── Signup Form
│   ├── Login Form
│   ├── 2FA Verification Screen
│   └── Password Reset
├── TradingDashboard.jsx (/)
│   ├── Model Selection (dual-model)
│   ├── Chain Selection (ethereum/solana)
│   ├── Prompt Input
│   └── Result Display
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
DEFAULT_MODEL_2=grok-4.20      # Verifier

# Authentication
JWT_SECRET=your-secret-key     # JWT signing key
TWILIO_ACCOUNT_SID=xxx          # Twilio for SMS 2FA
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+xxx

# Email Notifications
SENDGRID_API_KEY=xxx           # SendGrid for emails
EMAIL_FROM=noreply@yourdomain.com

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

---

## Troubleshooting

### Common Issues

#### "CRITICAL RISK BLOCKED"
**Cause:** Risk score exceeds 75
**Solution:** Check market conditions. High volatility or low liquidity may trigger this.

#### "2FA code expired"
**Cause:** More than 5 minutes passed since code was sent
**Solution:** Request a new code by logging in again

#### "Email notifications not received"
**Cause:** Email provider configuration missing
**Solution:** Configure SendGrid/AWS SES in backend/.env

#### Risk Dashboard shows no data
**Cause:** SQLite database empty or inaccessible
**Solution:** Execute some trades first, check data directory permissions

---

## File Reference

### Backend Structure

```
backend/app/
├── api/
│   ├── auth.py              # Authentication + 2FA
│   ├── notifications.py      # Email notifications
│   ├── escrow.py            # Escrow management
│   ├── trading.py           # Trade execution
│   ├── backtest.py          # Backtesting
│   └── routes.py            # API route registration
├── agents/
│   ├── orchestrator.py      # Multi-agent coordination
│   └── trading_graph.py     # Agent definitions
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
    ├── config.py            # Settings
    ├── llm.py                # LLM provider
    └── auth.py               # Authentication middleware
```

### Frontend Structure

```
frontend/src/
├── App.jsx                   # Main app + routing
├── pages/
│   ├── AuthPage.jsx          # Login/Signup/2FA
│   ├── NotificationsPage.jsx # Notification preferences
│   ├── EscrowDashboard.jsx   # Escrow management
│   ├── TradingDashboard.jsx  # Main trading UI
│   └── ...
├── contexts/
│   ├── AuthContext.jsx       # Authentication state
│   ├── ThemeContext.jsx      # Auto day/night theme
│   ├── AppModeContext.jsx    # Paper/Live mode
│   └── WalletContext.jsx     # Web3 wallet
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

---

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See the [LICENSE](LICENSE) file for the full text.

Copyright (c) 2026 PITIPARK JIRAHIRANKIT (jose-cisco)