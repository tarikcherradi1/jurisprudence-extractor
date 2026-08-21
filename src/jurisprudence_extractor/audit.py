from __future__ import annotations

from collections import Counter
from typing import Any

from .models import JudicialDecision


def audit_corpus(items: list[JudicialDecision]) -> dict[str, Any]:
    hashes = Counter(item.content_sha256 for item in items if item.content_sha256)
    return {
        "total": len(items),
        "by_source": dict(sorted(Counter(item.source for item in items).items())),
        "by_content_kind": dict(
            sorted(Counter(item.content_kind for item in items).items())
        ),
        "missing_decision_number": sum(not item.decision_number for item in items),
        "missing_case_number": sum(not item.case_number for item in items),
        "missing_decision_date": sum(not item.decision_date for item in items),
        "duplicate_content_hashes": sum(count - 1 for count in hashes.values()),
        "pending_anonymization": sum(
            item.anonymization_status == "pending" for item in items
        ),
    }
