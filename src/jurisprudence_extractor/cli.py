from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .anonymize import anonymize_decision
from .artifacts import build_artifacts, manifest_entry, write_artifacts
from .audit import audit_corpus
from .huggingface_audit import fetch_dataset_audit
from .sources import (
    ConstitutionalCourtSource,
    HuggingFaceDatasetSource,
    JuriscassationMetadataSource,
)
from .storage import DecisionStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest public Moroccan case law")
    parser.add_argument(
        "source",
        choices=[
            "constitutional-court",
            "huggingface-cassation",
            "juriscassation-metadata",
            "audit",
            "huggingface-audit",
            "huggingface-export",
        ],
    )
    parser.add_argument("--database", default="jurisprudence.sqlite3")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-dir", default="corpus-pilot")
    parser.add_argument("--input-jsonl", help="local published Hugging Face JSONL file")
    parser.add_argument("--bucket", help="existing private Google Cloud Storage bucket")
    parser.add_argument("--prefix", default="jurisprudence")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="stop at the first decision already stored (newest-first sources)",
    )
    parser.add_argument(
        "--anonymize",
        action="store_true",
        help="redact high-confidence identifiers before storage",
    )
    parser.add_argument("--subject", help="Arabic/French search term (minimum 3 characters)")
    parser.add_argument(
        "--chamber",
        type=int,
        action="append",
        choices=range(1, 8),
        help="Juriscassation chamber ID; repeat to select multiple chambers",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.source == "audit":
        with DecisionStore(args.database) as store:
            print(json.dumps(audit_corpus(store.iter_all()), ensure_ascii=False, indent=2))
        return
    if args.source == "huggingface-audit":
        print(json.dumps(fetch_dataset_audit(), ensure_ascii=False, indent=2))
        return
    if args.source == "huggingface-export":
        limit = args.limit or 100
        uploader = None
        if args.bucket:
            from .gcs import GCSArtifactStore

            uploader = GCSArtifactStore(args.bucket, args.prefix)
        manifest: list[dict[str, object]] = []
        uploaded = 0
        existing = 0
        review = 0
        source = HuggingFaceDatasetSource()
        rows = (
            source.iter_jsonl(args.input_jsonl, limit=limit)
            if args.input_jsonl
            else source.iter_api_rows(limit=limit)
        )
        for raw_row, original in rows:
            anonymized = anonymize_decision(original)
            bundle = build_artifacts(original, anonymized, raw_row)
            write_artifacts(args.output_dir, bundle)
            manifest.append(manifest_entry(bundle))
            review += int(bundle.requires_human_review)
            if uploader:
                new_count, existing_count = uploader.upload(bundle)
                uploaded += new_count
                existing += existing_count
        manifest_path = Path(args.output_dir) / "manifests" / "opendatamoroccanlaw.jsonl"
        manifest_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        manifest_path.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in manifest),
            encoding="utf-8",
        )
        print(
            f"exported={len(manifest)} review={review} uploaded={uploaded} "
            f"existing={existing} manifest={manifest_path}"
        )
        return

    if args.source == "constitutional-court":
        source = ConstitutionalCourtSource()
    elif args.source == "huggingface-cassation":
        source = HuggingFaceDatasetSource()
    else:
        if not args.subject:
            parser.error("--subject is required for juriscassation-metadata")
        source = JuriscassationMetadataSource(
            subject=args.subject,
            chambers=tuple(args.chamber or range(1, 8)),
        )

    inserted = 0
    duplicates = 0
    stopped_at_existing = False
    requires_review = 0
    with DecisionStore(args.database) as store:
        for decision in source.iter_decisions(limit=args.limit):
            item_requires_review = False
            if args.anonymize:
                result = anonymize_decision(decision)
                decision = result.decision
                item_requires_review = result.requires_human_review
            if args.incremental and store.contains(decision):
                stopped_at_existing = True
                break
            if store.save(decision):
                inserted += 1
                requires_review += int(item_requires_review)
            else:
                duplicates += 1
    print(
        f"inserted={inserted} duplicates={duplicates} "
        f"stopped_at_existing={stopped_at_existing} requires_review={requires_review}"
    )
