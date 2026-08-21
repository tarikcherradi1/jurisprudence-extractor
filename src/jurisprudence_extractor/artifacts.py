from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .anonymize import AnonymizationResult
from .models import JudicialDecision


@dataclass(frozen=True)
class ArtifactObject:
    name: str
    data: bytes
    content_type: str
    sha256: str


@dataclass(frozen=True)
class DecisionArtifacts:
    decision_id: str
    objects: tuple[ArtifactObject, ...]
    requires_human_review: bool


def _object(name: str, text: str, content_type: str) -> ArtifactObject:
    data = text.encode("utf-8")
    return ArtifactObject(name, data, content_type, hashlib.sha256(data).hexdigest())


def _decision_id(decision: JudicialDecision) -> str:
    identity = f"{decision.source}|{decision.source_id or decision.stable_key}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def build_artifacts(
    original: JudicialDecision,
    anonymized: AnonymizationResult,
    raw_payload: dict[str, object],
) -> DecisionArtifacts:
    decision = anonymized.decision
    decision_id = _decision_id(original)
    year = str(decision.decision_date.year) if decision.decision_date else "unknown"
    base = f"{decision.source}/{year}/{decision_id}"

    metadata = decision.model_dump(mode="json", exclude={"text", "summary"})
    metadata.update(
        decision_id=decision_id,
        original_content_sha256=original.content_sha256,
        requires_human_review=anonymized.requires_human_review,
    )
    markdown = "\n".join(
        [
            "---",
            f'decision_id: "{decision_id}"',
            f'source: "{decision.source}"',
            f'decision_number: {json.dumps(decision.decision_number, ensure_ascii=False)}',
            f'case_number: {json.dumps(decision.case_number, ensure_ascii=False)}',
            f'date: {json.dumps(decision.decision_date.isoformat() if decision.decision_date else None)}',
            f'chamber: {json.dumps(decision.chamber, ensure_ascii=False)}',
            f'anonymization_status: "{decision.anonymization_status}"',
            f"requires_human_review: {str(anonymized.requires_human_review).lower()}",
            "---",
            "",
            f"# Décision {decision.decision_number or decision_id}",
            "",
            decision.text,
            "",
        ]
    )

    objects = (
        _object(
            f"raw/{base}.json",
            json.dumps(raw_payload, ensure_ascii=False, indent=2),
            "application/json; charset=utf-8",
        ),
        _object(f"normalized/{base}.md", markdown, "text/markdown; charset=utf-8"),
        _object(
            f"metadata/{base}.json",
            json.dumps(metadata, ensure_ascii=False, indent=2),
            "application/json; charset=utf-8",
        ),
    )
    return DecisionArtifacts(decision_id, objects, anonymized.requires_human_review)


def write_artifacts(root: str | Path, bundle: DecisionArtifacts) -> None:
    root_path = Path(root)
    root_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    for item in bundle.objects:
        destination = root_path / item.name
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        destination.write_bytes(item.data)


def manifest_entry(bundle: DecisionArtifacts) -> dict[str, object]:
    return {
        "decision_id": bundle.decision_id,
        "requires_human_review": bundle.requires_human_review,
        "objects": [
            {"name": item.name, "sha256": item.sha256, "bytes": len(item.data)}
            for item in bundle.objects
        ],
    }
