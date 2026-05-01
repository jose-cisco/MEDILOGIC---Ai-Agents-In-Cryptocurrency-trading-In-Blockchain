"""
RAG Knowledge Base — Hybrid Semantic + Lexical Retrieval
=========================================================

Architecture (mirrors diagram):
- Query Embedding (dense) -> ChromaDB vector search (top RAG_SEMANTIC_TOP_K)
- BM25 Keyword Index -> BM25 ranked search (top RAG_LEXICAL_TOP_K)
- Reciprocal Rank Fusion -> (top RAG_MAX_RESULTS)

Validated pattern: 95% synthetic / 93% real-world accuracy
(context-augmented LLM framework — Karim et al. 2025)

SECURITY (OWASP LLM Top 10):
- LLM04: Document validation before ingestion (Data Poisoning protection)
- LLM08: Vector DB query access control (Vector Weaknesses protection)
"""

import logging
from typing import Any
from langchain_ollama import OllamaEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import get_settings
from app.core.llm import get_rag_llm
from app.core.rag_security import (
    validate_rag_document,
    check_vector_query_permission,
    validate_query_embedding,
    DocumentSource,
    ContentRisk,
)

logger = logging.getLogger(__name__)


class MarketKnowledgeBase:
    """
    Hybrid-retrieval knowledge base for crypto market context.
    Combines dense semantic search (ChromaDB) with sparse lexical search (BM25)
    fused via Reciprocal Rank Fusion (RRF).
    
    SECURITY: Includes document validation (LLM04) and query access control (LLM08).
    """

    def __init__(self):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        settings = get_settings()
        self.settings = settings

        # ChromaDB (semantic / dense)
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.embeddings = OllamaEmbeddings(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.RAG_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._doc_counter = self.collection.count()

        # BM25 (lexical / sparse) — lazily rebuilt
        self._bm25 = None
        self._bm25_docs: list[str] = []
        self._bm25_ids: list[str] = []

    # ─────────────────────────────────────────────────────────────────────────
    # Document Ingestion with Security (LLM04)
    # ─────────────────────────────────────────────────────────────────────────

    def _chunk_text(self, text: str, metadata: dict) -> list[dict]:
        """Split text into overlapping chunks according to config."""
        chunk_size = self.settings.RAG_CHUNK_SIZE
        overlap = self.settings.RAG_CHUNK_OVERLAP
        if len(text) <= chunk_size:
            return [{"text": text, "metadata": metadata}]
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append({
                "text": text[start:end],
                "metadata": {
                    **metadata,
                    "chunk_start": start,
                    "chunk_end": min(end, len(text)),
                },
            })
            start = end - overlap
        return chunks

    def add_documents(self, docs: list[dict], validate: bool = True) -> dict:
        """
        Ingest raw {text, metadata} dicts, chunk, embed, and store.
        
        SECURITY (LLM04): Documents are validated before ingestion to prevent
        data poisoning. Validation checks for:
        - Suspicious patterns (prompt injection, code execution)
        - Financial manipulation indicators
        - Source reputation
        
        Args:
            docs: List of documents with text and metadata
            validate: Whether to apply security validation
        
        Returns:
            Dict with ingestion statistics and any validation issues
        """
        validated_docs = []
        validation_issues = []
        blocked_count = 0
        
        for doc in docs:
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})
            source_url = metadata.get("source_url")
            
            if validate:
                # LLM04: Validate document before ingestion
                result = validate_rag_document(text, metadata, source_url)
                
                if not result.valid:
                    logger.warning(
                        "Document blocked from RAG ingestion",
                        extra={
                            "risk_level": result.risk_level.value,
                            "issues": result.issues,
                            "source_reputation": result.source_reputation.value,
                        }
                    )
                    blocked_count += 1
                    validation_issues.append({
                        "text_preview": text[:100],
                        "issues": result.issues,
                        "risk_level": result.risk_level.value,
                    })
                    continue
                
                # Use sanitized content if available
                safe_text = result.sanitized_content or text
                if result.warnings:
                    logger.info(
                        "Document accepted with warnings",
                        extra={"warnings": result.warnings}
                    )
            else:
                safe_text = text
            
            # Chunk the validated/sanitized content
            chunked = self._chunk_text(safe_text, metadata)
            validated_docs.extend(chunked)
        
        if not validated_docs:
            return {
                "added": 0,
                "blocked": blocked_count,
                "issues": validation_issues,
            }
        
        # Generate IDs and embeddings
        ids = [
            f"doc_{i}"
            for i in range(self._doc_counter, self._doc_counter + len(validated_docs))
        ]
        self._doc_counter += len(validated_docs)
        texts = [c["text"] for c in validated_docs]
        metadatas = [c["metadata"] for c in validated_docs]
        
        try:
            embeddings = self.embeddings.embed_documents(texts)
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            # Invalidate BM25 cache so it rebuilds on next query
            self._bm25 = None
            logger.debug("Added %d chunks to knowledge base.", len(validated_docs))
        except Exception as exc:
            logger.error("Failed to add documents to RAG: %s", exc)
            return {
                "added": 0,
                "blocked": blocked_count,
                "issues": validation_issues,
                "error": str(exc),
            }
        
        return {
            "added": len(validated_docs),
            "blocked": blocked_count,
            "issues": validation_issues if validation_issues else None,
        }

    def add_market_data(self, market_reports: list[dict], validate: bool = True) -> dict:
        """Add market reports with security validation."""
        docs = []
        for r in market_reports:
            text = (
                f"Market Report: {r.get('title', 'Untitled')}\n"
                f"Date: {r.get('date', 'Unknown')}\n"
                f"Token: {r.get('token_pair', 'Unknown')}\n"
                f"Chain: {r.get('chain', 'Unknown')}\n\n"
                f"{r.get('content', '')}"
            )
            docs.append({"text": text, "metadata": {
                "type": "market_report",
                "token_pair": r.get("token_pair", ""),
                "chain": r.get("chain", ""),
                "date": r.get("date", ""),
                "source": r.get("source", "user"),
            }})
        return self.add_documents(docs, validate=validate)

    def add_trading_lessons(self, lessons: list[dict], validate: bool = True) -> dict:
        """Add trading lessons with security validation."""
        docs = []
        for lesson in lessons:
            text = (
                f"Trading Lesson: {lesson.get('scenario', 'Unknown')}\n"
                f"Action Taken: {lesson.get('action', 'Unknown')}\n"
                f"Outcome: {lesson.get('outcome', 'Unknown')}\n"
                f"Key Insight: {lesson.get('insight', '')}\n"
                f"Market Conditions: {lesson.get('conditions', '')}\n"
                f"Confidence: {lesson.get('confidence', 0.5)}"
            )
            docs.append({"text": text, "metadata": {
                "type": "trading_lesson",
                "scenario": lesson.get("scenario", ""),
                "action": lesson.get("action", ""),
            }})
        return self.add_documents(docs, validate=validate)

    def add_protocol_knowledge(self, protocols: list[dict], validate: bool = True) -> dict:
        """Add protocol knowledge with security validation."""
        docs = []
        for proto in protocols:
            text = (
                f"Protocol Knowledge: {proto.get('name', 'Unknown')}\n"
                f"Chain: {proto.get('chain', 'Unknown')}\n"
                f"Type: {proto.get('type', 'Unknown')}\n"
                f"Risk Level: {proto.get('risk_level', 'Unknown')}\n"
                f"Description: {proto.get('description', '')}\n"
                f"Key Metrics: {proto.get('metrics', '')}\n"
                f"Trading Notes: {proto.get('trading_notes', '')}"
            )
            docs.append({"text": text, "metadata": {
                "type": "protocol_knowledge",
                "name": proto.get("name", ""),
                "chain": proto.get("chain", ""),
                "risk_level": proto.get("risk_level", ""),
            }})
        return self.add_documents(docs, validate=validate)

    # ─────────────────────────────────────────────────────────────────────────
    # BM25 (Lexical / Sparse) Index
    # ─────────────────────────────────────────────────────────────────────────

    def _build_bm25_index(self) -> None:
        """(Re)build BM25 index from all docs currently in ChromaDB."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank_bm25 not installed — lexical search disabled.")
            return

        count = self.collection.count()
        if count == 0:
            self._bm25 = None
            return

        results = self.collection.get(include=["documents"])
        docs = results.get("documents", [])
        ids = results.get("ids", [])
        if not docs:
            return

        tokenised = [d.lower().split() for d in docs]
        self._bm25 = BM25Okapi(tokenised)
        self._bm25_docs = docs
        self._bm25_ids = ids
        logger.debug("BM25 index built with %d documents.", len(docs))

    def _lexical_search(self, query: str, top_k: int) -> list[dict]:
        """Return BM25-ranked results as [{id, text, score}]."""
        if self._bm25 is None:
            self._build_bm25_index()
        if self._bm25 is None:
            return []

        tokenised_query = query.lower().split()
        scores = self._bm25.get_scores(tokenised_query)
        import numpy as np
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "id": self._bm25_ids[idx],
                    "text": self._bm25_docs[idx],
                    "score": float(scores[idx]),
                })
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Semantic (Dense) Search with Access Control (LLM08)
    # ─────────────────────────────────────────────────────────────────────────

    def _semantic_search(self, query: str, top_k: int, user_id: str = "system") -> list[dict]:
        """
        ChromaDB cosine-similarity search with access control.
        
        SECURITY (LLM08): Query access control and rate limiting.
        """
        # LLM08: Check query permission
        allowed, reason = check_vector_query_permission(user_id)
        if not allowed:
            logger.warning("Vector query blocked: %s", reason)
            return []
        
        count = self.collection.count()
        if count == 0:
            return []
        n = min(top_k, count)
        query_embedding = self.embeddings.embed_query(query)
        
        # LLM08: Validate embedding anomaly
        is_valid, issues = validate_query_embedding(query_embedding, query)
        if not is_valid:
            logger.warning("Embedding validation issues: %s", issues)
            # Continue but log the issues
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        docs = []
        for i in range(len(results["ids"][0])):
            docs.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": (results["metadatas"][0][i] if results["metadatas"] else {}),
                "distance": results["distances"][0][i] if results["distances"] else 1.0,
                "semantic_score": 1.0 - (results["distances"][0][i] if results["distances"] else 1.0),
            })
        return docs

    # ─────────────────────────────────────────────────────────────────────────
    # Reciprocal Rank Fusion (RRF)
    # ─────────────────────────────────────────────────────────────────────────

    def _rrf_fusion(
        self,
        semantic_results: list[dict],
        lexical_results: list[dict],
        top_n: int,
    ) -> list[dict]:
        """
        Reciprocal Rank Fusion fusing semantic + lexical ranked lists.
        Score(d) = alpha * 1/(k + rank_semantic) + beta * 1/(k + rank_lexical)
        """
        settings = self.settings
        k = settings.RAG_RRF_K
        alpha = settings.RAG_SEMANTIC_WEIGHT
        beta = settings.RAG_LEXICAL_WEIGHT

        rrf_scores: dict[str, float] = {}
        doc_store: dict[str, dict] = {}

        for rank, doc in enumerate(semantic_results, start=1):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + alpha / (k + rank)
            doc_store[doc_id] = doc

        for rank, doc in enumerate(lexical_results, start=1):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + beta / (k + rank)
            if doc_id not in doc_store:
                doc_store[doc_id] = doc

        sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
        fused = []
        for doc_id in sorted_ids[:top_n]:
            d = dict(doc_store[doc_id])
            d["rrf_score"] = rrf_scores[doc_id]
            fused.append(d)
        return fused

    # ─────────────────────────────────────────────────────────────────────────
    # Public Query API
    # ─────────────────────────────────────────────────────────────────────────

    def query(self, query_text: str, n_results: int = 5, user_id: str = "system") -> list[dict]:
        """Simple semantic-only query with access control."""
        try:
            return self._semantic_search(query_text, top_k=n_results, user_id=user_id)
        except Exception as exc:
            logger.error("Semantic query failed: %s", exc)
            return []

    def hybrid_query(self, query_text: str, n_results: int | None = None, user_id: str = "system") -> list[dict]:
        """
        Hybrid retrieval: Semantic + Lexical → RRF fusion.
        Returns top n_results results with rrf_score, semantic_score, distance.
        
        SECURITY (LLM08): Includes query access control.
        """
        settings = self.settings
        n = n_results or settings.RAG_MAX_RESULTS
        sem_top_k = settings.RAG_SEMANTIC_TOP_K
        lex_top_k = settings.RAG_LEXICAL_TOP_K

        try:
            semantic_results = self._semantic_search(query_text, top_k=sem_top_k, user_id=user_id)
        except Exception as exc:
            logger.error("Semantic search error: %s", exc)
            semantic_results = []

        try:
            lexical_results = self._lexical_search(query_text, top_k=lex_top_k)
        except Exception as exc:
            logger.error("Lexical search error: %s", exc)
            lexical_results = []

        if not semantic_results and not lexical_results:
            return []

        fused = self._rrf_fusion(semantic_results, lexical_results, top_n=n)
        return fused

    def get_relevant_context(self, query: str, n_results: int = 3, user_id: str = "system") -> str:
        """Returns formatted context string (uses hybrid retrieval)."""
        if self.collection.count() == 0:
            return ""
        results = self.hybrid_query(query, n_results=n_results or self.settings.RAG_MAX_RESULTS, user_id=user_id)
        if not results:
            return ""
        parts = [
            f"[{r['id']}] (rrf: {r.get('rrf_score', 0):.3f} | "
            f"sem: {r.get('semantic_score', 0):.2f}) {r['text']}"
            for r in results
        ]
        return "\n\n---\n\n".join(parts)

    def get_enhanced_context(self, query: str, n_results: int = 10, user_id: str = "system") -> dict:
        """
        Full enhanced context with hybrid retrieval + LLM summary.

        Returns:
            {
                context:         formatted retrieved passages,
                summary:         LLM-synthesised 3-5 key points,
                sources:         list of source types found,
                semantic_scores: list of cosine similarity scores,
                lexical_scores:  list of BM25 scores,
                rrf_scores:      list of RRF fusion scores,
                result_count:    number of results returned,
            }
        """
        if self.collection.count() == 0:
            return {"context": "", "sources": [], "summary": "", "result_count": 0}

        results = self.hybrid_query(query, n_results=n_results, user_id=user_id)
        if not results:
            return {"context": "", "sources": [], "summary": "", "result_count": 0}

        raw_parts = [f"[{r['id']}] {r['text']}" for r in results]
        raw_context = "\n\n---\n\n".join(raw_parts)

        sources = list({
            r.get("metadata", {}).get("type", "unknown")
            for r in results
            if r.get("metadata")
        })

        semantic_scores = [r.get("semantic_score", 0.0) for r in results]
        lexical_scores = [r.get("score", 0.0) for r in results]
        rrf_scores = [r.get("rrf_score", 0.0) for r in results]

        try:
            llm = get_rag_llm()
            response = llm.invoke([
                SystemMessage(content=(
                    "You are a crypto market analyst. "
                    "Summarise the following retrieved market knowledge into "
                    "3-5 concise, actionable bullet points that directly inform "
                    "a trading decision. Cite source IDs where relevant."
                )),
                HumanMessage(content=(
                    f"Query: {query}\n\n"
                    f"Retrieved Context (hybrid semantic + lexical):\n{raw_context}"
                )),
            ])
            summary = response.content
        except Exception as exc:
            logger.warning("RAG LLM summarisation failed: %s", exc)
            summary = raw_context[:500]

        return {
            "context": raw_context,
            "summary": summary,
            "sources": sources,
            "semantic_scores": semantic_scores,
            "lexical_scores": lexical_scores,
            "rrf_scores": rrf_scores,
            "result_count": len(results),
        }

    def get_collection_stats(self) -> dict:
        """Return stats about the knowledge base."""
        try:
            count = self.collection.count()
            bm25_size = len(self._bm25_docs) if self._bm25 else 0
            return {
                "total_documents": count,
                "bm25_index_size": bm25_size,
                "bm25_indexed": self._bm25 is not None,
                "collection_name": self.collection.name,
                "status": "active" if count > 0 else "empty",
                "hybrid_retrieval": True,
                "semantic_weight": self.settings.RAG_SEMANTIC_WEIGHT,
                "lexical_weight": self.settings.RAG_LEXICAL_WEIGHT,
            }
        except Exception as exc:
            return {
                "total_documents": 0,
                "collection_name": "market_knowledge",
                "status": f"error: {exc}",
                "hybrid_retrieval": False,
            }