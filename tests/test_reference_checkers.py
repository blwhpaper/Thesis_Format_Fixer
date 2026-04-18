from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from thesis_format_fixer.app.runner import run_check
from thesis_format_fixer.detectors.reference_parser import parse_reference_entry
from thesis_format_fixer.review.reference_checkers import run_reference_checks


def _parse_entries(items: list[str]) -> tuple:
    return tuple(parse_reference_entry(item) for item in items)


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


def test_reference_checker_journal_entry_clean_or_weak_only() -> None:
    entries = _parse_entries(
        [
            "[1] Smith J. Test Framework[J]. Journal of Testing, 2024, 12(1): 10-20.",
            "[2] Brown A. QA Methods[J]. Journal of QA, 2025, 5(2): 21-30.",
            "[3] Lee C. Software Metrics[J]. Software Journal, 2024, 3(1): 31-40.",
            "[4] Green D. Evaluation Study[J]. Testing Review, 2023, 6(4): 12-19.",
            "[5] White E. Validation Pipeline[J]. Journal of Validation, 2026, 2(1): 44-53.",
        ]
    )
    result = run_reference_checks(entries, current_year=2026)

    assert result.entry_findings == ()
    assert result.error_count == 0


def test_reference_checker_journal_missing_pages_yields_entry_finding() -> None:
    entries = _parse_entries(["[1] Smith J. Missing pages[J]. Journal of Tests, 2024, 12(1)."])
    result = run_reference_checks(entries, current_year=2026)

    assert any(item.scope == "entry" and item.evidence.get("check") == "pages_missing" for item in result.findings)


def test_reference_checker_thesis_missing_year_yields_entry_finding() -> None:
    entries = _parse_entries(["[1] 王强. 基于语料库的翻译研究[D]. 太原: 太原学院."])
    result = run_reference_checks(entries, current_year=2026)

    assert any(item.scope == "entry" and item.evidence.get("check") == "year_missing" for item in result.findings)


def test_reference_checker_electronic_missing_url_yields_entry_finding() -> None:
    entries = _parse_entries(["[1] Lee C. Online source[EB/OL]. Database of Studies, 2024."])
    result = run_reference_checks(entries, current_year=2026)

    assert any(
        item.scope == "entry" and item.evidence.get("check") == "electronic_url_missing" for item in result.findings
    )


def test_reference_checker_english_count_under_five_yields_collection_finding() -> None:
    entries = _parse_entries(
        [
            "[1] Smith J. J1[J]. Journal A, 2024, 1(1): 1-2.",
            "[2] Brown A. J2[J]. Journal B, 2024, 1(1): 1-2.",
            "[3] 王强. 中文条目[J]. 测试学报, 2023, 2(1): 3-4.",
        ]
    )
    result = run_reference_checks(entries, current_year=2026)

    assert any(item.scope == "collection" and item.rule_id == "FR-4.11-04" and "少于 5" in item.message for item in result.findings)


def test_reference_checker_language_order_violation_yields_collection_finding() -> None:
    entries = _parse_entries(
        [
            "[1] Smith J. J1[J]. Journal A, 2024, 1(1): 1-2.",
            "[2] Brown A. J2[J]. Journal B, 2024, 1(1): 1-2.",
            "[3] White E. J3[J]. Journal C, 2024, 1(1): 1-2.",
            "[4] 王强. 中文条目[J]. 测试学报, 2023, 2(1): 3-4.",
            "[5] Lee C. J4[J]. Journal D, 2024, 1(1): 1-2.",
            "[6] Green D. J5[J]. Journal E, 2024, 1(1): 1-2.",
        ]
    )
    result = run_reference_checks(entries, current_year=2026)

    assert any(
        item.scope == "collection"
        and item.rule_id == "FR-4.11-04"
        and "英文在前、中文在后" in item.message
        for item in result.findings
    )


def test_reference_checker_many_unknown_or_low_confidence_yields_collection_finding() -> None:
    entries = _parse_entries(
        [
            "random text A",
            "random text B",
            "random text C",
            "[4] random non-standard entry",
            "[5] Smith J. Stable entry[J]. Journal A, 2025, 1(1): 1-3.",
            "[6] Brown A. Stable entry[J]. Journal B, 2025, 1(1): 4-6.",
        ]
    )
    result = run_reference_checks(entries, current_year=2026)

    assert any(
        item.scope == "collection" and item.evidence.get("low_confidence_count", 0) >= 3 for item in result.findings
    )


def test_runner_report_exposes_reference_checker_statistics_and_samples(tmp_path: Path) -> None:
    input_docx = tmp_path / "refs.docx"
    report_json = tmp_path / "refs.report.json"
    _write_min_docx(
        input_docx,
        body=[
            "REFERENCES",
            "[1] Smith J. A practical testing framework[J]. Journal of Testing, 2024, 12(3): 10-20.",
            "[2] 王强. 基于语料库的翻译研究[D]. 太原: 太原学院.",
            "[3] random non-standard entry",
            "致谢",
        ],
    )
    assert run_check(input_docx, report_json_out=report_json) == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    diag = payload["sections"]["references_diagnostics"]
    summary = payload["summary"]

    assert "reference_check_finding_count" in diag
    assert "reference_check_error_count" in diag
    assert "reference_check_warning_count" in diag
    assert "reference_check_rule_counts" in diag
    assert "reference_collection_findings" in diag
    assert "reference_entry_findings_sample" in diag
    assert "reference_english_count" in diag
    assert "reference_chinese_count" in diag
    assert "reference_unknown_count" in diag

    assert "reference_check_finding_count" in summary
    assert "reference_check_error_count" in summary
    assert "reference_check_warning_count" in summary
    assert "reference_english_count" in summary
    assert "reference_chinese_count" in summary
    assert "reference_unknown_count" in summary

