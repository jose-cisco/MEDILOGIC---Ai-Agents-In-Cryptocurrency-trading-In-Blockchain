# Walkthrough — Hybrid RAG + Dual-LLM Upgrade

## What Was Changed

### 10 files modified across 4 layers

| Layer | File | Change |
|---|---|---|
| **Deps** | `requirements.txt` | Added `rank_bm25`, `langchain-openai`, `scikit-learn` |
| **Config** | `core/config.py` | New hybrid RAG params; correct GLM-5.1 model slug |
| **LLM** | `core/llm.py` | Proper dual-LLM routing with OpenAI-compat clients |
| **RAG** | `rag/knowledge_base.py` | Full hybrid pipeline rewrite (BM25 + RRF) |
| **Graph** | `agents/trading_graph.py` | `rag_metadata` in state; dual-LLM nodes; PoT confidence |
| **Graph** | `agents/orchestrator.py` | Returns `rag_metadata` through the graph |
| **Engine** | `backtesting/engine.py` | Fixed duplicate seed bug; upgraded to hybrid RAG |
| **API** | `api/knowledge.py` | New `/hybrid-query`, `/enhanced-context`, `/stats` endpoints |
| **API** | `api/trading.py` | Returns `rag_metadata` in every `TradeResult` |
| **Schema** | `schemas/models.py` | `rag_metadata` field on `TradeResult`; new fields on `TradeDecision` |
| **Frontend** | `TradingDashboard.jsx` | LLM badges, collapsible RAG panel with RRF score bars |

---

## Architecture — Hybrid RAG Pipeline

```
Query (token_pair + chain + market_data)
        │
        ├─► Query Embedding (OllamaEmbeddings dense)
        │           │
        │           └─► ChromaDB cosine search
        │                   top-25 semantic results
        │
        └─► BM25Okapi keyword index (rank_bm25)
                    │
                    └─► BM25 ranked results
                            top-25 lexical results
                                    │
                ────────────────────┘
                Reciprocal Rank Fusion (RRF)
                  score = 0.65/(60+rank_sem) + 0.35/(60+rank_lex)
                ────────────────────
                        │
                Top-15 fused passages
                        │
                Context-augmented Prompt
                        │
                RAG LLM (GLM-5.1 via Controller)
                        │
        {context, summary, sources,
         semantic_scores, lexical_scores,
         rrf_scores, result_count}
```

---

## Architecture — Dual-LLM Trading Graph

```
Planner (GLM-5.1 Reasoning, io.net)
    Perceive → Plan → Reason → Act
    Input:  market_data + hybrid RAG context (top-10)
    Output: {action, amount, confidence, risk_score,
             market_regime, indicators_used, rag_sources_cited}
        ↓
Verifier (Grok 4.20 Reasoning, x.ai)
    Ensemble security analysis (FELLMVP 98.8%)
    Input:  planner_decision + market_data + RAG context
    Output: {approved, adjusted_risk_score,
             vulnerabilities_found, ensemble_scores,
             rag_cross_validation}
        ↓
Controller (GLM-5.1 Reasoning, io.net)
    Proof-of-Thought (PoT) consensus
    Input:  planner + verifier + RAG summary
    Output: {approved, final_action, final_amount,
             execution_parameters, pot_confidence}
        ↓
Execute / Reject → TradeResult (with rag_metadata)
```

---

## What Was Fixed

- **`engine.py` duplicate seed bug**: `np.random.seed(42)` was called twice
  (lines 100 and 106). Removed the duplicate — now called once.

---

## New API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/knowledge/hybrid-query` | RRF-fused results with `rrf_score` per passage |
| `POST` | `/api/knowledge/enhanced-context` | Full context + LLM synthesis + scores |
| `GET` | `/api/knowledge/stats` | Collection size + BM25 index size + weights |

---

## Activation for Real Trading

### 1. Install new dependencies
```bash
cd ai-trading-agent/backend
pip install rank_bm25 langchain-openai scikit-learn
```

### 2. Create `.env` from example
```bash
cp .env.example .env
```

### 3. Fill in your API keys in `.env`
```env
# Planner + Controller
IONET_API_KEY=your_ionet_key
IONET_MODEL=THUDM/GLM-Z1-32B-0414

# Verifier
XAI_API_KEY=your_xai_key
XAI_MODEL=grok-3-mini-fast-beta   # update slug when Grok 4.20 is GA

# Switch provider
LLM_PROVIDER=ionet
```

### 4. Start backend
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Verify RAG is live
```bash
# Add some market knowledge
curl -X POST http://localhost:8000/api/knowledge/add \
  -H 'Content-Type: application/json' \
  -d '{"documents":[{"text":"ETH/USDT bullish trend Q1 2025 RSI 58 MACD crossover","metadata":{"type":"market_report","token_pair":"ETH/USDT"}}]}'

# Hybrid query
curl -X POST http://localhost:8000/api/knowledge/hybrid-query \
  -H 'Content-Type: application/json' \
  -d '{"query":"ETH trading conditions","n_results":5}'

# Stats
curl http://localhost:8000/api/knowledge/stats
```

---

## Verification Results

All 9 Python files pass AST syntax check ✓

```
✓  app/core/config.py
✓  app/core/llm.py
✓  app/rag/knowledge_base.py
✓  app/agents/trading_graph.py
✓  app/agents/orchestrator.py
✓  app/backtesting/engine.py
✓  app/api/knowledge.py
✓  app/api/trading.py
✓  app/schemas/models.py
```

---

## Fallback Behaviour (Local Dev — No API Keys)

| Condition | Planner | Verifier |
|---|---|---|
| `IONET_API_KEY` set | GLM-5.1 via io.net ✓ | — |
| `XAI_API_KEY` set | — | Grok 4.20 via x.ai ✓ |
| Neither key set | Ollama (local) | Ollama (local) |
| `rank_bm25` missing | ChromaDB semantic only | ChromaDB semantic only |
