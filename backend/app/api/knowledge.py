"""
Knowledge API Routes
====================
Exposes the hybrid RAG knowledge base (semantic + lexical retrieval) via REST.

Endpoints:
  POST /knowledge/add              — ingest raw documents (JSON)
  POST /knowledge/upload           — ingest PDF or TXT files (multipart)
  POST /knowledge/scrape-url       — fetch website URL(s), extract news by task, ingest into ChromaDB
  POST /knowledge/query            — semantic-only search
  POST /knowledge/hybrid-query     — hybrid semantic + lexical (RRF fused) [x402 paid]
  POST /knowledge/context          — relevant context string (backward compat)
  POST /knowledge/enhanced-context — full hybrid context with scores + summary [x402 paid]
  GET  /knowledge/stats            — collection stats + BM25 index info

x402 Payment:
  hybrid-query and enhanced-context endpoints require x402 payment when enabled.
  Basic query, add, context, and stats remain free.
"""
from __future__ import annotations

import io
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from app.rag.knowledge_base import MarketKnowledgeBase
from app.core.x402 import x402_service, get_resource_price, PaymentResource
from app.services.news_scraper_service import news_scraper_service

router = APIRouter()
kb: Optional[MarketKnowledgeBase] = None


def get_kb() -> MarketKnowledgeBase:
    global kb
    if kb is None:
        kb = MarketKnowledgeBase()
    return kb


def _build_knowledge_x402_meta(http_request: Request, resource: PaymentResource) -> dict:
    """Build x402 payment metadata for knowledge endpoint responses."""
    receipt = getattr(http_request.state, "x402_receipt", None)
    if receipt:
        return {
            "payment_required": True,
            "payment_verified": True,
            "payment_tx_hash": receipt.tx_hash,
            "payment_amount_usd": receipt.amount_usd,
            "payment_resource": receipt.resource,
        }
    if x402_service.enabled:
        return {
            "payment_required": True,
            "payment_verified": False,
            "payment_resource": resource.value,
            "price_usd": get_resource_price(resource),
        }
    return {"payment_required": False}


# ─── Request Models ───────────────────────────────────────────────────────────

class AddDocsRequest(BaseModel):
    documents: list[dict]


class QueryRequest(BaseModel):
    query: str
    n_results: int = Field(default=10, ge=1, le=50)


class ScrapeUrlRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)
    task: str = Field(min_length=5, max_length=4000)
    source_label: str = Field(default="web-news")
    max_pages: int = Field(default=5, ge=1, le=8)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/add")
async def add_documents(request: AddDocsRequest):
    """Ingest documents into the hybrid knowledge base."""
    try:
        get_kb().add_documents(request.documents)
        return {"status": "success", "count": len(request.documents)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    source: str = Form(default="file-upload"),
):
    """
    Ingest one or more PDF or TXT files into the hybrid knowledge base.
    Each file is parsed into text, then chunked and embedded.
    """
    docs = []
    errors = []
    for f in files:
        filename = f.filename or "unknown"
        ext = filename.rsplit(".", 1)[-1].lower()
        try:
            raw = await f.read()
            if ext == "txt":
                text = raw.decode("utf-8", errors="replace")
            elif ext == "pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(io.BytesIO(raw))
                    text = "\n\n".join(
                        page.extract_text() or "" for page in reader.pages
                    )
                except ImportError:
                    errors.append(f"{filename}: pypdf not installed — pip install pypdf")
                    continue
            else:
                errors.append(f"{filename}: unsupported type '{ext}' (use PDF or TXT)")
                continue

            if not text.strip():
                errors.append(f"{filename}: file appears to be empty or unreadable")
                continue

            docs.append({
                "text": text,
                "metadata": {"source": source, "filename": filename, "type": ext},
            })
        except Exception as e:
            errors.append(f"{filename}: {e}")

    if docs:
        get_kb().add_documents(docs)

    return {
        "status": "success" if docs else "error",
        "ingested_files": [d["metadata"]["filename"] for d in docs],
        "ingested_count": len(docs),
        "errors": errors,
    }


@router.post("/scrape-url")
async def scrape_url_content(request: ScrapeUrlRequest):
    """
    Scrape one or more website URLs, let the LLM extract task-relevant news items,
    and ingest the resulting documents into ChromaDB.
    """
    result = await news_scraper_service.scrape_urls(
        urls=request.urls,
        task=request.task,
        source_label=request.source_label,
        max_pages=request.max_pages,
    )

    documents = result.get("documents", [])
    if documents:
        get_kb().add_documents(documents)

    return {
        "status": "success" if documents else result.get("status", "error"),
        "ingested_count": len(documents),
        "scraped_pages": result.get("scraped_pages", []),
        "errors": result.get("errors", []),
        "source_label": request.source_label,
    }


@router.post("/query")
async def query_knowledge(request: QueryRequest):
    """Semantic-only vector search (backward compatible)."""
    try:
        results = get_kb().query(request.query, request.n_results)
        return {"results": results, "retrieval_mode": "semantic"}
    except Exception as e:
        return {"results": [], "error": str(e)}


@router.post("/hybrid-query")
async def hybrid_query_knowledge(request: QueryRequest, http_request: Request):
    """
    Hybrid retrieval: semantic similarity (ChromaDB) + lexical (BM25),
    fused via Reciprocal Rank Fusion. Returns rrf_score per result.

    x402: Requires payment when X402_ENABLED=true (X-Payment header).
    """
    try:
        results = get_kb().hybrid_query(request.query, n_results=request.n_results)
        x402_meta = _build_knowledge_x402_meta(http_request, PaymentResource.KNOWLEDGE_HYBRID)
        return {
            "results": results,
            "retrieval_mode": "hybrid_semantic_lexical_rrf",
            "result_count": len(results),
            "x402_metadata": x402_meta,
        }
    except Exception as e:
        return {"results": [], "error": str(e)}


@router.post("/context")
async def get_context(request: QueryRequest):
    """Get context string using hybrid retrieval (backward compatible)."""
    try:
        context = get_kb().get_relevant_context(request.query, request.n_results)
        return {"context": context}
    except Exception as e:
        return {"context": "", "error": str(e)}


@router.post("/enhanced-context")
async def get_enhanced_context(request: QueryRequest, http_request: Request):
    """
    Full enhanced context: hybrid RAG retrieval + LLM summary (GLM-5.1).
    Returns context passages, LLM synthesis, per-passage scores, and sources.

    x402: Requires payment when X402_ENABLED=true (X-Payment header).
    """
    try:
        data = get_kb().get_enhanced_context(request.query, n_results=request.n_results)
        x402_meta = _build_knowledge_x402_meta(http_request, PaymentResource.KNOWLEDGE_ENHANCED)
        return {
            "status": "success",
            **data,
            "retrieval_mode": "hybrid_semantic_lexical_rrf",
            "x402_metadata": x402_meta,
        }
    except Exception as e:
        return {"status": "error", "context": "", "summary": "", "error": str(e)}


@router.get("/stats")
async def get_stats():
    """Knowledge base statistics including BM25 index info."""
    try:
        stats = get_kb().get_collection_stats()
        return {"status": "success", **stats}
    except Exception as e:
        return {"status": "error", "error": str(e)}
