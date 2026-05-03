"""
RAG Security Module - LLM04 & LLM08 Protections
================================================

Addresses OWASP LLM Top 10 vulnerabilities:

LLM04 - Data Poisoning / RAG Validation:
- Document content validation before ingestion
- Source reputation scoring
- Anomaly detection in embeddings
- Content integrity verification

LLM08 - Vector and Embedding Weaknesses:
- Vector database access controls
- Embedding anomaly detection
- Query rate limiting
- Document integrity checks
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ─── Document Validation Patterns ───────────────────────────────────────────────

SUSPICIOUS_PATTERNS = [
    # Prompt injection in documents
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|rules)",
    r"disregard\s+(all\s+)?(previous|instructions)",
    r"you\s+are\s+now\s+(a|an)\s+\w+",
    
    # Code execution patterns
    r"<script[^>]*>.*?</script>",
    r"javascript\s*:",
    r"on\w+\s*=",
    r"eval\s*\(",
    r"exec\s*\(",
    
    # Data manipulation patterns
    r"(?:inject|poison|manipulate)\s+(?:data|market|price)",
    r"(?:fake|false|manipulated)\s+(?:data|signal|indicator)",
    
    # Exfiltration patterns
    r"(?:exfiltrate|steal|leak)\s+(?:data|key|secret)",
    r"(?:send|transmit|upload)\s+(?:to|via)\s+(?:http|ftp)",
]

FINANCIAL_MANIPULATION_PATTERNS = [
    r"pump\s+(?:and\s+)?dump",
    r"wash\s+trad(?:e|ing)",
    r"market\s+manipulation",
    r"spoof(?:ing)?",
    r"front[- ]?run(?:ning)?",
    r"insider\s+trad(?:e|ing)",
    r"price\s+manipulation",
    r"coordinate[ds]?\s+(?:buy|sell)",
    r"artificial\s+(?:price|volume|demand)",
]


class DocumentSource(str, Enum):
    """Document source reputation levels."""
    OFFICIAL = "official"      # Official sources (exchanges, APIs)
    VERIFIED = "verified"      # Verified third-party
    UNVERIFIED = "unverified"  # User-submitted
    SUSPICIOUS = "suspicious"   # Flagged content
    BLOCKED = "blocked"        # Blacklisted source


class ContentRisk(str, Enum):
    """Risk levels for document content."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DocumentValidationResult:
    """Result of document validation."""
    valid: bool
    risk_level: ContentRisk
    source_reputation: DocumentSource
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_content: Optional[str] = None
    integrity_hash: Optional[str] = None
    confidence: float = 1.0


@dataclass  
class EmbeddingAnomalyResult:
    """Result of embedding anomaly detection."""
    is_anomaly: bool
    anomaly_score: float
    details: List[str] = field(default_factory=list)


# ─── Document Source Reputation ─────────────────────────────────────────────────

# Known trusted sources for financial/market data
TRUSTED_SOURCES = {
    # Official exchanges
    "coingecko.com": DocumentSource.OFFICIAL,
    "coinmarketcap.com": DocumentSource.OFFICIAL,
    "binance.com": DocumentSource.OFFICIAL,
    "coinbase.com": DocumentSource.OFFICIAL,
    "kraken.com": DocumentSource.OFFICIAL,
    "uniswap.org": DocumentSource.OFFICIAL,
    
    # Verified financial data
    "messari.io": DocumentSource.VERIFIED,
    "defillama.com": DocumentSource.VERIFIED,
    "dune.com": DocumentSource.VERIFIED,
    "etherscan.io": DocumentSource.VERIFIED,
    "solscan.io": DocumentSource.VERIFIED,
    
    # Verified news
    "coindesk.com": DocumentSource.VERIFIED,
    "cointelegraph.com": DocumentSource.VERIFIED,
    "theblock.co": DocumentSource.VERIFIED,
}

# Blacklisted sources
BLACKLISTED_SOURCES = {
    "bitconnect.com": DocumentSource.BLOCKED,
    "plustoken.com": DocumentSource.BLOCKED,
    "onecoin.com": DocumentSource.BLOCKED,
}


