"""PII detection and stripping for memory consolidation.

Uses regex-based detection — same philosophy as Claude Code's regex
sentiment analysis: deterministic, zero latency, zero LLM cost.
Applied during the Dream Cycle's Consolidate phase before embedding.
"""

import re

import structlog

logger = structlog.get_logger()

# Patterns for common PII types
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE_PATTERN = re.compile(
    r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
_SSN_PATTERN = re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")
_CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
_IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": _EMAIL_PATTERN,
    "phone": _PHONE_PATTERN,
    "ssn": _SSN_PATTERN,
    "credit_card": _CREDIT_CARD_PATTERN,
    "ip_address": _IP_PATTERN,
}

_REPLACEMENT_MAP: dict[str, str] = {
    "email": "[EMAIL_REDACTED]",
    "phone": "[PHONE_REDACTED]",
    "ssn": "[SSN_REDACTED]",
    "credit_card": "[CC_REDACTED]",
    "ip_address": "[IP_REDACTED]",
}


def detect_pii(text: str) -> dict[str, list[str]]:
    """Detect PII patterns in text.

    Returns dict of PII type → list of matched strings.
    """
    found: dict[str, list[str]] = {}
    for pii_type, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            found[pii_type] = matches
    return found


def strip_pii(text: str, enabled: bool = True) -> tuple[str, dict[str, int]]:
    """Strip PII from text, returning cleaned text and redaction counts.

    Args:
        text: Input text to clean.
        enabled: If False, returns text unchanged (for orgs that opt out).

    Returns:
        Tuple of (cleaned_text, {pii_type: count_redacted}).
    """
    if not enabled:
        return text, {}

    redaction_counts: dict[str, int] = {}
    cleaned = text

    for pii_type, pattern in _PII_PATTERNS.items():
        replacement = _REPLACEMENT_MAP[pii_type]
        matches = pattern.findall(cleaned)
        if matches:
            redaction_counts[pii_type] = len(matches)
            cleaned = pattern.sub(replacement, cleaned)

    if redaction_counts:
        logger.info("pii.stripped", redactions=redaction_counts)

    return cleaned, redaction_counts


def has_pii(text: str) -> bool:
    """Quick check if text contains any PII patterns."""
    return bool(detect_pii(text))
