from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_rag_llm

logger = logging.getLogger(__name__)


def _safe_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


class NewsScraperService:
    """Fetches website content, extracts likely article/news text, and turns it into RAG docs."""

    def __init__(self, timeout_seconds: float = 15.0, max_pages_per_seed: int = 5):
        self.timeout_seconds = timeout_seconds
        self.max_pages_per_seed = max_pages_per_seed

    async def scrape_urls(
        self,
        urls: list[str],
        task: str,
        source_label: str = "web-news",
        max_pages: int = 5,
    ) -> dict[str, Any]:
        normalized_urls = self._normalize_urls(urls)
        if not normalized_urls:
            raise ValueError("At least one valid http(s) URL is required.")

        capped_pages = max(1, min(max_pages, self.max_pages_per_seed))
        scraped_pages: list[dict[str, Any]] = []
        errors: list[str] = []

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "AI-Agent-Blockchain-Trading/1.0 "
                    "(news-ingestion bot for research and vector indexing)"
                )
            },
        ) as client:
            for seed_url in normalized_urls:
                try:
                    pages = await self._collect_pages(client, seed_url, capped_pages)
                    scraped_pages.extend(pages)
                except Exception as exc:
                    logger.warning("Failed to scrape %s: %s", seed_url, exc)
                    errors.append(f"{seed_url}: {exc}")

        if not scraped_pages:
            return {
                "status": "error",
                "documents": [],
                "scraped_pages": [],
                "ingested_count": 0,
                "errors": errors or ["No pages could be scraped."],
            }

        documents = self._build_documents_from_pages(scraped_pages, task, source_label)
        return {
            "status": "success" if documents else "error",
            "documents": documents,
            "scraped_pages": [
                {
                    "url": page["url"],
                    "title": page["title"],
                    "source_domain": page["domain"],
                }
                for page in scraped_pages
            ],
            "ingested_count": len(documents),
            "errors": errors,
        }

    def _normalize_urls(self, urls: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in urls:
            value = raw.strip()
            if not value:
                continue
            if not value.startswith(("http://", "https://")):
                value = f"https://{value}"
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path or ''}"
            if parsed.query:
                clean = f"{clean}?{parsed.query}"
            if clean not in seen:
                normalized.append(clean)
                seen.add(clean)
        return normalized

    async def _collect_pages(
        self,
        client: httpx.AsyncClient,
        seed_url: str,
        max_pages: int,
    ) -> list[dict[str, Any]]:
        seed_page = await self._fetch_page(client, seed_url)
        if not seed_page:
            return []

        pages = [seed_page]
        candidate_links = seed_page.get("candidate_links", [])
        for link in candidate_links[: max(0, max_pages - 1)]:
            try:
                page = await self._fetch_page(client, link)
            except Exception as exc:
                logger.debug("Skipping linked page %s: %s", link, exc)
                continue
            if page:
                pages.append(page)
        return pages

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> dict[str, Any] | None:
        response = await client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise ValueError(f"unsupported content type '{content_type or 'unknown'}'")

        return self._extract_page_data(url, response.text)

    def _extract_page_data(self, url: str, html: str) -> dict[str, Any]:
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise RuntimeError(
                "beautifulsoup4 is required for URL scraping. Install it with 'pip install beautifulsoup4'."
            ) from exc

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
        domain = urlparse(url).netloc

        meta_description = ""
        meta_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
        if meta_tag and meta_tag.get("content"):
            meta_description = meta_tag["content"].strip()

        headline_nodes = soup.select("h1, h2, h3")
        headlines = [
            node.get_text(" ", strip=True)
            for node in headline_nodes
            if node.get_text(" ", strip=True)
        ][:20]

        article_nodes = soup.select("article")
        article_text = "\n\n".join(
            node.get_text(" ", strip=True) for node in article_nodes if node.get_text(" ", strip=True)
        )

        paragraph_nodes = soup.select("main p, article p, p")
        paragraphs = [
            node.get_text(" ", strip=True)
            for node in paragraph_nodes
            if node.get_text(" ", strip=True)
        ][:40]

        body_text = article_text or "\n".join(paragraphs)
        body_text = re.sub(r"\s+", " ", body_text).strip()

        candidate_links: list[str] = []
        seen_links: set[str] = set()
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "").strip()
            label = anchor.get_text(" ", strip=True)
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            absolute = urljoin(url, href)
            parsed = urlparse(absolute)
            if parsed.netloc != domain:
                continue
            if parsed.path in {"", "/"}:
                continue
            if absolute in seen_links:
                continue

            lower_path = parsed.path.lower()
            anchor_parent = " ".join(anchor.get("class", []))
            looks_article = (
                len(label) >= 24
                or any(token in lower_path for token in ["/news", "/article", "/story", "/posts", "/markets"])
                or "article" in anchor_parent.lower()
            )
            if looks_article:
                candidate_links.append(absolute)
                seen_links.add(absolute)

        compiled_text = "\n\n".join(
            part for part in [
                f"Title: {title}" if title else "",
                f"Description: {meta_description}" if meta_description else "",
                f"Headlines: {' | '.join(headlines[:10])}" if headlines else "",
                f"Body: {_truncate(body_text, 12000)}" if body_text else "",
            ] if part
        )

        return {
            "url": url,
            "domain": domain,
            "title": title or domain,
            "description": meta_description,
            "headlines": headlines,
            "body_text": body_text,
            "compiled_text": compiled_text,
            "candidate_links": candidate_links[:6],
        }

    def _build_documents_from_pages(
        self,
        scraped_pages: list[dict[str, Any]],
        task: str,
        source_label: str,
    ) -> list[dict[str, Any]]:
        llm_payload = []
        for page in scraped_pages:
            llm_payload.append({
                "url": page["url"],
                "domain": page["domain"],
                "title": page["title"],
                "description": page["description"],
                "headlines": page["headlines"][:10],
                "content": _truncate(page["compiled_text"], 6000),
            })

        try:
            llm = get_rag_llm()
            response = llm.invoke([
                SystemMessage(content=(
                    "You are an autonomous web-news extraction assistant. "
                    "Given scraped website content and a task, extract distinct news items relevant "
                    "to the task and return ONLY valid JSON as an array. "
                    "Each item must have keys: title, summary, source_url, source_domain, published_at, tags. "
                    "Use an empty string for unknown published_at and an empty array for missing tags. "
                    "Be concise, factual, and avoid duplicating the same story."
                )),
                HumanMessage(content=(
                    f"Task:\n{task}\n\n"
                    f"Scraped website payload:\n{json.dumps(llm_payload, ensure_ascii=True)}"
                )),
            ])
            extracted = self._parse_json_array(response.content)
        except Exception as exc:
            logger.warning("LLM news extraction failed, using fallback documents: %s", exc)
            extracted = []

        documents: list[dict[str, Any]] = []
        for item in extracted:
            title = str(item.get("title", "")).strip()
            summary = str(item.get("summary", "")).strip()
            source_url = str(item.get("source_url", "")).strip()
            source_domain = str(item.get("source_domain", "")).strip()
            published_at = str(item.get("published_at", "")).strip()
            tags = item.get("tags") if isinstance(item.get("tags"), list) else []
            if not title or not summary or not source_url:
                continue

            text = "\n".join(part for part in [
                f"News Title: {title}",
                f"Scrape Task: {task}",
                f"Summary: {summary}",
                f"Published At: {published_at}" if published_at else "",
                f"Tags: {', '.join(str(tag) for tag in tags)}" if tags else "",
                f"Source URL: {source_url}",
                f"Source Domain: {source_domain}" if source_domain else "",
            ] if part)
            documents.append({
                "text": text,
                "metadata": {
                    "type": "web_news",
                    "source": source_label,
                    "source_url": source_url,
                    "source_domain": source_domain or urlparse(source_url).netloc,
                    "task": task,
                    "title": title,
                    "published_at": published_at,
                    "tags": ", ".join(str(tag) for tag in tags),
                },
            })

        if documents:
            return documents

        fallback_documents: list[dict[str, Any]] = []
        for index, page in enumerate(scraped_pages, start=1):
            fallback_text = "\n".join(part for part in [
                f"Scraped Page Title: {page['title']}",
                f"Scrape Task: {task}",
                f"Source URL: {page['url']}",
                f"Source Domain: {page['domain']}",
                _truncate(page["compiled_text"], 5000),
            ] if part)
            fallback_documents.append({
                "text": fallback_text,
                "metadata": {
                    "type": "web_page_scrape",
                    "source": source_label,
                    "source_url": page["url"],
                    "source_domain": page["domain"],
                    "task": task,
                    "title": page["title"] or f"scraped-page-{index}",
                    "slug": _safe_slug(page["title"] or page["domain"]),
                },
            })
        return fallback_documents

    def _parse_json_array(self, content: str) -> list[dict[str, Any]]:
        try:
            start = content.find("[")
            end = content.rfind("]") + 1
            payload = content[start:end] if start >= 0 and end > start else content
            parsed = json.loads(payload)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError:
            logger.debug("Failed to decode scraper LLM JSON payload.")
        return []


news_scraper_service = NewsScraperService()