class DocumentValidator:
    """
    Validates documents before RAG ingestion.
    
    Addresses LLM04: Data Poisoning
    """
    
    def __init__(self):
        self.suspicious_patterns = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_PATTERNS]
        self.financial_patterns = [re.compile(p, re.IGNORECASE) for p in FINANCIAL_MANIPULATION_PATTERNS]
        self._document_registry: Dict[str, Dict[str, Any]] = {}
        self._source_stats: Dict[str, Dict[str, int]] = {}
    
    def validate_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source_url: Optional[str] = None
    ) -> DocumentValidationResult:
        """
        Validate a document for RAG ingestion.
        
        Args:
            content: Document text content
            metadata: Optional metadata (type, date, etc.)
            source_url: Optional source URL for reputation check
        
        Returns:
            DocumentValidationResult with validation outcome
        """
        issues = []
        warnings = []
        risk_level = ContentRisk.SAFE
        source_reputation = DocumentSource.UNVERIFIED
        
        # Check source reputation
        if source_url:
            source_reputation = self._check_source_reputation(source_url)
            if source_reputation == DocumentSource.BLOCKED:
                return DocumentValidationResult(
                    valid=False,
                    risk_level=ContentRisk.CRITICAL,
                    source_reputation=source_reputation,
                    issues=["Document from blacklisted source blocked"],
                    confidence=1.0
                )
            if source_reputation == DocumentSource.SUSPICIOUS:
                risk_level = ContentRisk.HIGH
                issues.append("Document from suspicious source")
        
        # Check for suspicious patterns
        pattern_issues = self._check_suspicious_patterns(content)
        if pattern_issues:
            issues.extend(pattern_issues)
            if len(pattern_issues) > 3:
                risk_level = ContentRisk.CRITICAL
            elif len(pattern_issues) > 1:
                risk_level = max(risk_level, ContentRisk.HIGH, key=lambda x: x.value)
            else:
                risk_level = max(risk_level, ContentRisk.MEDIUM, key=lambda x: x.value)
        
        # Check for financial manipulation patterns
        financial_issues = self._check_financial_patterns(content)
        if financial_issues:
            warnings.extend(financial_issues)
            risk_level = max(risk_level, ContentRisk.MEDIUM, key=lambda x: x.value)
        
        # Validate metadata
        if metadata:
            meta_issues = self._validate_metadata(metadata)
            issues.extend(meta_issues)
        
        # Calculate integrity hash
        integrity_hash = self._calculate_hash(content)
        
        # Check for duplicate/near-duplicate
        duplicate_check = self._check_duplicate(content, integrity_hash)
        if duplicate_check:
            warnings.append("Potential duplicate content detected")
        
        # Determine if document should be blocked
        is_valid = risk_level not in (ContentRisk.CRITICAL, ContentRisk.HIGH)
        
        # Sanitize content if needed
        sanitized_content = None
        if risk_level in (ContentRisk.MEDIUM, ContentRisk.LOW):
            sanitized_content = self._sanitize_content(content)
        
        # Register document
        self._register_document(integrity_hash, source_url, risk_level)
        
        return DocumentValidationResult(
            valid=is_valid,
            risk_level=risk_level,
            source_reputation=source_reputation,
            issues=issues,
            warnings=warnings,
            sanitized_content=sanitized_content,
            integrity_hash=integrity_hash,
            confidence=0.9 if issues else 1.0
        )
    
    def _check_source_reputation(self, source_url: str) -> DocumentSource:
        """Check reputation of source URL."""
        source_url_lower = source_url.lower()
        
        # Check blacklist first
        for blocked in BLACKLISTED_SOURCES:
            if blocked in source_url_lower:
                return DocumentSource.BLOCKED
        
        # Check trusted sources
        for trusted, rep in TRUSTED_SOURCES.items():
            if trusted in source_url_lower:
                return rep
        
        # Check for suspicious patterns in URL
        suspicious_url_patterns = [
            r"free\s*\d+\s*signals?",
            r"guaranteed\s+(?:profit|returns?)",
            r"\d+x\s+(?:gains?|profit)",
        ]
        for pattern in suspicious_url_patterns:
            if re.search(pattern, source_url_lower, re.IGNORECASE):
                return DocumentSource.SUSPICIOUS
        
        return DocumentSource.UNVERIFIED
    
    def _check_suspicious_patterns(self, content: str) -> List[str]:
        """Check content for suspicious patterns."""
        issues = []
        for pattern in self.suspicious_patterns:
            matches = pattern.findall(content)
            if matches:
                issues.append("Suspicious pattern: " + pattern.pattern[:50])
        return issues
    
    def _check_financial_patterns(self, content: str) -> List[str]:
        """Check for financial manipulation indicators."""
        warnings = []
        for pattern in self.financial_patterns:
            if pattern.search(content):
                warnings.append("Financial manipulation indicator: " + pattern.pattern[:40])
        return warnings
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Validate document metadata."""
        issues = []
        
        # Check required metadata fields
        required_fields = ["type", "date"]
        for field in required_fields:
            if field not in metadata:
                issues.append("Missing required metadata: " + field)
        
        # Validate date format
        if "date" in metadata:
            try:
                datetime.fromisoformat(str(metadata["date"]).replace("Z", "+00:00"))
            except ValueError:
                issues.append("Invalid date format in metadata")
        
        return issues
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate integrity hash for content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _check_duplicate(self, content: str, hash_value: str) -> bool:
        """Check if document is duplicate or near-duplicate."""
        if hash_value in self._document_registry:
            return True
        
        # Check for similar content (simple check)
        content_lower = content.lower()[:500]  # First 500 chars
        for doc_hash, doc_info in self._document_registry.items():
            if content_lower == doc_info.get("content_preview", ""):
                return True
        
        return False
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content to remove potentially dangerous elements."""
        sanitized = content
        
        # Remove script tags (including permissive malformed closing tags browsers may accept)
        script_tag_pattern = re.compile(
            r"<script\b[^>]*>.*?</script\b[^>]*>",
            flags=re.IGNORECASE | re.DOTALL,
        )
        previous = None
        while previous != sanitized:
            previous = sanitized
            sanitized = script_tag_pattern.sub("", sanitized)
        
        # Remove javascript: URLs
        sanitized = re.sub(r'javascript\s*:[^"\'>\s]+', '', sanitized, flags=re.IGNORECASE)
        
        # Remove event handlers
        sanitized = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)
        
        # Remove injection patterns
        sanitized = re.sub(
            r'(ignore|disregard)\s+(all\s+)?(previous|instructions)',
            '[REMOVED]',
            sanitized,
            flags=re.IGNORECASE
        )
        
        return sanitized
    
    def _register_document(
        self,
        hash_value: str,
        source_url: Optional[str],
        risk_level: ContentRisk
    ) -> None:
        """Register document in tracking system."""
        self._document_registry[hash_value] = {
            "source_url": source_url,
            "risk_level": risk_level.value,
            "registered_at": datetime.utcnow().isoformat(),
        }
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about validated documents."""
        total = len(self._document_registry)
        by_risk = {}
        for doc_info in self._document_registry.values():
            risk = doc_info.get("risk_level", "unknown")
            by_risk[risk] = by_risk.get(risk, 0) + 1
        
        return {
            "total_documents": total,
            "by_risk_level": by_risk,
        }


class VectorDatabaseSecurity:
    """
    Provides access control and monitoring for vector database.
    
    Addresses LLM08: Vector and Embedding Weaknesses
    """
    
    def __init__(self, max_query_rate: int = 100, rate_window_seconds: int = 60):
        self.max_query_rate = max_query_rate
        self.rate_window_seconds = rate_window_seconds
        self._query_log: Dict[str, List[float]] = {}  # user_id -> timestamps
        self._embedding_cache: Dict[str, List[float]] = {}
        self._anomaly_threshold = 0.15  # 15% deviation
    
    def check_query_permission(
        self,
        user_id: str,
        operation: str = "query"
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user has permission for vector DB operation.
        
        Args:
            user_id: User identifier
            operation: Operation type (query, insert, delete)
        
        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        # Rate limiting
        now = time.time()
        window_start = now - self.rate_window_seconds
        
        if user_id not in self._query_log:
            self._query_log[user_id] = []
        
        # Clean old entries
        self._query_log[user_id] = [
            ts for ts in self._query_log[user_id] if ts > window_start
        ]
        
        # Check rate limit
        if len(self._query_log[user_id]) >= self.max_query_rate:
            return False, "Rate limit exceeded. Try again later."
        
        # Log this query
        self._query_log[user_id].append(now)
        
        return True, None
    
    def detect_embedding_anomaly(
        self,
        embedding: List[float],
        expected_norm: float = 1.0,
        expected_dim: Optional[int] = None
    ) -> EmbeddingAnomalyResult:
        """
        Detect anomalies in embeddings that could indicate poisoning.
        
        Args:
            embedding: The embedding vector to check
            expected_norm: Expected L2 norm (usually 1.0 for normalized embeddings)
            expected_dim: Expected dimensionality
        
        Returns:
            EmbeddingAnomalyResult with anomaly detection results
        """
        details = []
        anomaly_score = 0.0
        
        if not embedding:
            return EmbeddingAnomalyResult(
                is_anomaly=True,
                anomaly_score=1.0,
                details=["Empty embedding vector"]
            )
        
        # Check dimensionality
        if expected_dim and len(embedding) != expected_dim:
            anomaly_score += 0.5
            details.append(f"Unexpected dimensionality: {len(embedding)} vs expected {expected_dim}")
        
        # Check L2 norm
        import math
        norm = math.sqrt(sum(x * x for x in embedding))
        norm_deviation = abs(norm - expected_norm) / expected_norm
        
        if norm_deviation > self._anomaly_threshold:
            anomaly_score += 0.3
            details.append(f"Norm deviation: {norm:.4f} vs expected {expected_norm} ({norm_deviation:.1%})")
        
        # Check for extreme values
        max_val = max(abs(x) for x in embedding)
        min_val = min(embedding)
        
        if max_val > 10.0:  # Unusually large values
            anomaly_score += 0.4
            details.append(f"Extreme values detected: max |x| = {max_val:.2f}")
        
        # Check for uniform distribution (potential synthetic injection)
        mean_val = sum(embedding) / len(embedding)
        variance = sum((x - mean_val) ** 2 for x in embedding) / len(embedding)
        
        if variance < 0.001:  # Suspiciously uniform
            anomaly_score += 0.3
            details.append("Suspiciously uniform embedding (possible synthetic injection)")
        
        # Check for NaN or Inf
        import math
        if any(math.isnan(x) or math.isinf(x) for x in embedding):
            anomaly_score = 1.0
            details.append("NaN or Inf values in embedding")
        
        return EmbeddingAnomalyResult(
            is_anomaly=anomaly_score > 0.5,
            anomaly_score=min(1.0, anomaly_score),
            details=details
        )
    
    def validate_query_embedding(
        self,
        query_embedding: List[float],
        query_text: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate query embedding before vector search.
        
        Args:
            query_embedding: The query embedding vector
            query_text: Original query text
        
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        
        # Check embedding anomaly
        anomaly_result = self.detect_embedding_anomaly(query_embedding)
        if anomaly_result.is_anomaly:
            issues.append(f"Embedding anomaly detected: score={anomaly_result.anomaly_score:.2f}")
            issues.extend(anomaly_result.details)
        
        # Check query text for injection
        injection_patterns = [
            r"ignore\s+(?:all\s+)?previous",
            r"inject\s+(?:malicious|poison)",
            r"DROP\s+TABLE",
            r"__import__",
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, query_text, re.IGNORECASE):
                issues.append("Potential injection in query text")
                break
        
        return len(issues) == 0, issues
    
    def log_query(
        self,
        user_id: str,
        query_text: str,
        results_count: int,
        latency_ms: float
    ) -> None:
        """Log query for monitoring and anomaly detection."""
        logger.info(
            "RAG_QUERY",
            extra={
                "user_id": user_id,
                "query_preview": query_text[:100],
                "results_count": results_count,
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    def get_rate_limit_status(self, user_id: str) -> Dict[str, int]:
        """Get current rate limit status for user."""
        now = time.time()
        window_start = now - self.rate_window_seconds
        
        if user_id not in self._query_log:
            return {"queries_remaining": self.max_query_rate, "window_seconds": self.rate_window_seconds}
        
        recent_queries = sum(1 for ts in self._query_log[user_id] if ts > window_start)
        return {
            "queries_remaining": max(0, self.max_query_rate - recent_queries),
            "queries_used": recent_queries,
            "window_seconds": self.rate_window_seconds,
        }


# ─── Singleton instances ───────────────────────────────────────────────────────

_document_validator: Optional[DocumentValidator] = None
_vector_security: Optional[VectorDatabaseSecurity] = None


def get_document_validator() -> DocumentValidator:
    """Get singleton document validator instance."""
    global _document_validator
    if _document_validator is None:
        _document_validator = DocumentValidator()
    return _document_validator


def get_vector_security() -> VectorDatabaseSecurity:
    """Get singleton vector security instance."""
    global _vector_security
    if _vector_security is None:
        _vector_security = VectorDatabaseSecurity()
    return _vector_security


# ─── Convenience functions ─────────────────────────────────────────────────────

def validate_rag_document(
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    source_url: Optional[str] = None
) -> DocumentValidationResult:
    """
    Validate a document before RAG ingestion.
    
    Args:
        content: Document text content
        metadata: Optional metadata
        source_url: Optional source URL
    
    Returns:
        DocumentValidationResult
    """
    validator = get_document_validator()
    return validator.validate_document(content, metadata, source_url)


def check_vector_query_permission(user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if user can query vector database.
    
    Args:
        user_id: User identifier
    
    Returns:
        Tuple of (allowed, reason_if_denied)
    """
    security = get_vector_security()
    return security.check_query_permission(user_id)


def validate_query_embedding(
    embedding: List[float],
    query_text: str
) -> Tuple[bool, List[str]]:
    """
    Validate embedding before vector search.
    
    Args:
        embedding: Query embedding vector
        query_text: Original query text
    
    Returns:
        Tuple of (is_valid, issues)
    """
    security = get_vector_security()
    return security.validate_query_embedding(embedding, query_text)