from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .models import JudicialDecision

LOGGER = logging.getLogger(__name__)


class SourceBlocked(RuntimeError):
    """Raised when collection is disallowed or requires protected access."""


class PublicHttpClient:
    user_agent = "JurisprudenceExtractor/0.1 (+research; contact required)"
    delay_seconds = 1.0

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        self._robots_cache: dict[str, RobotFileParser | None] = {}

    def assert_robots_allowed(self, url: str) -> None:
        parsed = urlparse(url)
        authority = f"{parsed.scheme}://{parsed.netloc}"
        if authority not in self._robots_cache:
            robots_url = f"{authority}/robots.txt"
            try:
                response = self.session.get(robots_url, timeout=(10, 30))
            except requests.RequestException as exc:
                raise SourceBlocked(f"robots.txt is unreachable for {url}") from exc
            if 400 <= response.status_code < 500:
                self._robots_cache[authority] = None
            elif response.status_code >= 500:
                raise SourceBlocked(f"robots.txt is unreachable for {url}")
            else:
                response.raise_for_status()
                parser = RobotFileParser(robots_url)
                parser.parse(response.text.splitlines())
                self._robots_cache[authority] = parser
        parser = self._robots_cache[authority]
        if parser is None:
            return
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

    def post(self, url: str, data: dict[str, object]) -> requests.Response:
        self.assert_robots_allowed(url)
        time.sleep(self.delay_seconds)
        response = self.session.post(url, data=data, timeout=(10, 45))
        if response.status_code in {401, 403, 429}:
            raise SourceBlocked(
                f"Protected or rate-limited source ({response.status_code}): {url}"
            )
        response.raise_for_status()
        return response


class PublicSource(PublicHttpClient, ABC):
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


class JuriscassationMetadataSource(PublicSource):
    """Collect official public search metadata without bypassing the document gate."""

    index_url = "https://juriscassation.cspj.ma/Decisions/RechercheDecisions"
    results_url = "https://juriscassation.cspj.ma/Decisions/RechercheDecisionsRes"

    def __init__(
        self,
        subject: str,
        chambers: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7),
        session: requests.Session | None = None,
    ) -> None:
        super().__init__(session=session)
        if len(subject.strip()) < 3:
            raise ValueError("Juriscassation requires a subject of at least 3 characters")
        if not chambers or any(chamber not in range(1, 8) for chamber in chambers):
            raise ValueError("Chambers must contain values between 1 and 7")
        self.subject = subject.strip()
        self.chambers = chambers

    def parse_results(self, html: str) -> list[JudicialDecision]:
        soup = BeautifulSoup(html, "html.parser")
        decisions: list[JudicialDecision] = []
        for row in soup.select("table#myid tbody tr"):
            cells = row.select("td")
            if len(cells) < 4:
                continue
            case_number = cells[0].get_text(" ", strip=True) or None
            decision_number = cells[1].get_text(" ", strip=True) or None
            raw_date = cells[2].get_text(" ", strip=True)
            excerpt = cells[3].get_text(" ", strip=True)
            if not excerpt:
                continue
            decision_date = date.fromisoformat(raw_date) if raw_date else None
            source_id = "|".join(
                value for value in (case_number, decision_number, raw_date) if value
            )
            decisions.append(
                JudicialDecision(
                    source="juriscassation_cspj_metadata",
                    source_url=self.index_url,
                    source_id=source_id,
                    jurisdiction="Cour de cassation",
                    court="Cour de cassation du Royaume du Maroc",
                    decision_number=decision_number,
                    case_number=case_number,
                    decision_date=decision_date,
                    language="ar",
                    summary=excerpt,
                    text=excerpt,
                    content_kind="excerpt",
                    publication_status="official",
                ).with_fingerprint()
            )
        return decisions

    def iter_decisions(self, limit: int | None = None) -> Iterator[JudicialDecision]:
        index = self.get(self.index_url)
        soup = BeautifulSoup(index.text, "html.parser")
        token = soup.select_one('input[name="__RequestVerificationToken"]')
        if token is None or not token.get("value"):
            raise SourceBlocked("Juriscassation verification token is unavailable")

        yielded = 0
        page = 1
        while limit is None or yielded < limit:
            data: dict[str, object] = {
                "ChambreIds": [str(chamber) for chamber in self.chambers],
                "Sujet": self.subject,
                "page": page,
                "__RequestVerificationToken": token.get("value"),
            }
            items = self.parse_results(self.post(self.results_url, data).text)
            if not items:
                return
            for item in items:
                yield item
                yielded += 1
                if limit is not None and yielded >= limit:
                    return
            page += 1


