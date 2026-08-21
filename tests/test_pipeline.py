from jurisprudence_extractor.models import JudicialDecision
from jurisprudence_extractor.sources import (
    ConstitutionalCourtSource,
    JuriscassationMetadataSource,
)
from jurisprudence_extractor.storage import DecisionStore

FIXTURE = """
<html><body><main>
<h1>قرارات المحكمة الدستورية</h1>
<p>قرار رقم : 263/26</p>
<p>تاريخ صدور القرار : 2026/06/15</p>
<p>باسم جلالة الملك وطبقا للقانون المحكمة الدستورية بعد اطلاعها على الوثائق
وبناء على الدستور تقضي بما يلي مع نشر هذا القرار في الجريدة الرسمية.</p>
</main></body></html>
"""

JURISCASSATION_FIXTURE = """
<table id="myid"><tbody><tr>
<td>2023/1/1/1823</td><td>2024/104</td><td>2024-02-13</td>
<td class="matched-sentence">مشمولات عقد التأمين سبب قيام المسؤولية المدنية</td>
<td><a class="show-modal-btn" data-id="opaque">معاينة القرار</a></td>
</tr></tbody></table>
"""


def test_constitutional_decision_parser() -> None:
    item = ConstitutionalCourtSource().parse_decision(
        FIXTURE, "https://www.courconstitutionnelle.ma/Decision?id=2127"
    )
    assert item.decision_number == "263/26"
    assert item.decision_date.isoformat() == "2026-06-15"
    assert len(item.content_sha256) == 64


def test_store_deduplicates(tmp_path) -> None:
    item = JudicialDecision(
        source="test",
        source_url="https://example.test/decision/1",
        jurisdiction="Test court",
        text="A sufficiently complete decision text.",
    ).with_fingerprint()
    with DecisionStore(tmp_path / "test.sqlite3") as store:
        assert store.save(item) is True
        assert store.save(item) is False


def test_juriscassation_metadata_parser() -> None:
    source = JuriscassationMetadataSource(subject="المسؤولية", chambers=(1,))
    items = source.parse_results(JURISCASSATION_FIXTURE)
    assert len(items) == 1
    assert items[0].decision_number == "2024/104"
    assert items[0].case_number == "2023/1/1/1823"
    assert items[0].content_kind == "excerpt"
