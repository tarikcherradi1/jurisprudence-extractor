from jurisprudence_extractor.anonymize import anonymize_decision
from jurisprudence_extractor.audit import audit_corpus
from jurisprudence_extractor.huggingface_audit import summarize_dataset
from jurisprudence_extractor.models import JudicialDecision
from jurisprudence_extractor.sources import (
    ConstitutionalCourtSource,
    HuggingFaceDatasetSource,
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
        assert store.contains(item) is False
        assert store.save(item) is True
        assert store.contains(item) is True
        assert store.save(item) is False


def test_juriscassation_metadata_parser() -> None:
    source = JuriscassationMetadataSource(subject="المسؤولية", chambers=(1,))
    items = source.parse_results(JURISCASSATION_FIXTURE)
    assert len(items) == 1
    assert items[0].decision_number == "2024/104"
    assert items[0].case_number == "2023/1/1/1823"
    assert items[0].content_kind == "excerpt"


def test_conservative_anonymization() -> None:
    item = JudicialDecision(
        source="test",
        source_url="https://example.test/decision/2",
        jurisdiction="Test court",
        summary="Contact: avocat@example.ma",
        text="La victime, téléphone 0612345678, CIN: AB123456.",
    )
    result = anonymize_decision(item)
    assert "0612345678" not in result.decision.text
    assert "AB123456" not in result.decision.text
    assert "avocat@example.ma" not in result.decision.summary
    assert result.redaction_count == 3
    assert result.requires_human_review is True
    assert result.decision.anonymization_status == "automatic"
    assert len(result.decision.content_sha256) == 64


def test_corpus_audit_uses_measured_counts() -> None:
    full = JudicialDecision(
        source="official",
        source_url="https://example.test/decision/3",
        jurisdiction="Test court",
        decision_number="3",
        text="Same published text.",
    ).with_fingerprint()
    excerpt = full.model_copy(
        update={"source": "secondary", "content_kind": "excerpt"}
    )
    report = audit_corpus([full, excerpt])
    assert report["total"] == 2
    assert report["by_content_kind"] == {"excerpt": 1, "full_text": 1}
    assert report["duplicate_content_hashes"] == 1
    assert report["missing_case_number"] == 2


def test_huggingface_row_mapping_matches_published_schema() -> None:
    item = HuggingFaceDatasetSource.parse_row(
        {
            "docket_number": "1/2/2/187",
            "decision_number": "2021/34",
            "date": "2021-02-02T00:00:00",
            "chamber": "غرفة الأحوال الشخصية والميراث",
            "bench": None,
            "text": "باسم جلالة الملك وطبقا للقانون نص قرار منشور للاختبار.",
            "has_preamble": True,
            "source": "juriscassation.cspj.ma",
        },
        0,
    )
    assert item.case_number == "1/2/2/187"
    assert item.decision_date.isoformat() == "2021-02-02"
    assert item.publication_status == "secondary"
    assert item.source_license == "CC-BY-4.0"
    assert item.upstream_source == "juriscassation.cspj.ma"


def test_huggingface_audit_summary() -> None:
    size = {"size": {"dataset": {"num_rows": 29_000, "num_bytes_parquet_files": 85}}}
    statistics = {
        "statistics": [
            {"column_name": "date", "column_statistics": {"min": "1997", "max": "2026", "nan_count": 0}},
            {"column_name": "chamber", "column_statistics": {"frequencies": {"civil": 5}}},
            {"column_name": "bench", "column_statistics": {"nan_count": 28_604}},
            {"column_name": "decision_number", "column_statistics": {"nan_count": 0}},
            {"column_name": "docket_number", "column_statistics": {"nan_count": 0}},
            {"column_name": "text", "column_statistics": {"min": 410, "max": 124_181}},
        ]
    }
    report = summarize_dataset(size, statistics)
    assert report["rows"] == 29_000
    assert report["missing_bench"] == 28_604
    assert report["text_length_max"] == 124_181