class HuggingFaceDatasetSource:
    dataset_id = "OpenDataMoroccanLaw/morocco-cassation-court-decisions"
    dataset_url = (
        "https://huggingface.co/datasets/"
        "OpenDataMoroccanLaw/morocco-cassation-court-decisions"
    )
    rows_api_url = "https://datasets-server.huggingface.co/rows"

    @classmethod
    def parse_row(cls, row: dict[str, object], index: int) -> JudicialDecision:
        text = str(row.get("text") or "").strip()
        if not text:
            raise ValueError(f"Dataset row {index} has no decision text")

        raw_date = str(row.get("date") or "").strip()
        decision_date = date.fromisoformat(raw_date[:10]) if raw_date else None
        docket_number = str(row.get("docket_number") or "").strip() or None
        decision_number = str(row.get("decision_number") or "").strip() or None
        source_id = "|".join(
            value
            for value in (
                docket_number,
                decision_number,
                decision_date.isoformat() if decision_date else None,
            )
            if value
        ) or str(index)

        return JudicialDecision(
            source="opendatamoroccanlaw_huggingface",
            source_url=cls.dataset_url,
            source_id=source_id,
            jurisdiction="Cour de cassation",
            court="Cour de cassation du Royaume du Maroc",
            chamber=str(row.get("chamber") or "").strip() or None,
            formation=str(row.get("bench") or "").strip() or None,
            decision_number=decision_number,
            case_number=docket_number,
            decision_date=decision_date,
            language="ar",
            text=text,
            publication_status="secondary",
            source_license="CC-BY-4.0",
            upstream_source=str(row.get("source") or "").strip() or None,
            has_preamble=(
                row.get("has_preamble") if isinstance(row.get("has_preamble"), bool) else None
            ),
        ).with_fingerprint()

    def iter_decisions(self, limit: int | None = None) -> Iterator[JudicialDecision]:
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional dependency: pip install '.[huggingface]'"
            ) from exc

        dataset = load_dataset(self.dataset_id, split="train", streaming=True)
        yielded = 0
        for index, row in enumerate(dataset):
            try:
                decision = self.parse_row(row, index)
            except (TypeError, ValueError):
                LOGGER.warning("Skipping incomplete dataset row %s", index)
                continue
            yield decision
            yielded += 1
            if limit is not None and yielded >= limit:
                return

    def iter_api_rows(
        self, limit: int = 100
    ) -> Iterator[tuple[dict[str, object], JudicialDecision]]:
        """Fetch bounded rows through the public dataset API for pilots and audits."""
        if limit < 1:
            return
        offset = 0
        while offset < limit:
            length = min(100, limit - offset)
            response = requests.get(
                self.rows_api_url,
                params={
                    "dataset": self.dataset_id,
                    "config": "default",
                    "split": "train",
                    "offset": offset,
                    "length": length,
                },
                timeout=(10, 60),
            )
            response.raise_for_status()
            rows = response.json().get("rows", [])
            if not rows:
                return
            for wrapped in rows:
                row = wrapped.get("row", {})
                if not isinstance(row, dict):
                    continue
                try:
                    yield row, self.parse_row(row, offset)
                except (TypeError, ValueError):
                    LOGGER.warning("Skipping incomplete dataset row %s", offset)
                offset += 1

    def iter_jsonl(
        self, path: str | Path, limit: int | None = None
    ) -> Iterator[tuple[dict[str, object], JudicialDecision]]:
        """Stream the published JSONL file without loading the corpus into memory."""
        yielded = 0
        with Path(path).open(encoding="utf-8") as stream:
            for index, line in enumerate(stream):
                if limit is not None and yielded >= limit:
                    return
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise TypeError("row is not an object")
                    decision = self.parse_row(row, index)
                except (json.JSONDecodeError, TypeError, ValueError):
                    LOGGER.warning("Skipping invalid JSONL row %s", index)
                    continue
                yield row, decision
                yielded += 1
