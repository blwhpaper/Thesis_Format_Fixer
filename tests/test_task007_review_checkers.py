from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from thesis_format_fixer.detectors.block_locator import locate_blocks
from thesis_format_fixer.io.document_loader import load_document
from thesis_format_fixer.review.checkers import (
    body_english_punctuation_review,
    heading_structure_review,
    pagination_review,
    reference_structure_review,
)


def _write_min_docx(path: Path, *, body: list[str], footer_text: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    body_xml = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in body)
    document_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main' "
        "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>"
        f"<w:body>{body_xml}<w:sectPr/></w:body></w:document>"
    )

    content_overrides = [
        "<Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/>",
    ]
    rels_items = []

    footer_xml = None
    if footer_text is not None:
        footer_xml = (
            "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
            "<w:ftr xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
            f"<w:p><w:r><w:t>{footer_text}</w:t></w:r></w:p></w:ftr>"
        )
        content_overrides.append(
            "<Override PartName='/word/footer1.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml'/>"
        )
        rels_items.append(
            "<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer' Target='footer1.xml'/>"
        )

    content_types_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
        "<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
        "<Default Extension='xml' ContentType='application/xml'/>"
        f"{''.join(content_overrides)}</Types>"
    )

    root_rels_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
        "<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' "
        "Target='word/document.xml'/></Relationships>"
    )

    document_rels_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
        f"{''.join(rels_items)}</Relationships>"
    )

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", root_rels_xml)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", document_rels_xml)
        if footer_xml is not None:
            archive.writestr("word/footer1.xml", footer_xml)


def test_heading_structure_review_minimal_sample(tmp_path: Path) -> None:
    docx = tmp_path / "heading.docx"
    _write_min_docx(
        docx,
        body=["CONTENTS", "1 Intro", "1.1 Scope", "1.1.1 Details", "REFERENCES", "[1] A. Journal, 2024."],
    )
    context = load_document(docx)
    block_map = locate_blocks(context)

    findings = heading_structure_review(context, block_map)
    assert findings
    assert any(item.rule_id == "FR-4.8-01" for item in findings)


def test_reference_structure_review_minimal_sample(tmp_path: Path) -> None:
    docx = tmp_path / "refs.docx"
    _write_min_docx(
        docx,
        body=[
            "REFERENCES",
            "[1] Smith J. Journal of Tests, 2025.",
            "[2] 王强. 测试出版社, 2024.",
        ],
    )
    context = load_document(docx)
    block_map = locate_blocks(context)

    findings = reference_structure_review(context, block_map)
    assert findings
    assert any(item.rule_id == "FR-4.11-03" for item in findings)
    assert any(item.rule_id == "FR-4.11-04" for item in findings)


def test_pagination_review_minimal_sample(tmp_path: Path) -> None:
    docx = tmp_path / "page.docx"
    _write_min_docx(docx, body=["1 Intro", "Text"], footer_text="-1-")

    context = load_document(docx)
    block_map = locate_blocks(context)
    findings = pagination_review(context, block_map)

    assert findings
    assert any(item.rule_id == "FR-4.15-03" for item in findings)


def test_body_english_punctuation_review_hits_chinese_punctuation_in_body(tmp_path: Path) -> None:
    docx = tmp_path / "body-punct-hit.docx"
    _write_min_docx(
        docx,
        body=[
            "CONTENTS",
            "1 Intro",
            "This sentence has wrong punctuation， in body.",
            "REFERENCES",
            "[1] Smith J. Journal of Tests, 2025.",
        ],
    )
    context = load_document(docx)
    block_map = locate_blocks(context)

    findings = body_english_punctuation_review(context, block_map)
    assert any(item.rule_id == "FR-4.9-02" and item.decision.value == "warn" for item in findings)


def test_body_english_punctuation_review_does_not_scan_non_body_sections(tmp_path: Path) -> None:
    docx = tmp_path / "body-punct-non-body.docx"
    _write_min_docx(
        docx,
        body=[
            "Abstract",
            "This abstract line has chinese punct， but should be ignored.",
            "CONTENTS",
            "1 Intro",
            "This body line is clean.",
            "REFERENCES",
            "[1] Smith J. Journal of Tests, 2025.",
        ],
    )
    context = load_document(docx)
    block_map = locate_blocks(context)

    findings = body_english_punctuation_review(context, block_map)
    assert not any(item.rule_id == "FR-4.9-02" and item.decision.value in {"warn", "fail"} for item in findings)


def test_body_english_punctuation_review_skips_obvious_chinese_quote(tmp_path: Path) -> None:
    docx = tmp_path / "body-punct-quote-skip.docx"
    _write_min_docx(
        docx,
        body=[
            "CONTENTS",
            "1 Intro",
            "The source keeps Chinese quote: “这是中文引文，含中文标点。”",
            "REFERENCES",
            "[1] Smith J. Journal of Tests, 2025.",
        ],
    )
    context = load_document(docx)
    block_map = locate_blocks(context)

    findings = body_english_punctuation_review(context, block_map)
    assert not any(item.rule_id == "FR-4.9-02" and item.decision.value in {"warn", "fail"} for item in findings)
