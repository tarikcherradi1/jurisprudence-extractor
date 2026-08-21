from jurisprudence_extractor.models import JudicialDecision
from jurisprudence_extractor.sources import ConstitutionalCourtSource
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
