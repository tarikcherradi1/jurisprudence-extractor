from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .sources import PublicHttpClient


@dataclass(frozen=True)
class PdfAsset:
    source_page: str
    source_url: str
    title: str
    data: bytes
    sha256: str


class ConstitutionalCourtPdfSource(PublicHttpClient):
    index_url = "https://cour-constitutionnelle.ma/Publication?CC=4&Page=Publication"
    allowed_host = "cour-constitutionnelle.ma"

    def discover(self) -> list[tuple[str, str]]:
        index = self.get(self.index_url)
        soup = BeautifulSoup(index.text, "html.parser")
        publication_pages: set[str] = set()
        for link in soup.select('a[href*="Pdf?id="]'):
            publication_pages.add(urljoin(self.index_url, str(link.get("href"))))

        discovered: dict[str, str] = {}
        for page_url in sorted(publication_pages):
            page = self.get(page_url)
            page_soup = BeautifulSoup(page.text, "html.parser")
            title_node = page_soup.select_one(".pdf-container .title, .article-content")
            title = title_node.get_text(" ", strip=True) if title_node else "Recueil de décisions"
            for link in page_soup.select('a[href$=".pdf"], iframe[src$=".pdf"]'):
                href = link.get("href") or link.get("src")
                if not href:
                    continue
                pdf_url = urljoin(page_url, str(href))
                if urlparse(pdf_url).hostname != self.allowed_host:
                    continue
                discovered[pdf_url] = title
        return sorted(discovered.items())

    def iter_pdfs(self, limit: int | None = None):
        for index, (url, title) in enumerate(self.discover()):
            if limit is not None and index >= limit:
                return
            response = self.get(url)
            data = response.content
            if not data.startswith(b"%PDF-"):
                raise ValueError(f"Public document is not a valid PDF: {url}")
            yield PdfAsset(
                source_page=self.index_url,
                source_url=url,
                title=title,
                data=data,
                sha256=hashlib.sha256(data).hexdigest(),
            )


class MarocDroitPdfSource(PublicHttpClient):
    """Secondary public PDFs discovered on robots-allowed attachment routes."""

    seed_urls = (
        "https://www.marocdroit.com/attachment/2741595/",
        "https://www.marocdroit.com/attachment/2748822/",
        "https://www.marocdroit.com/attachment/2573277/",
        "https://www.marocdroit.com/attachment/2741643/",
    )

    def iter_pdfs(self, limit: int | None = None):
        for index, url in enumerate(self.seed_urls):
            if limit is not None and index >= limit:
                return
            response = self.get(url)
            data = response.content
            if not data.startswith(b"%PDF-"):
                raise ValueError(f"Public attachment is not a valid PDF: {url}")
            yield PdfAsset(
                source_page=url,
                source_url=url,
                title=f"Décision judiciaire publiée par MarocDroit ({url.rstrip('/').rsplit('/', 1)[-1]})",
                data=data,
                sha256=hashlib.sha256(data).hexdigest(),
            )


def write_pdf_assets(
    root: str | Path, assets: list[PdfAsset], collection: str = "cour_constitutionnelle"
) -> Path:
    root_path = Path(root)
    pdf_root = root_path / "pdf" / collection
    pdf_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    manifest_path = root_path / "manifests" / f"{collection}_pdfs.jsonl"
    manifest_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    entries = []
    for asset in assets:
        filename = f"{asset.sha256[:24]}.pdf"
        destination = pdf_root / filename
        destination.write_bytes(asset.data)
        entries.append(
            {
                "filename": filename,
                "title": asset.title,
                "source_page": asset.source_page,
                "source_url": asset.source_url,
                "bytes": len(asset.data),
                "sha256": asset.sha256,
            }
        )
    manifest_path.write_text(
        "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries),
        encoding="utf-8",
    )
    return manifest_path
