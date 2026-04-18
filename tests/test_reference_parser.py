from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from thesis_format_fixer.app.runner import run_check
from thesis_format_fixer.detectors.reference_parser import parse_reference_entry


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


def test_parse_standard_english_journal_entry_j() -> None:
    parsed = parse_reference_entry(
        "[1] Smith J. A practical testing framework[J]. Journal of Testing, 2024, 12(3): 10-20."
    )

    assert parsed.index_number == 1
    assert parsed.entry_type == "journal"
    assert parsed.type_code == "J"
    assert parsed.year == "2024"
    assert parsed.pages == "10-20"
    assert parsed.parse_confidence == "high"


def test_parse_standard_english_book_entry_m() -> None:
    parsed = parse_reference_entry(
        "[2] Brown A. Research Methods[M]. 2nd ed. New York: Sample Press, 2021."
    )

    assert parsed.entry_type == "book"
    assert parsed.type_code == "M"
    assert parsed.publication_place == "New York"
    assert parsed.publisher == "Sample Press"
    assert parsed.edition is not None
    assert parsed.year == "2021"
    assert parsed.parse_confidence == "high"


def test_parse_standard_chinese_thesis_entry_d() -> None:
    parsed = parse_reference_entry("[3] 王强. 基于语料库的翻译研究[D]. 太原: 太原学院, 2023.")

    assert parsed.entry_type == "thesis"
    assert parsed.type_code == "D"
    assert parsed.language_hint in {"zh", "mixed"}
    assert parsed.publication_place == "太原"
    assert parsed.publisher == "太原学院"
    assert parsed.year == "2023"
    assert parsed.parse_confidence == "high"


def test_parse_electronic_entry_with_j_ol() -> None:
    parsed = parse_reference_entry(
        "[4] Lee C. Online teaching effectiveness[J/OL]. Journal of E-Learning, 2025. https://example.org/paper/123"
    )

    assert parsed.entry_type == "journal"
    assert parsed.type_code == "J"
    assert parsed.medium_code == "OL"
    assert parsed.url_or_locator == "https://example.org/paper/123"
    assert parsed.year == "2025"
    assert parsed.parse_confidence == "high"


def test_parse_entry_with_missing_fields_still_partially_extracts() -> None:
    parsed = parse_reference_entry("[5] Chen L. Incomplete entry[J]. 2022.")

    assert parsed.entry_type == "journal"
    assert parsed.year == "2022"
    assert parsed.title is not None
    assert parsed.parse_confidence in {"high", "low"}


def test_parse_non_standard_entry_degrades_to_low_without_exception() -> None:
    parsed = parse_reference_entry("random note without citation structure")

    assert parsed.raw_text == "random note without citation structure"
    assert parsed.entry_type == "unknown"
    assert parsed.parse_confidence == "low"
    assert "entry_type_unknown" in parsed.parse_notes


def test_runner_report_exposes_reference_parse_statistics(tmp_path: Path) -> None:
    input_docx = tmp_path / "refs.docx"
    report_json = tmp_path / "refs.report.json"
    _write_min_docx(
        input_docx,
        body=[
            "REFERENCES",
            "[1] Smith J. A practical testing framework[J]. Journal of Testing, 2024, 12(3): 10-20.",
            "[2] random non-standard entry without clear structure",
            "致谢",
        ],
    )

    assert run_check(input_docx, report_json_out=report_json) == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    diag = payload["sections"]["references_diagnostics"]

    assert diag["reference_entry_count"] == 2
    assert "reference_parsed_count" in diag
    assert "reference_parse_high_confidence_count" in diag
    assert "reference_parse_low_confidence_count" in diag
    assert "reference_type_counts" in diag
    assert "unresolved_reference_entries" in diag
    assert len(diag["unresolved_reference_entries"]) >= 1
