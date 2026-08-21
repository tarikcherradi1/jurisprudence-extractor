from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .anonymize import anonymize_decision
from .artifacts import build_artifacts, manifest_entry, write_artifacts
from .audit import audit_corpus
from .huggingface_audit import fetch_dataset_audit
from .pdf_sources import (
    ConstitutionalCourtPdfSource,
    MarocDroitPdfSource,
    write_pdf_assets,
)
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
            "constitutional-pdfs",
            "marocdroit-pdfs",
            "crawl-pdfs",
            "pdf-to-markdown",
        ],
    )
    parser.add_argument("--database", default="jurisprudence.sqlite3")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-dir")
    parser.add_argument("--input-jsonl", help="local published Hugging Face JSONL file")
    parser.add_argument("--bucket", help="existing private Google Cloud Storage bucket")
    parser.add_argument("--prefix", default="jurisprudence")
    parser.add_argument(
        "--pdf-source",
        choices=["constitutional", "marocdroit", "marocdroit-search"],
        help="source spider used by crawl-pdfs",
    )
    parser.add_argument("--job-dir", help="Scrapy state directory used to pause and resume")
    parser.add_argument("--input-dir", help="local PDF corpus root for pdf-to-markdown")
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="disable OCR fallback for image-only PDF pages",
    )
    parser.add_argument(
        "--browser-fallback",
        action="store_true",
        help="enable the Playwright download handler for source requests marked as JavaScript",
    )
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
    output_dir = args.output_dir or "corpus-pilot"

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
            write_artifacts(output_dir, bundle)
            manifest.append(manifest_entry(bundle))
            review += int(bundle.requires_human_review)
            if uploader:
                new_count, existing_count = uploader.upload(bundle)
                uploaded += new_count
                existing += existing_count
        manifest_path = Path(output_dir) / "manifests" / "opendatamoroccanlaw.jsonl"
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
    if args.source == "constitutional-pdfs":
        assets = list(ConstitutionalCourtPdfSource().iter_pdfs(limit=args.limit))
        manifest_path = write_pdf_assets(output_dir, assets)
        print(
            f"pdfs={len(assets)} bytes={sum(len(asset.data) for asset in assets)} "
            f"manifest={manifest_path}"
        )
        return
    if args.source == "marocdroit-pdfs":
        assets = list(MarocDroitPdfSource().iter_pdfs(limit=args.limit))
        manifest_path = write_pdf_assets(output_dir, assets, collection="marocdroit")
        print(
            f"pdfs={len(assets)} bytes={sum(len(asset.data) for asset in assets)} "
            f"manifest={manifest_path}"
        )
        return
    if args.source == "crawl-pdfs":
        if not args.pdf_source:
            parser.error("--pdf-source is required for crawl-pdfs")
        from .scrapy_crawler import run_pdf_crawl

        run_pdf_crawl(
            source=args.pdf_source,
            output_dir=output_dir,
            bucket=args.bucket,
            prefix=args.prefix,
            job_dir=args.job_dir,
            limit=args.limit,
            browser_fallback=args.browser_fallback,
        )
        return
    if args.source == "pdf-to-markdown":
        if not args.input_dir:
            parser.error("--input-dir is required for pdf-to-markdown")
        from .pdf_markdown import extract_pdf_markdown

        results = extract_pdf_markdown(
            corpus_root=args.input_dir,
            output_root=args.output_dir or args.input_dir,
            limit=args.limit,
            enable_ocr=not args.no_ocr,
            bucket=args.bucket,
            prefix=args.prefix,
        )
        print(
            f"pdfs={len(results)} pages={sum(item.pages for item in results)} "
            f"characters={sum(item.characters for item in results)} "
            f"ocr={sum(item.extraction_method == 'ocr' for item in results)}"
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
