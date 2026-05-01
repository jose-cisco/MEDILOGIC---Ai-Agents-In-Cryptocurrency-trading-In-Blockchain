# RAG Upgrade: Hybrid Semantic + Lexical Pipeline + Dual-LLM Trading Graph

## Goal
Upgrade the existing `ai-trading-agent` backend RAG system and trading graph to mirror the architecture shown in the diagram:
- **Hybrid retrieval**: Semantic similarity (dense embeddings via ChromaDB) + Lexical similarity (BM25/keyword) — top 10–25 results merged and reranked
- **Context-augmented prompts**: Query + retrieved context injected into both Planner and Verifier
- **Dual-LLM wiring** (real trading): GLM-5.1 Reasoning (io.net) as Planner, Grok 4.20 (x.ai) as Verifier
- **Structured output generation**: Typed JSON schemas enforced at every node
- **Enhanced Knowledge API**: `/knowledge/enhanced-context` route plus full stats
- **Fix `engine.py`**: Deduplicate the random seed call (minor stuck bug), add dual-LLM planner to backtesting
- **Update `requirements.txt`**: Add `rank_bm25`, `langchain-openai`, `scikit-learn` for hybrid search + OpenAI-compatible x.ai client

---

## Proposed Changes

### 1. `requirements.txt` — add hybrid RAG + OpenAI client deps

#### [MODIFY] requirements.txt
- Add `rank_bm25>=0.2.2`
- Add `langchain-openai>=0.3.0`
- Add `scikit-learn>=1.4.0`

---

### 2. `core/config.py` — extended RAG settings

#### [MODIFY] config.py
- `RAG_MAX_RESULTS: int = 15` (was 5)
- `RAG_LEXICAL_WEIGHT: float = 0.35` (BM25 weight in hybrid fusion)
- `RAG_SEMANTIC_WEIGHT: float = 0.65`
- `RAG_TOP_N_FUSION: int = 15` (top-N after Reciprocal Rank Fusion)
- `IONET_MODEL: str = "THUDM/GLM-Z1-32B-0414"` (correct io.net model id for GLM-5.1 Reasoning)

---

### 3. `core/llm.py` — proper dual-LLM routing

#### [MODIFY] llm.py
- `get_planner_llm()` → always routes to **io.net** (GLM-5.1 Reasoning) if `IONET_API_KEY` is set, else Ollama
- `get_verifier_llm()` → always routes to **x.ai** (Grok 4.20) if `XAI_API_KEY` is set, else Ollama
- `get_controller_llm()` → routes to io.net (GLM-5.1) for final PoT consensus
- `get_ionet_llm()` helper: uses `ChatOpenAI` with `base_url=IONET_BASE_URL, api_key=IONET_API_KEY`
- Add fallback chain: primary → secondary → Ollama

---

### 4. `rag/knowledge_base.py` — Hybrid RAG pipeline (main upgrade)

#### [MODIFY] knowledge_base.py
Implements the full diagram pipeline:

```
Query
  ↓
Query Embedding (semantic)    +   BM25 keyword index (lexical)
       ↓                                  ↓
ChromaDB vector search           BM25 ranked results
  (Top 25 semantic)              (Top 25 lexical)
       ↓                                  ↓
        Reciprocal Rank Fusion (RRF)
               ↓
         Top 10-15 merged results
               ↓
     Context-augmented Prompt
               ↓
         RAG LLM (summarise)
               ↓
      {context, summary, sources, scores}
```

New methods:
- `_build_bm25_index()` — builds BM25 index from all docs in ChromaDB
- `hybrid_query()` — RRF fusion of semantic + lexical scores
- `get_enhanced_context()` — upgraded to use hybrid retrieval, returns `{context, summary, sources, semantic_scores, lexical_scores, result_count}`
- `get_relevant_context()` — updated to call `hybrid_query()`

---

### 5. `agents/trading_graph.py` — Dual-LLM + RAG-augmented decisions

#### [MODIFY] trading_graph.py
- **Planner node**: Use `get_planner_llm()` (io.net GLM-5.1), inject hybrid RAG context (top 10–15)
- **Verifier node**: Use `get_verifier_llm()` (x.ai Grok 4.20), include RAG context for cross-validation
- **Controller node**: Use `get_controller_llm()` (io.net GLM-5.1), reference RAG summary in PoT reasoning
- `_get_rag_context()`: call new `hybrid_query()` with `n_results=10`
- Add `rag_metadata` to `AgentState` to pass retrieval scores through the graph

---

### 6. `agents/orchestrator.py` — Pass RAG metadata

#### [MODIFY] orchestrator.py
- Include `rag_metadata` in both `run()` and `run_sync()` initial states
- Return `rag_metadata` in the orchestrator result

---

### 7. `backtesting/engine.py` — Fix + dual-LLM backtest

#### [MODIFY] engine.py
- **Fix**: Remove duplicate `np.random.seed(42)` call (lines 100 & 106)
- `_get_rag_context_for_backtest()`: call hybrid RAG with `n_results=10`
- `generate_llm_decisions()`: use `get_planner_llm()` (GLM-5.1) instead of `get_backtest_llm()`
- System message updated: "GLM-5.1 Reasoning via io.net"

---

### 8. `api/knowledge.py` — New endpoints

#### [MODIFY] knowledge.py
- `POST /knowledge/enhanced-context` → calls `get_enhanced_context()` with hybrid retrieval
- `POST /knowledge/hybrid-query` → exposes raw hybrid search results to frontend
- `GET /knowledge/stats` → returns collection stats + BM25 index size

---

### 9. `.env.example` — Updated keys

#### [MODIFY] .env.example
- Add `IONET_API_KEY=`
- Add `XAI_API_KEY=`
- Add `LLM_PROVIDER=ionet`
- Add `RAG_LEXICAL_WEIGHT=0.35`

---

### 10. Frontend RAG Panel — `TradingDashboard.jsx`

#### [MODIFY] TradingDashboard.jsx
- Show RAG context panel in trade result: semantic/lexical scores, top retrieved docs, summary
- Badge showing "GLM-5.1 Planner ✓" and "Grok 4.20 Verifier ✓" on trade card

---

## Verification Plan

### Automated
```bash
cd backend && python -c "from app.rag.knowledge_base import MarketKnowledgeBase; kb = MarketKnowledgeBase(); print(kb.get_collection_stats())"
cd backend && python -c "from app.core.llm import get_planner_llm, get_verifier_llm; print(get_planner_llm()); print(get_verifier_llm())"
```

### Manual
- Start backend: `uvicorn app.main:app --reload`
- POST `/api/knowledge/add` with sample docs
- POST `/api/knowledge/hybrid-query` → verify both semantic + lexical scores returned
- POST `/api/trading/execute` → verify `rag_context` appears in response reasoning
