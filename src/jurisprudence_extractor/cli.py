from __future__ import annotations

import argparse
import logging

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
        ],
    )
    parser.add_argument("--database", default="jurisprudence.sqlite3")
    parser.add_argument("--limit", type=int)
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
    with DecisionStore(args.database) as store:
        for decision in source.iter_decisions(limit=args.limit):
            if store.save(decision):
                inserted += 1
            else:
                duplicates += 1
    print(f"inserted={inserted} duplicates={duplicates}")
