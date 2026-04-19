from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from thesis_format_fixer.app.runner import run_fix

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def _write_docx(
    path: Path,
    *,
    body_paragraphs: list[str],
    footnotes: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    body_xml = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in body_paragraphs)
    document_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main' "
        "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>"
        f"<w:body>{body_xml}<w:sectPr/></w:body></w:document>"
    )

    footnotes_xml = None
    document_rels = [
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>",
        "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>",
    ]
    content_type_overrides = [
        "<Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/>",
    ]

    if footnotes is not None:
        footnote_xml_items = [
            "<w:footnote w:id='-1' w:type='separator'><w:p><w:r><w:separator/></w:r></w:p></w:footnote>",
            "<w:footnote w:id='0' w:type='continuationSeparator'><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>",
        ]
        for idx, text in enumerate(footnotes, start=1):
            footnote_xml_items.append(
                f"<w:footnote w:id='{idx}'><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:footnote>"
            )

        footnotes_xml = (
            "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
            "<w:footnotes xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
            f"{''.join(footnote_xml_items)}</w:footnotes>"
        )

        document_rels.append(
            "<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes' "
            "Target='footnotes.xml'/>"
        )
        content_type_overrides.append(
            "<Override PartName='/word/footnotes.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml'/>"
        )

    document_rels.append("</Relationships>")

    content_types_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
        "<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
        "<Default Extension='xml' ContentType='application/xml'/>"
        f"{''.join(content_type_overrides)}</Types>"
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
        archive.writestr("word/_rels/document.xml.rels", "".join(document_rels))
        if footnotes_xml is not None:
            archive.writestr("word/footnotes.xml", footnotes_xml)


def _read_paragraph_texts(path: Path, member: str = "word/document.xml") -> list[str]:
    with ZipFile(path, "r") as archive:
        root = ET.fromstring(archive.read(member))
    texts: list[str] = []
    for paragraph in root.findall(".//w:p", NS):
        text = "".join((node.text or "") for node in paragraph.findall(".//w:t", NS)).strip()
        if text:
            texts.append(text)
    return texts


def test_task015_fixes_chinese_punctuation_in_english_body(tmp_path: Path) -> None:
    input_docx = tmp_path / "in.docx"
    output_docx = tmp_path / "out" / "in.fixed.docx"
    _write_docx(
        input_docx,
        body_paragraphs=[
            "CONTENTS",
            "1 Intro",
            "This is a safe body line， and it should end here。",
            "REFERENCES",
            "[1] Smith J， Journal of Testing。 2026.",
        ],
    )

    assert run_fix(input_docx, output_docx) == 0

    texts = _read_paragraph_texts(output_docx)
    assert "This is a safe body line, and it should end here." in texts

    report = json.loads(output_docx.with_suffix(".report.json").read_text(encoding="utf-8"))
    auto_fixed_ids = {item["rule_id"] for item in report["sections"]["auto_fixed"]}
    assert "FR-4.9-02" in auto_fixed_ids


def test_task015_does_not_modify_references_section(tmp_path: Path) -> None:
    input_docx = tmp_path / "in.docx"
    output_docx = tmp_path / "out" / "in.fixed.docx"
    _write_docx(
        input_docx,
        body_paragraphs=[
            "CONTENTS",
            "1 Intro",
            "This body sentence is clean.",
            "REFERENCES",
            "[1] Smith J， Journal of Testing。 2026.",
        ],
    )

    assert run_fix(input_docx, output_docx) == 0

    texts = _read_paragraph_texts(output_docx)
    assert "[1] Smith J， Journal of Testing。 2026." in texts


def test_task015_does_not_modify_footnotes(tmp_path: Path) -> None:
    input_docx = tmp_path / "in.docx"
    output_docx = tmp_path / "out" / "in.fixed.docx"
    _write_docx(
        input_docx,
        body_paragraphs=[
            "CONTENTS",
            "1 Intro",
            "This is a safe body line， to be fixed。",
            "REFERENCES",
            "[1] Smith J. Journal of Testing, 2026.",
        ],
        footnotes=["Footnote keeps chinese punct， and stays。"],
    )

    assert run_fix(input_docx, output_docx) == 0

    footnote_texts = _read_paragraph_texts(output_docx, member="word/footnotes.xml")
    assert "Footnote keeps chinese punct， and stays。" in footnote_texts


def test_task015_skips_high_risk_mixed_paragraph(tmp_path: Path) -> None:
    input_docx = tmp_path / "in.docx"
    output_docx = tmp_path / "out" / "in.fixed.docx"
    _write_docx(
        input_docx,
        body_paragraphs=[
            "CONTENTS",
            "1 Intro",
            "This line 包含较多中文内容用于说明和引用， therefore keep。",
            "REFERENCES",
            "[1] Smith J. Journal of Testing, 2026.",
        ],
    )

    assert run_fix(input_docx, output_docx) == 0

    texts = _read_paragraph_texts(output_docx)
    assert "This line 包含较多中文内容用于说明和引用， therefore keep。" in texts

    report = json.loads(output_docx.with_suffix(".report.json").read_text(encoding="utf-8"))
    non_fixed = report["sections"]["detected_not_auto_modified"]
    task015_rows = [item for item in non_fixed if item["rule_id"] == "FR-4.9-02"]
    assert task015_rows
    assert task015_rows[0]["details"]["reason"] == "high_risk_candidates_skipped"
