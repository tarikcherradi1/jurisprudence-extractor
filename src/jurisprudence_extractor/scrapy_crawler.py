from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import quote_plus, urljoin, urlparse

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import CloseSpider, DropItem
from scrapy.http import Request

USER_AGENT = "JurisprudenceExtractor/0.1 (+public legal research; admin@lovemaroc.org)"
PROTECTED_STATUSES = {401, 403, 429}
COLLECTION_MARKERS = (
    "قضاء محكمة النقض عدد",
    "مجلة قضاء",
    "دفاتر محكمة النقض",
    "jurisprudence",
)
DECISION_MARKERS = ("قرار", "حكم", "أمر قضائي", "arrêt", "jugement", "ordonnance")
RESEARCH_MARKERS = (
    "تعليق",
    "قراءة في",
    "دراسة",
    "بحث",
    "رسالة",
    "أطروحة",
    "commentaire",
    "étude",
    "mémoire",
    "thèse",
)


def _safe_collection(value: str) -> str:
    collection = value.strip("/")
    if not collection or ".." in collection or not re.fullmatch(r"[a-z0-9/_-]+", collection):
        raise ValueError(f"Unsafe collection path: {value!r}")
    return collection


def _classify_judicial_pdf(title: str) -> str | None:
    normalized = " ".join(title.casefold().split())
    if any(marker.casefold() in normalized for marker in RESEARCH_MARKERS):
        return None
    if any(marker.casefold() in normalized for marker in COLLECTION_MARKERS):
        return "collection"
    if any(marker.casefold() in normalized for marker in DECISION_MARKERS):
        return "decision"
    return None


class PdfArchivePipeline:
    """Validate, deduplicate and archive PDFs locally and optionally in GCS."""

    def __init__(
        self,
        output_dir: str,
        bucket: str | None,
        prefix: str,
        crawler=None,
        limit: int | None = None,
    ) -> None:
        self.root = Path(output_dir)
        self.bucket_name = bucket
        self.prefix = prefix
        self.crawler = crawler
        self.gcs: Any = None
        self.seen: set[tuple[str, str]] = set()
        self.limit = limit
        self.archived = 0

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            crawler.settings.get("PDF_OUTPUT_DIR", "pdf-corpus"),
            crawler.settings.get("PDF_BUCKET"),
            crawler.settings.get("PDF_PREFIX", "jurisprudence"),
            crawler,
            crawler.settings.getint("PDF_LIMIT") or None,
        )

    def open_spider(self) -> None:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.bucket_name:
            from .gcs import GCSObjectStore

            self.gcs = GCSObjectStore(self.bucket_name, self.prefix)

    def process_item(self, item):
        if self.limit is not None and self.archived >= self.limit:
            raise DropItem("PDF archive limit reached")
        data = bytes(item["body"])
        if not data.startswith(b"%PDF-"):
            raise DropItem(f"Not a PDF: {item['source_url']}")

        collection = _safe_collection(str(item["collection"]))
        sha256 = hashlib.sha256(data).hexdigest()
        key = (collection, sha256)
        if key in self.seen:
            raise DropItem(f"Duplicate PDF in this crawl: {sha256}")
        self.seen.add(key)

        pdf_name = f"raw/pdf/{collection}/{sha256}.pdf"
        metadata_name = f"metadata/{collection}/{sha256}.json"
        metadata = {
            "title": str(item["title"]),
            "source_page": str(item["source_page"]),
            "source_url": str(item["source_url"]),
            "publication_status": str(item["publication_status"]),
            "document_kind": str(item.get("document_kind") or "decision"),
            "requires_human_review": str(item["publication_status"]) != "official",
            "bytes": len(data),
            "sha256": sha256,
            "collected_at": datetime.now(UTC).isoformat(),
        }
        metadata_bytes = json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")

        pdf_path = self.root / pdf_name
        metadata_path = self.root / metadata_name
        pdf_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        metadata_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        is_new_local = not pdf_path.exists()
        if is_new_local:
            pdf_path.write_bytes(data)
        if not metadata_path.exists():
            metadata_path.write_bytes(metadata_bytes)

        manifest_path = self.root / "manifests" / f"{collection.replace('/', '_')}.jsonl"
        manifest_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if is_new_local:
            with manifest_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        if self.gcs:
            labels = {
                "sha256": sha256,
                "publication-status": str(item["publication_status"]),
            }
            self.gcs.upload_bytes(pdf_name, data, "application/pdf", labels)
            self.gcs.upload_bytes(metadata_name, metadata_bytes, "application/json", labels)

        if self.crawler is not None:
            self.crawler.stats.inc_value("pdf/bytes", len(data))
            self.crawler.stats.inc_value("pdf/archived")
        self.archived += 1
        archived_item = {**dict(item), "sha256": sha256, "bytes": len(data)}
        archived_item.pop("body", None)
        return archived_item


