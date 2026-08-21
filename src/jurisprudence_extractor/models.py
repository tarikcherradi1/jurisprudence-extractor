from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class JudicialDecision(BaseModel):
    """Canonical, provenance-first representation of a judicial decision."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: str = Field(min_length=2)
    source_url: HttpUrl
    source_id: str | None = None
    jurisdiction: str = Field(min_length=2)
    court: str | None = None
    chamber: str | None = None
    city: str | None = None
    decision_number: str | None = None
    case_number: str | None = None
    decision_date: date | None = None
    decision_type: str | None = None
    language: Literal["ar", "fr", "mixed", "unknown"] = "unknown"
    title: str | None = None
    summary: str | None = None
    text: str = Field(min_length=1)
    publication_status: Literal["official", "secondary", "unverified"] = "official"
    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    content_sha256: str = ""

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def with_fingerprint(self) -> "JudicialDecision":
        digest = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        return self.model_copy(update={"content_sha256": digest})

    @property
    def stable_key(self) -> str:
        raw = "|".join(
            [
                self.source,
                self.decision_number or "",
                self.case_number or "",
                self.decision_date.isoformat() if self.decision_date else "",
                self.content_sha256,
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
