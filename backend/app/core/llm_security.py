"""
LLM Security Module - OWASP LLM Top 10 Protections
====================================================

This module provides security protections for LLM interactions:

1. LLM01 - Prompt Injection Protection
2. LLM05 - Improper Output Handling
3. LLM07 - System Prompt Protection
4. LLM09 - Hallucination Detection
"""
from __future__ import annotations

import logging
import re
import secrets
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ─── Prompt Injection Patterns (LLM01) ─────────────────────────────────────────

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|rules)",
    r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|rules)",
    r"forget\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|rules)",
    r"you\s+are\s+now\s+(a|an)\s+\w+",
    r"act\s+as\s+(if|a|an)",
    r"pretend\s+(to\s+be|that\s+you\s+are)",
    r"what\s+(is|are)\s+(your|the)\s+(system|original)\s+(prompt|instructions)",
    r"repeat\s+(your|the)\s+(system|original)\s+(prompt|instructions)",
    r"show\s+me\s+(your|the)\s+(system|original)\s+(prompt|instructions)",
    r"print\s+(your|the)\s+(system|original)\s+(prompt|instructions)",
    r"---+\s*(system|admin|user)\s*---+",
    r"\[\[(system|admin|user)\]\]",
    r"<\|.*?\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"override\s+(all\s+)?(previous|safety|security)",
    r"bypass\s+(all\s+)?(restrictions|filters|safety)",
    r"DAN\s+(Do Anything Now)",
    r"developer\s+mode",
    r"jailbreak",
]

RAG_DANGEROUS_PATTERNS = [
    r"ignore\s+(all\s+)?previous",
    r"disregard\s+(all\s+)?instructions",
    r"execute\s+arbitrary\s+code",
    r"eval\s*\(",
    r"exec\s*\(",
    r"subprocess\.",
]


class SecurityAction(str, Enum):
    """Actions to take when security issue detected."""
    ALLOW = "allow"
    SANITIZE = "sanitize"
    BLOCK = "block"
    ALERT = "alert"


@dataclass
class SecurityCheckResult:
    """Result of a security check."""
    safe: bool
    action: SecurityAction
    original_content: str
    sanitized_content: Optional[str] = None
    issues: List[str] = None
    confidence: float = 1.0
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class PromptSecurityScanner:
    """Scans prompts for injection attempts. Addresses LLM01."""
    
    def __init__(self):
        self.injection_patterns = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]
        self.rag_patterns = [re.compile(p, re.IGNORECASE) for p in RAG_DANGEROUS_PATTERNS]
    
    def scan_user_prompt(self, prompt: str) -> SecurityCheckResult:
        """Scan user prompt for injection attempts."""
        issues = []
        
        for pattern in self.injection_patterns:
            if pattern.search(prompt):
                issues.append("Injection pattern detected: " + pattern.pattern[:40])
        
        if issues:
            sanitized = self._sanitize_prompt(prompt)
            return SecurityCheckResult(
                safe=False,
                action=SecurityAction.SANITIZE,
                original_content=prompt,
                sanitized_content=sanitized,
                issues=issues,
                confidence=0.9
            )
        
        return SecurityCheckResult(
            safe=True,
            action=SecurityAction.ALLOW,
            original_content=prompt,
        )
    
    def scan_rag_content(self, content: str) -> SecurityCheckResult:
        """Scan RAG content for malicious patterns."""
        issues = []
        
        for pattern in self.rag_patterns:
            if pattern.search(content):
                issues.append("Malicious pattern in RAG: " + pattern.pattern[:40])
        
        if issues:
            sanitized = self._sanitize_rag_content(content)
            action = SecurityAction.SANITIZE if len(issues) <= 2 else SecurityAction.BLOCK
            return SecurityCheckResult(
                safe=False,
                action=action,
                original_content=content,
                sanitized_content=sanitized,
                issues=issues,
                confidence=0.85
            )
        
        return SecurityCheckResult(
            safe=True,
            action=SecurityAction.ALLOW,
            original_content=content,
        )
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """Remove or escape injection patterns."""
        sanitized = prompt
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        sanitized = re.sub(r'(ignore|disregard|forget)', '[REDACTED]', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'[-=]{3,}', '---', sanitized)
        return sanitized
    
    def _sanitize_rag_content(self, content: str) -> str:
        """Sanitize RAG content."""
        sanitized = content
        sanitized = re.sub(r'(eval|exec|subprocess)\s*[\(\.].*?', '[CODE_REMOVED]', sanitized)
        sanitized = re.sub(r'(ignore|disregard)\s+(all\s+)?(previous|instructions)', '[REDACTED]', sanitized, flags=re.IGNORECASE)
        return sanitized