class PublicPdfSpider(scrapy.Spider):
    handle_httpstatus_list: ClassVar[list[int]] = [401, 403, 429]

    def _ensure_public(self, response) -> None:
        if response.status in PROTECTED_STATUSES:
            raise CloseSpider(f"protected_or_rate_limited_{response.status}")

    def _pdf_item(
        self,
        response,
        *,
        collection: str,
        publication_status: str,
        source_page: str,
        title: str,
        document_kind: str = "decision",
    ) -> dict[str, object]:
        self._ensure_public(response)
        return {
            "body": response.body,
            "collection": collection,
            "publication_status": publication_status,
            "source_page": source_page,
            "source_url": response.url,
            "title": title,
            "document_kind": document_kind,
        }


class ConstitutionalPdfSpider(PublicPdfSpider):
    name = "constitutional-pdfs"
    allowed_domains: ClassVar[list[str]] = ["cour-constitutionnelle.ma"]
    start_urls: ClassVar[list[str]] = [
        "https://cour-constitutionnelle.ma/Publication?CC=4&Page=Publication"
    ]

    def parse(self, response, **kwargs):
        self._ensure_public(response)
        links = response.css('a[href*="Pdf?id="]::attr(href)').getall()
        for href in sorted(set(links)):
            yield response.follow(href, callback=self.parse_publication)

    def parse_publication(self, response):
        self._ensure_public(response)
        title = response.css(".pdf-container .title, .article-content").xpath("string(.)").get()
        title = (title or "Recueil de décisions").strip()
        links = response.css('a[href$=".pdf"]::attr(href), iframe[src$=".pdf"]::attr(src)').getall()
        for href in sorted(set(links)):
            pdf_url = urljoin(response.url, href)
            if urlparse(pdf_url).hostname not in self.allowed_domains:
                continue
            yield Request(
                pdf_url,
                callback=self.parse_pdf,
                cb_kwargs={"source_page": response.url, "title": title},
            )

    def parse_pdf(self, response, source_page: str, title: str):
        yield self._pdf_item(
            response,
            collection="official/cour-constitutionnelle",
            publication_status="official",
            source_page=source_page,
            title=title,
            document_kind="collection",
        )


class MarocDroitPdfSpider(PublicPdfSpider):
    name = "marocdroit-pdfs"
    allowed_domains: ClassVar[list[str]] = ["marocdroit.com", "www.marocdroit.com"]
    start_urls: ClassVar[list[str]] = [
        "https://www.marocdroit.com/attachment/2741595/",
        "https://www.marocdroit.com/attachment/2748822/",
        "https://www.marocdroit.com/attachment/2573277/",
        "https://www.marocdroit.com/attachment/2741643/",
    ]

    def parse(self, response, **kwargs):
        identifier = response.url.rstrip("/").rsplit("/", 1)[-1]
        yield self._pdf_item(
            response,
            collection="secondary/marocdroit",
            publication_status="secondary",
            source_page=response.url,
            title=f"Décision judiciaire publiée par MarocDroit ({identifier})",
        )


