"""E2E Contract test for Review flow: structured findings -> WordReviewAdapter -> reviewed docx -> report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from thesis_format_fixer.review.adapter import WordReviewAdapter
from thesis_format_fixer.review.contracts import (
    StructuredReviewFinding,
    to_adapter_finding,
)


def _load_docx_api():
    docx = pytest.importorskip("docx", reason="python-docx is required for real DOCX integration tests")
    Document = docx.Document
    probe = Document()
    if not hasattr(probe, "add_comment"):
        pytest.skip("python-docx version does not support Document.add_comment comments API")
    return Document


def _body_texts(document) -> list[str]:
    return [paragraph.text for paragraph in document.paragraphs]


@pytest.fixture
def sample_structured_findings() -> list[StructuredReviewFinding]:
    """Provides a stable, auditable list of structured findings."""
    return [
        # Valid finding that should map to adapter
        StructuredReviewFinding(
            rule_id="FR-1.1",
            category="Format",
            severity="Medium",
            message="Please use correct font.",
            anchor_strategy="paragraph",
            paragraph_index=0,
            run_index=0,
            anchor_text="Test",
        ),
        # Invalid finding: missing paragraph_index (error/fallback boundary test)
        StructuredReviewFinding(
            rule_id="FR-1.2",
            category="Format",
            severity="Medium",
            message="Cannot anchor without paragraph.",
            anchor_strategy="paragraph",
            paragraph_index=None,
        ),
        # Valid finding but points to out-of-bounds paragraph index in our test
        StructuredReviewFinding(
            rule_id="FR-1.3",
            category="Format",
            severity="Low",
            message="Out of bounds paragraph.",
            anchor_strategy="paragraph",
            paragraph_index=999,
        ),
    ]


def test_review_e2e_contract_harness(tmp_path: Path, sample_structured_findings: list[StructuredReviewFinding]) -> None:
    Document = _load_docx_api()
    input_path = tmp_path / "thesis_input.docx"
    output_path = tmp_path / "thesis_reviewed.docx"
    report_path = tmp_path / "review_report.json"

    # 1. Create a minimal mock docx
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("First paragraph.")
    document.add_paragraph("Second paragraph.")
    
    before_texts = _body_texts(document)
    document.save(input_path)

    # 2. Process findings (simulate mapping layer)
    adapter_findings = []
    mapping_report = []

    for finding in sample_structured_findings:
        map_result = to_adapter_finding(finding)
        mapping_report.append({
            "rule_id": finding.rule_id,
            "status": map_result.status,
            "reason": map_result.reason,
        })
        if map_result.status == "mapped" and map_result.adapter_finding:
            adapter_findings.append(map_result.adapter_finding)

    # 3. Apply to WordReviewAdapter
    loaded_doc = Document(input_path)
    adapter = WordReviewAdapter()
    apply_result = adapter.apply_findings(loaded_doc, adapter_findings)

    # 4. Save reviewed docx
    loaded_doc.save(output_path)

    # 5. Generate result summary/report
    final_report = {
        "schema_version": "review-report-v1",
        "input_file": str(input_path),
        "output_file": str(output_path),
        "mapping_details": mapping_report,
        "apply_summary": {
            "total": apply_result.total,
            "added": apply_result.added,
            "skipped": apply_result.skipped,
            "duplicate": apply_result.duplicate,
            "unsupported": apply_result.unsupported,
        },
        "apply_details": apply_result.details,
    }
    report_path.write_text(json.dumps(final_report, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- Verification ---

    # Assert reviewed docx exists and can be opened
    assert output_path.exists()
    reopened = Document(output_path)
    
    # Assert original content is NOT tampered
    assert _body_texts(reopened) == before_texts
    
    # Assert findings were consumed (1 valid mapped, 1 invalid mapping, 1 valid but out of bounds -> skipped)
    assert len(sample_structured_findings) == 3
    
    assert final_report["mapping_details"][0]["status"] == "mapped"
    assert final_report["mapping_details"][1]["status"] == "skipped"  # missing paragraph_index maps to skipped
    assert final_report["mapping_details"][2]["status"] == "mapped"
    
    assert final_report["apply_summary"]["total"] == 2
    assert final_report["apply_summary"]["added"] == 1
    assert final_report["apply_summary"]["skipped"] == 1  # Out of bounds
    
    # Assert comment exists in reopened document
    comments = list(reopened.comments)
    assert len(comments) == 1
    assert "[TFF-RULE:FR-1.1]" in comments[0].text

    # Assert report exists
    assert report_path.exists()
