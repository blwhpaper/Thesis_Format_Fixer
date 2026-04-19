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


def test_reference_checker_journal_entry_clean() -> None:
    entries = _parse_entries(
        [
            "[1] Smith J. Test Framework[J]. Journal of Testing, 2024(1): 10-20.",
            "[2] Brown A. QA Methods[J]. Journal of QA, 2025(2): 21-30.",
            "[3] Lee C. Software Metrics[J]. Software Journal, 2024(3): 31-40.",
            "[4] Green D. Evaluation Study[J]. Testing Review, 2023(4): 12-19.",
            "[5] White E. Validation Pipeline[J]. Journal of Validation, 2026(1): 44-53.",
        ]
    )

    result = run_reference_checks(entries)
    assert result.findings == ()


def test_reference_checker_emits_type_and_structure_finding_codes() -> None:
    entries = _parse_entries(
        [
            "[1] No marker entry.",
            "[2] Bad type[W]. payload.",
            "[3] Bad carrier[EB/XX]. source, 2024. https://example.org/x",
            "[4] Smith J. Missing pages[J]. Journal A, 2024(1).",
            "[5] Wang Q. Thesis with pages[D]. Taiyuan: TYU, 2023, 1-9.",
            "[6] Wang Q. Thesis missing year[D]. Taiyuan: TYU.",
            "[7] E source[EB/OL]. only year, 2024.",
            "[8] Book no pages[M]. Beijing: Press, 2020.",
        ]
    )

    result = run_reference_checks(entries)
    codes = {item.finding_code for item in result.findings}

    assert "reference_type_marker_missing" in codes
    assert "reference_type_marker_invalid" in codes
    assert "reference_type_carrier_invalid" in codes
    assert "reference_journal_structure_invalid" in codes
    assert "reference_book_structure_invalid" in codes
    assert "reference_thesis_structure_invalid" in codes
    assert "reference_eb_ol_structure_invalid" in codes
    assert "reference_d_thesis_has_page_range" in codes


def test_reference_checker_emits_language_and_count_finding_codes() -> None:
    entries = _parse_entries(
        [
            "[1] Smith J. J1[J]. Journal A, 2024(1): 1-2.",
            "[2] Wang Q. 中文条目[J]. 测试学报, 2023(2): 3-4.",
            "[3] Brown A. J2[J]. Journal B, 2024(1): 1-2.",
        ]
    )

    result = run_reference_checks(entries)
    codes = {item.finding_code for item in result.findings}

    assert "reference_english_count_insufficient" in codes
    assert "reference_language_order_invalid" in codes


def test_reference_checker_emits_marks_punctuation_and_field_order_codes() -> None:
    entries = _parse_entries(
        [
            "[1] Smith J. Cites 《English Title》[J]. Journal A, 2024(1): 1-2.",
            "[2] Smith J. Bad punctuation[J]. Journal A,, 2024(1): 1-2",
            "[3] Smith J. Order issue 2024[J]. Journal A(1): 1-2.",
        ]
    )

    result = run_reference_checks(entries)
    codes = {item.finding_code for item in result.findings}

    assert "reference_english_contains_cn_book_title_marks" in codes
    assert "reference_punctuation_invalid" in codes
    assert "reference_field_order_invalid" in codes


def test_reference_checker_findings_expose_required_fields() -> None:
    entries = _parse_entries(["[1] random text"])
    result = run_reference_checks(entries)

    finding = result.findings[0]
    assert finding.rule_code
    assert finding.finding_code
    assert finding.severity
    assert finding.block_id
    assert finding.reference_index is not None
    assert finding.reference_text
    assert finding.reason or finding.expected_pattern
    assert finding.is_auto_fixable is False


def test_runner_report_exposes_reference_checker_statistics_and_samples(tmp_path: Path) -> None:
    input_docx = tmp_path / "refs.docx"
    report_json = tmp_path / "refs.report.json"
    _write_min_docx(
        input_docx,
        body=[
            "REFERENCES",
            "[1] Smith J. A practical testing framework[J]. Journal of Testing, 2024(3): 10-20.",
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

    sample = diag["reference_entry_findings_sample"]
    if sample:
        assert "finding_code" in sample[0]
        assert "rule_code" in sample[0]
        assert "reference_text" in sample[0]

    assert "reference_check_finding_count" in summary
    assert "reference_check_error_count" in summary
    assert "reference_check_warning_count" in summary
    assert "reference_english_count" in summary
    assert "reference_chinese_count" in summary
    assert "reference_unknown_count" in summary
