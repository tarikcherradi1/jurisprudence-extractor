from __future__ import annotations

import argparse
import json
import logging

from .anonymize import anonymize_decision
from .audit import audit_corpus
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
        ],
    )
    parser.add_argument("--database", default="jurisprudence.sqlite3")
    parser.add_argument("--limit", type=int)
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
