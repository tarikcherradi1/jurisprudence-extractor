from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SHA256_NAME = re.compile(r"^[0-9a-f]{64}$")
EXTRACTOR_VERSION = "v2"


@dataclass(frozen=True)
class PdfMarkdownResult:
    source_pdf: str
    source_sha256: str
    markdown_path: str
    extraction_path: str
    extraction_method: str
    pages: int
    characters: int


def _require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required command is unavailable: {name}")


def _pdftotext(pdf_path: Path) -> list[str]:
    _require_command("pdftotext")
    completed = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        check=True,
        capture_output=True,
    )
    text = completed.stdout.decode("utf-8", errors="replace")
    return _split_pdf_text(text)


def _split_pdf_text(text: str) -> list[str]:
    pages = [page.rstrip() for page in text.split("\f")]
    # pdftotext emits one terminal form feed after the final physical page.
    # Remove that delimiter only; preserve any preceding blank physical pages.
    if pages and not pages[-1].strip():
        pages.pop()
    return pages or [""]


def _character_count(pages: list[str]) -> int:
    return sum(len(re.sub(r"\s+", "", page)) for page in pages)


def _ocr_pdf(source: Path, destination: Path) -> None:
    _require_command("ocrmypdf")
    subprocess.run(
        [
            "ocrmypdf",
            "--skip-text",
            "--deskew",
            "--rotate-pages",
            "--language",
            "ara+fra+eng",
            str(source),
            str(destination),
        ],
        check=True,
        capture_output=True,
    )


def _markdown_document(
    pages: list[str], metadata: dict[str, Any], source_sha256: str, method: str
) -> str:
    title = str(metadata.get("title") or f"Décision judiciaire {source_sha256[:12]}").strip()
    source_url = metadata.get("source_url")
    character_count = _character_count(pages)
    requires_review = method == "ocr" or metadata.get("publication_status") != "official"
    header = [
        "---",
        f"source_pdf_sha256: {source_sha256}",
        f"source_url: {json.dumps(source_url, ensure_ascii=False)}",
        f"extraction_method: {method}",
        f"extractor_version: {EXTRACTOR_VERSION}",
        f"requires_human_review: {str(requires_review).lower()}",
        f"pages: {len(pages)}",
        f"characters: {character_count}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    body: list[str] = []
    for page_number, page in enumerate(pages, start=1):
        body.extend([f"## Page {page_number}", "", page.strip(), ""])
    return "\n".join(header + body).rstrip() + "\n"


def _metadata_for_pdf(corpus_root: Path, relative_pdf: Path) -> dict[str, Any]:
    metadata_path = corpus_root / "metadata" / relative_pdf.with_suffix(".json")
    if not metadata_path.is_file():
        return {}
    loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(f"PDF metadata is not an object: {metadata_path}")
    return loaded


def extract_pdf_markdown(
    corpus_root: str | Path,
    output_root: str | Path | None = None,
    *,
    limit: int | None = None,
    enable_ocr: bool = True,
    minimum_characters_per_page: int = 40,
    bucket: str | None = None,
    prefix: str = "jurisprudence",
) -> list[PdfMarkdownResult]:
    corpus = Path(corpus_root)
    pdf_root = corpus / "raw" / "pdf" if (corpus / "raw" / "pdf").is_dir() else corpus
    destination_root = Path(output_root) if output_root else corpus
    pdf_paths = sorted(pdf_root.rglob("*.pdf"))
    if limit is not None:
        pdf_paths = pdf_paths[:limit]

    gcs = None
    if bucket:
        from .gcs import GCSObjectStore

        gcs = GCSObjectStore(bucket, prefix)

    results: list[PdfMarkdownResult] = []
    for pdf_path in pdf_paths:
        source_data = pdf_path.read_bytes()
        source_sha256 = hashlib.sha256(source_data).hexdigest()
        if SHA256_NAME.fullmatch(pdf_path.stem) and pdf_path.stem != source_sha256:
            raise ValueError(f"PDF filename does not match its SHA-256: {pdf_path}")

        relative_pdf = pdf_path.relative_to(pdf_root)
        metadata = _metadata_for_pdf(corpus, relative_pdf)
        pages = _pdftotext(pdf_path)
        method = "native"
        threshold = minimum_characters_per_page * len(pages)
        if enable_ocr and _character_count(pages) < threshold:
            with tempfile.TemporaryDirectory(prefix="jurisprudence-ocr-") as temp_dir:
                ocr_pdf = Path(temp_dir) / "ocr.pdf"
                _ocr_pdf(pdf_path, ocr_pdf)
                ocr_pages = _pdftotext(ocr_pdf)
                if _character_count(ocr_pages) > _character_count(pages):
                    pages = ocr_pages
                    method = "ocr"

        relative_stem = relative_pdf.with_suffix("")
        markdown_path = (
            destination_root
            / "derived"
            / "md"
            / EXTRACTOR_VERSION
            / relative_stem.with_suffix(".md")
        )
        extraction_path = (
            destination_root
            / "derived"
            / "extraction"
            / EXTRACTOR_VERSION
            / relative_stem.with_suffix(".json")
        )
        markdown_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        extraction_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        markdown = _markdown_document(pages, metadata, source_sha256, method)
        markdown_bytes = markdown.encode("utf-8")
        extraction = {
            "source_pdf": str(relative_pdf),
            "source_sha256": source_sha256,
            "markdown": str(markdown_path.relative_to(destination_root)),
            "extraction_method": method,
            "extractor_version": EXTRACTOR_VERSION,
            "requires_human_review": (
                method == "ocr" or metadata.get("publication_status") != "official"
            ),
            "pages": len(pages),
            "characters": _character_count(pages),
        }
        extraction_bytes = json.dumps(extraction, ensure_ascii=False, indent=2).encode("utf-8")
        if not markdown_path.exists():
            markdown_path.write_bytes(markdown_bytes)
        if not extraction_path.exists():
            extraction_path.write_bytes(extraction_bytes)

        markdown_name = str(markdown_path.relative_to(destination_root))
        extraction_name = str(extraction_path.relative_to(destination_root))
        if gcs:
            requires_review = (
                method == "ocr" or metadata.get("publication_status") != "official"
            )
            object_metadata = {
                "source-sha256": source_sha256,
                "extraction-method": method,
                "requires-human-review": str(requires_review).lower(),
            }
            gcs.upload_bytes(markdown_name, markdown_bytes, "text/markdown", object_metadata)
            gcs.upload_bytes(
                extraction_name, extraction_bytes, "application/json", object_metadata
            )

        results.append(
            PdfMarkdownResult(
                source_pdf=str(pdf_path),
                source_sha256=source_sha256,
                markdown_path=str(markdown_path),
                extraction_path=str(extraction_path),
                extraction_method=method,
                pages=len(pages),
                characters=_character_count(pages),
            )
        )

    manifest_path = destination_root / "manifests" / "pdf_markdown.jsonl"
    manifest_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    manifest_path.write_text(
        "".join(json.dumps(asdict(item), ensure_ascii=False) + "\n" for item in results),
        encoding="utf-8",
    )
    return results
