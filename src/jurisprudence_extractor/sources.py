from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .models import JudicialDecision

LOGGER = logging.getLogger(__name__)


class SourceBlocked(RuntimeError):
    """Raised when collection is disallowed or requires protected access."""


class PublicSource(ABC):
    user_agent = "JurisprudenceExtractor/0.1 (+research; contact required)"
    delay_seconds = 1.0

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def assert_robots_allowed(self, url: str) -> None:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = RobotFileParser(robots_url)
        try:
            parser.read()
        except OSError as exc:
            raise SourceBlocked(f"Unable to verify robots.txt for {url}") from exc
        if not parser.can_fetch(self.user_agent, url):
            raise SourceBlocked(f"robots.txt disallows collection: {url}")

    def get(self, url: str) -> requests.Response:
        self.assert_robots_allowed(url)
        time.sleep(self.delay_seconds)
        response = self.session.get(url, timeout=(10, 45))
        if response.status_code in {401, 403, 429}:
            raise SourceBlocked(
                f"Protected or rate-limited source ({response.status_code}): {url}"
            )
        response.raise_for_status()
        return response

    @abstractmethod
    def iter_decisions(self, limit: int | None = None) -> Iterator[JudicialDecision]:
        raise NotImplementedError


class ConstitutionalCourtSource(PublicSource):
    """Collector for public Moroccan Constitutional Court decision pages."""

    index_url = "https://www.courconstitutionnelle.ma/Decisions?Page=Decision"

    def parse_decision(self, html: str, url: str) -> JudicialDecision:
        soup = BeautifulSoup(html, "html.parser")
        page_text = soup.get_text(" ", strip=True)
        number = None
        decision_date = None

        number_match = re.search(r"قرار\s+رقم\s*[:：]?\s*([^\s]+)", page_text)
        if number_match:
            number = number_match.group(1)

        date_match = re.search(
            r"تاريخ\s+صدور\s+القرار\s*[:：]?\s*(\d{4}/\d{2}/\d{2})",
            page_text,
        )
        if date_match:
            decision_date = date.fromisoformat(date_match.group(1).replace("/", "-"))

        main = soup.select_one("main, .decision, .content, #content")
        text = main.get_text(" ", strip=True) if main else page_text
        if len(text) < 80:
            raise ValueError(f"Decision content too short: {url}")

        return JudicialDecision(
            source="cour_constitutionnelle_maroc",
            source_url=url,
            source_id=url.rsplit("=", 1)[-1] if "id=" in url else None,
            jurisdiction="Cour constitutionnelle",
            court="Cour constitutionnelle du Royaume du Maroc",
            decision_number=number,
            decision_date=decision_date,
            language="ar",
            text=text,
            publication_status="official",
        ).with_fingerprint()

    def iter_decisions(self, limit: int | None = None) -> Iterator[JudicialDecision]:
        response = self.get(self.index_url)
        soup = BeautifulSoup(response.text, "html.parser")
        seen: set[str] = set()
        selector = 'a[href*="Decision?id="], a[href*="Decision?Page=Decision&id="]'
        for link in soup.select(selector):
            url = requests.compat.urljoin(self.index_url, link.get("href"))
            if url in seen:
                continue
            seen.add(url)
            yield self.parse_decision(self.get(url).text, url)
            if limit is not None and len(seen) >= limit:
                return


class HuggingFaceDatasetSource:
    dataset_id = "OpenDataMoroccanLaw/morocco-cassation-court-decisions"

    def iter_decisions(self, limit: int | None = None) -> Iterator[JudicialDecision]:
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional dependency: pip install '.[huggingface]'"
            ) from exc

        dataset = load_dataset(self.dataset_id, split="train", streaming=True)
        for index, row in enumerate(dataset):
            text = str(row.get("text") or row.get("decision_text") or "").strip()
            source_url = row.get("url") or row.get("source_url")
            if not text or not source_url:
                LOGGER.warning("Skipping incomplete dataset row %s", index)
                continue
            yield JudicialDecision(
                source="juriscassation_cspj_via_huggingface",
                source_url=source_url,
                source_id=str(row.get("id") or index),
                jurisdiction="Cour de cassation",
                court="Cour de cassation du Royaume du Maroc",
                decision_number=row.get("decision_number"),
                case_number=row.get("case_number"),
                decision_date=row.get("decision_date") or row.get("date"),
                language=row.get("language") or "ar",
                title=row.get("title"),
                text=text,
                publication_status="official",
            ).with_fingerprint()
            if limit is not None and index + 1 >= limit:
                return