class MarocDroitSearchPdfSpider(PublicPdfSpider):
    """Discover public judicial PDF attachments through the site's own search."""

    name = "marocdroit-search-pdfs"
    allowed_domains: ClassVar[list[str]] = ["marocdroit.com", "www.marocdroit.com"]
    preflight_urls: ClassVar[list[str]] = ["https://www.marocdroit.com/search/"]
    search_terms: ClassVar[tuple[str, ...]] = (
        "قضاء النقض",
        "محكمة النقض",
        "المحكمة الإدارية",
        "المحكمة التجارية",
        "محكمة الاستئناف",
    )

    async def start(self):
        for term in self.search_terms:
            yield Request(
                f"https://www.marocdroit.com/search/?keyword={quote_plus(term)}",
                callback=self.parse_search,
            )

    def parse_search(self, response):
        self._ensure_public(response)
        article_links = response.css('a[href*="_a"][href$=".html"]::attr(href)').getall()
        for href in sorted(set(article_links)):
            yield response.follow(href, callback=self.parse_article)

        pagination = response.css('a[href*="/search/"][href*="start_liste="]::attr(href)').getall()
        for href in sorted(set(pagination)):
            yield response.follow(href, callback=self.parse_search)

    def parse_article(self, response):
        self._ensure_public(response)
        page_title = response.css("h1::text, title::text").get() or "Publication MarocDroit"
        attachments = response.css('a[href*="/attachment/"]')
        for link in attachments:
            href = link.attrib.get("href")
            if not href:
                continue
            attachment_title = " ".join(link.css("::text").getall()).strip()
            title = attachment_title or page_title.strip()
            document_kind = _classify_judicial_pdf(f"{page_title} {title}")
            if document_kind is None:
                continue
            yield response.follow(
                href,
                callback=self.parse_pdf,
                cb_kwargs={
                    "source_page": response.url,
                    "title": title,
                    "document_kind": document_kind,
                },
            )

    def parse_pdf(self, response, source_page: str, title: str, document_kind: str):
        yield self._pdf_item(
            response,
            collection="secondary/marocdroit-search",
            publication_status="secondary",
            source_page=source_page,
            title=title,
            document_kind=document_kind,
        )


SPIDERS = {
    "constitutional": ConstitutionalPdfSpider,
    "marocdroit": MarocDroitPdfSpider,
    "marocdroit-search": MarocDroitSearchPdfSpider,
}


def run_pdf_crawl(
    source: str,
    output_dir: str,
    bucket: str | None = None,
    prefix: str = "jurisprudence",
    job_dir: str | None = None,
    limit: int | None = None,
    browser_fallback: bool = False,
) -> None:
    if source not in SPIDERS:
        raise ValueError(f"Unknown PDF crawl source: {source}")

    # Scrapy obeys robots.txt for every request. This synchronous preflight adds a
    # fail-closed gate for an unreachable robots file or a server-side robots error.
    from .sources import PublicHttpClient

    robots_client = PublicHttpClient()
    robots_client.delay_seconds = 0
    spider_class = SPIDERS[source]
    preflight_urls = getattr(spider_class, "start_urls", None) or getattr(
        spider_class, "preflight_urls", []
    )
    for url in preflight_urls:
        robots_client.assert_robots_allowed(url)

    settings: dict[str, object] = {
        "USER_AGENT": USER_AGENT,
        "ROBOTSTXT_OBEY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.0,
        "AUTOTHROTTLE_MAX_DELAY": 60.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 0.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [408, 500, 502, 503, 504, 522, 524],
        "ITEM_PIPELINES": {f"{__name__}.PdfArchivePipeline": 300},
        "PDF_OUTPUT_DIR": output_dir,
        "PDF_BUCKET": bucket,
        "PDF_PREFIX": prefix,
        "PDF_LIMIT": limit or 0,
        "LOG_LEVEL": "INFO",
        "TELNETCONSOLE_ENABLED": False,
    }
    if job_dir:
        settings["JOBDIR"] = job_dir
    if limit is not None:
        settings["CLOSESPIDER_ITEMCOUNT"] = limit
    if browser_fallback:
        try:
            import scrapy_playwright  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("Install the browser dependency: pip install '.[browser]'") from exc
        settings.update(
            {
                "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
                "DOWNLOAD_HANDLERS": {
                    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                },
                "PLAYWRIGHT_BROWSER_TYPE": "chromium",
            }
        )

    process = CrawlerProcess(settings=settings)
    process.crawl(spider_class)
    process.start()
