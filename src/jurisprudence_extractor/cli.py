from __future__ import annotations

import argparse
import logging

from .sources import ConstitutionalCourtSource, HuggingFaceDatasetSource
from .storage import DecisionStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest public Moroccan case law")
    parser.add_argument(
        "source",
        choices=["constitutional-court", "huggingface-cassation"],
    )
    parser.add_argument("--database", default="jurisprudence.sqlite3")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    source = (
        ConstitutionalCourtSource()
        if args.source == "constitutional-court"
        else HuggingFaceDatasetSource()
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
