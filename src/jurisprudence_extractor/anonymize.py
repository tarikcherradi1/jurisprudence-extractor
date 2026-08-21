from __future__ import annotations

import re
from dataclasses import dataclass

from .models import JudicialDecision


@dataclass(frozen=True)
class AnonymizationResult:
    decision: JudicialDecision
    redaction_count: int
    requires_human_review: bool


_RULES = (
    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", re.UNICODE), "[EMAIL_MASQUE]"),
    (re.compile(r"(?<!\d)(?:\+212|0)[5-7]\d{8}(?!\d)"), "[TELEPHONE_MASQUE]"),
    (
        re.compile(
            r"(?i)(?P<label>\b(?:cin|c\.i\.n\.?|بطاقة\s+التعريف)\s*(?:n[°o]?|رقم)?\s*[:：-]?\s*)"
            r"[A-Z]{1,2}\s*\d{4,8}"
        ),
        r"\g<label>[CIN_MASQUEE]",
    ),
)

_REVIEW_SIGNALS = re.compile(
    r"(?i)\b(?:mineur|mineure|victime|adresse|domicili[ée]|nom\s+complet)\b|"
    r"(?:قاصر|ضحية|العنوان|الساكن(?:ة)?)"
)


def _redact(text: str) -> tuple[str, int]:
    count = 0
    for pattern, replacement in _RULES:
        text, matches = pattern.subn(replacement, text)
        count += matches
    return text, count


def anonymize_decision(decision: JudicialDecision) -> AnonymizationResult:
    """Redact high-confidence identifiers; never claim that names are detected safely."""
    text, text_count = _redact(decision.text)
    summary = decision.summary
    summary_count = 0
    if summary:
        summary, summary_count = _redact(summary)

    requires_review = bool(_REVIEW_SIGNALS.search(decision.text))
    total = text_count + summary_count
    payload = decision.model_dump()
    payload.update(
        text=text,
        summary=summary,
        content_sha256="",
        anonymization_status="automatic",
        redaction_count=total,
    )
    sanitized = JudicialDecision.model_validate(payload).with_fingerprint()
    return AnonymizationResult(sanitized, total, requires_review)