class OutputValidator:
    """Validates LLM outputs. Addresses LLM05."""
    
    VALID_ACTIONS = {"buy", "sell", "hold"}
    VALID_REGIMES = {"trending_up", "trending_down", "ranging", "volatile", "unknown"}
    MAX_AMOUNT_USD = 1000000.0
    
    def validate_planner_output(self, output: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Validate planner output against schema and bounds."""
        errors = []
        corrected = output.copy()
        
        action = output.get("action", "").lower()
        if action not in self.VALID_ACTIONS:
            errors.append("Invalid action, defaulting to hold")
            corrected["action"] = "hold"
        
        try:
            amount = float(output.get("amount", 0))
            if amount < 0:
                errors.append("Negative amount, setting to 0")
                corrected["amount"] = 0
            elif amount > self.MAX_AMOUNT_USD:
                errors.append("Amount exceeds max, capping")
                corrected["amount"] = self.MAX_AMOUNT_USD
        except (ValueError, TypeError):
            errors.append("Invalid amount, setting to 0")
            corrected["amount"] = 0
        
        try:
            confidence = float(output.get("confidence", 0))
            if not (0 <= confidence <= 1):
                corrected["confidence"] = max(0, min(1, confidence))
        except (ValueError, TypeError):
            corrected["confidence"] = 0
        
        try:
            risk = float(output.get("risk_score", 1))
            if not (0 <= risk <= 1):
                corrected["risk_score"] = max(0, min(1, risk))
        except (ValueError, TypeError):
            corrected["risk_score"] = 1
        
        regime = output.get("market_regime", "").lower()
        if regime not in self.VALID_REGIMES:
            corrected["market_regime"] = "unknown"
        
        return len(errors) == 0, errors, corrected
    
    def validate_controller_output(self, output: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Validate controller output."""
        errors = []
        corrected = output.copy()
        
        if not isinstance(output.get("approved"), bool):
            errors.append("approved must be boolean, defaulting to False")
            corrected["approved"] = False
        
        action = output.get("final_action", "").lower()
        if action not in self.VALID_ACTIONS:
            errors.append("Invalid final_action, defaulting to hold")
            corrected["final_action"] = "hold"
        
        try:
            amount = float(output.get("final_amount", 0))
            if amount < 0:
                corrected["final_amount"] = 0
            elif amount > self.MAX_AMOUNT_USD:
                corrected["final_amount"] = self.MAX_AMOUNT_USD
        except (ValueError, TypeError):
            corrected["final_amount"] = 0
        
        return len(errors) == 0, errors, corrected


class HallucinationDetector:
    """Detects hallucinations. Addresses LLM09."""
    
    HALLUCINATION_INDICATORS = [
        r"according\s+to\s+(my|the)\s+(training|data)",
        r"I\s+(was|am)\s+(trained|programmed)",
        r"my\s+knowledge\s+cutoff",
        r"I\s+(don't|do\s+not)\s+have\s+(access|information)",
    ]
    
    VAGUE_PATTERNS = [
        r"(it\s+seems|appears|looks\s+like)",
        r"(possibly|probably|maybe|might)",
    ]
    
    def __init__(self, confidence_threshold: float = 0.6):
        self.confidence_threshold = confidence_threshold
        self.hallucination_patterns = [re.compile(p, re.IGNORECASE) for p in self.HALLUCINATION_INDICATORS]
        self.vague_patterns = [re.compile(p, re.IGNORECASE) for p in self.VAGUE_PATTERNS]
    
    def detect_hallucination(self, reasoning: str, claimed_sources: List[str], 
                             available_sources: List[str]) -> Tuple[bool, float, List[str]]:
        """Detect potential hallucinations in LLM reasoning."""
        issues = []
        score = 0.0
        
        for pattern in self.hallucination_patterns:
            if pattern.search(reasoning):
                score += 0.2
                issues.append("Hallucination indicator: " + pattern.pattern[:30])
        
        for source in claimed_sources:
            if source not in available_sources and not source.startswith("doc_"):
                score += 0.3
                issues.append("Potentially fabricated source: " + source)
        
        vague_count = sum(1 for p in self.vague_patterns if p.search(reasoning))
        if vague_count > 3:
            score += 0.1 * (vague_count - 3)
        
        return score > 0.3, min(1.0, score), issues


class SystemPromptProtector:
    """Protects system prompts. Addresses LLM07."""
    
    def __init__(self):
        self._canary_tokens: Dict[str, str] = {}
    
    def generate_canary_token(self, prompt_id: str) -> str:
        """Generate a unique canary token."""
        token = "CANARY_" + secrets.token_hex(8)
        self._canary_tokens[prompt_id] = token
        return token
    
    def inject_canary(self, system_prompt: str, prompt_id: str) -> str:
        """Inject canary token into system prompt."""
        token = self.generate_canary_token(prompt_id)
        return system_prompt + "\n\n<!-- Integrity: " + token + " -->"
    
    def check_canary_leak(self, output: str) -> bool:
        """Check if canary token appears in output."""
        for prompt_id, token in self._canary_tokens.items():
            if token in output:
                logger.warning("CANARY LEAK DETECTED", extra={"prompt_id": prompt_id})
                return True
        return False


# ─── Singleton instances ─────────────────────────────────────────────────────

_scanner: Optional[PromptSecurityScanner] = None
_validator: Optional[OutputValidator] = None
_hallucination_detector: Optional[HallucinationDetector] = None
_prompt_protector: Optional[SystemPromptProtector] = None


def get_scanner() -> PromptSecurityScanner:
    """Get singleton scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = PromptSecurityScanner()
    return _scanner


def get_validator() -> OutputValidator:
    """Get singleton validator instance."""
    global _validator
    if _validator is None:
        _validator = OutputValidator()
    return _validator


def get_hallucination_detector() -> HallucinationDetector:
    """Get singleton hallucination detector instance."""
    global _hallucination_detector
    if _hallucination_detector is None:
        _hallucination_detector = HallucinationDetector()
    return _hallucination_detector


def get_prompt_protector() -> SystemPromptProtector:
    """Get singleton prompt protector instance."""
    global _prompt_protector
    if _prompt_protector is None:
        _prompt_protector = SystemPromptProtector()
    return _prompt_protector


def secure_user_prompt(prompt: str) -> Tuple[str, bool]:
    """Sanitize user prompt for injection attempts."""
    scanner = get_scanner()
    result = scanner.scan_user_prompt(prompt)
    
    if not result.safe:
        logger.warning("Prompt injection attempt detected", extra={"issues": result.issues})
        return result.sanitized_content or result.original_content, True
    
    return result.original_content, False


def secure_rag_content(content: str) -> Tuple[str, bool]:
    """Sanitize RAG content for malicious patterns."""
    scanner = get_scanner()
    result = scanner.scan_rag_content(content)
    
    if not result.safe:
        logger.warning("Malicious RAG content detected", extra={"issues": result.issues})
        if result.action == SecurityAction.BLOCK:
            return "[CONTENT BLOCKED FOR SECURITY]", True
        return result.sanitized_content or result.original_content, True
    
    return result.original_content, False


def validate_llm_trade_output(output: Dict[str, Any], role: str = "planner") -> Dict[str, Any]:
    """Validate and correct LLM trade output."""
    validator = get_validator()
    
    if role == "planner":
        valid, errors, corrected = validator.validate_planner_output(output)
    elif role == "controller":
        valid, errors, corrected = validator.validate_controller_output(output)
    else:
        return output
    
    if errors:
        logger.warning("LLM output validation issues for " + role, extra={"errors": errors})
    
    return corrected


def check_hallucination(reasoning: str, claimed_sources: List[str], 
                        available_sources: List[str]) -> Tuple[bool, List[str]]:
    """Check for hallucination in LLM reasoning."""
    detector = get_hallucination_detector()
    has_hall, score, issues = detector.detect_hallucination(reasoning, claimed_sources, available_sources)
    
    if has_hall:
        logger.warning("Potential hallucination detected", extra={"score": score, "issues": issues})
    
    return has_hall, issues