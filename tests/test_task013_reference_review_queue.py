from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from thesis_format_fixer.app.runner import run_check
from thesis_format_fixer.contracts.report_types import ReferenceCheckFinding
from thesis_format_fixer.review.finding_prioritizer import build_reference_review_queue


def _write_min_docx(path: Path, *, body: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body_xml = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in body)
    document_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
        f"<w:body>{body_xml}<w:sectPr/></w:body></w:document>"
    )
    content_types_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
        "<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
        "<Default Extension='xml' ContentType='application/xml'/>"
        "<Override PartName='/word/document.xml' "
        "ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/>"
        "</Types>"
    )
    root_rels_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
        "<Relationship Id='rId1' "
        "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' "
        "Target='word/document.xml'/></Relationships>"
    )
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", root_rels_xml)
        archive.writestr("word/document.xml", document_xml)


def test_task013_prioritizer_builds_stable_queue_and_buckets() -> None:
    findings = (
        ReferenceCheckFinding(
            rule_id="FR-4.11-06",
            severity="weak",
            scope="collection",
            entry_index=None,
            message="参考文献疑似未按发表顺序排列（弱提示）。",
        ),
        ReferenceCheckFinding(
            rule_id="FR-4.11-04",
            severity="warning",
            scope="collection",
            entry_index=None,
            message="英文参考文献数量少于 5 篇。",
            evidence={"english_count": 2, "required_min": 5},
        ),
        ReferenceCheckFinding(
            rule_id="FR-4.11-03",
            severity="error",
            scope="entry",
            entry_index=0,
            message="参考文献条目类型无法识别。",
            evidence={"check": "entry_type_unknown"},
        ),
        ReferenceCheckFinding(
            rule_id="FR-4.11-05",
            severity="warning",
            scope="collection",
            entry_index=None,
            message="近三年相关文献命中较少（提示项）。",
        ),
    )

    queue = build_reference_review_queue(findings)

    ordered = queue.queue
    assert [item.priority_bucket for item in ordered] == ["P0", "P0", "P1", "P2"]
    assert ordered[0].rule_id == "FR-4.11-04"
    assert ordered[1].rule_id == "FR-4.11-03"
    assert ordered[0].is_blocking is True
    assert ordered[1].is_blocking is True
    assert queue.summary.blocking_count == 2
    assert queue.summary.p1_count == 1
    assert queue.summary.p2_count == 1


def test_task013_prioritizer_keeps_input_order_when_same_priority() -> None:
    findings = (
        ReferenceCheckFinding(
            rule_id="FR-4.11-03",
            severity="warning",
            scope="entry",
            entry_index=2,
            message="A",
        ),
        ReferenceCheckFinding(
            rule_id="FR-4.11-03",
            severity="warning",
            scope="entry",
            entry_index=3,
            message="B",
        ),
        ReferenceCheckFinding(
            rule_id="FR-4.11-03",
            severity="warning",
            scope="entry",
            entry_index=4,
            message="C",
        ),
    )

    queue = build_reference_review_queue(findings)
    assert [item.message for item in queue.queue] == ["A", "B", "C"]


def test_task013_report_exposes_reference_review_queue_and_summary(tmp_path: Path) -> None:
    input_docx = tmp_path / "refs.docx"
    report_json = tmp_path / "refs.report.json"
    _write_min_docx(
        input_docx,
        body=[
            "REFERENCES",
            "[1] random non-standard entry",
            "[2] 王强. 中文条目[J]. 测试学报, 2022, 2(1): 3-4.",
            "致谢",
        ],
    )

    assert run_check(input_docx, report_json_out=report_json) == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))

    reference_review = payload["sections"]["reference_review"]
    assert "reference_finding_count" in reference_review
    assert "reference_blocking_count" in reference_review
    assert "reference_priority_summary" in reference_review
    assert "reference_review_queue" in reference_review
    assert "top_priority_findings" in reference_review

    summary = payload["summary"]
    assert "reference_finding_count" in summary
    assert "reference_blocking_count" in summary
    assert "reference_priority_summary" in summary


def test_task013_report_handles_empty_reference_findings_safely(tmp_path: Path) -> None:
    input_docx = tmp_path / "no_refs.docx"
    report_json = tmp_path / "no_refs.report.json"
    _write_min_docx(input_docx, body=["Only one paragraph."])

    assert run_check(input_docx, report_json_out=report_json) == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))

    reference_review = payload["sections"]["reference_review"]
    assert reference_review["reference_finding_count"] == 0
    assert reference_review["reference_blocking_count"] == 0
    assert reference_review["reference_review_queue"] == []
