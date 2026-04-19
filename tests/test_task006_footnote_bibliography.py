from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from thesis_format_fixer.app.runner import run_check, run_fix

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def _write_docx(
    path: Path,
    *,
    body_paragraphs: list[str],
    footnotes: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    document_paragraph_xml = "".join(
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in body_paragraphs
    )
    document_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main' "
        "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>"
        f"<w:body>{document_paragraph_xml}<w:sectPr/></w:body></w:document>"
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
            if text:
                footnote_xml_items.append(
                    f"<w:footnote w:id='{idx}'><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:footnote>"
                )
            else:
                footnote_xml_items.append(f"<w:footnote w:id='{idx}'><w:p/></w:footnote>")

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

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/_rels/document.xml.rels", "".join(document_rels))
        if footnotes_xml is not None:
            zf.writestr("word/footnotes.xml", footnotes_xml)


def _read_xml(path: Path, member: str) -> ET.Element:
    with ZipFile(path, "r") as archive:
        return ET.fromstring(archive.read(member))


def test_task006_fixes_footnotes_and_bibliography_styles(tmp_path: Path) -> None:
    input_docx = tmp_path / "in.docx"
    output_docx = tmp_path / "out" / "in.fixed.docx"

    _write_docx(
        input_docx,
        body_paragraphs=[
            "Title",
            "REFERENCES",
            "[1] Smith J. Journal of Testing, 2026.",
            "[2] Brown A. Testing Press, 2025.",
            "[3] Lee C. Test Report, 2024.",
            "[4] White D. Journal of QA, 2026.",
            "[5] Green E. Sample Dissertation, 2025.",
        ],
        footnotes=["这是中文脚注", "This is an English footnote."],
    )

    code = run_fix(input_docx, output_docx)
    assert code == 0

    footnotes_root = _read_xml(output_docx, "word/footnotes.xml")
    normal_footnotes = [
        node for node in footnotes_root.findall(".//w:footnote", NS) if node.get(f"{{{W_NS}}}type") is None
    ]
    assert len(normal_footnotes) == 2

    first_run_fonts = normal_footnotes[0].find(".//w:rPr/w:rFonts", NS)
    second_run_fonts = normal_footnotes[1].find(".//w:rPr/w:rFonts", NS)
    assert first_run_fonts is not None
    assert second_run_fonts is not None
    assert first_run_fonts.get(f"{{{W_NS}}}ascii") == "宋体"
    assert second_run_fonts.get(f"{{{W_NS}}}ascii") == "Times New Roman"

    for footnote in normal_footnotes:
        spacing = footnote.find(".//w:pPr/w:spacing", NS)
        size = footnote.find(".//w:rPr/w:sz", NS)
        assert spacing is not None
        assert spacing.get(f"{{{W_NS}}}line") == "240"
        assert spacing.get(f"{{{W_NS}}}lineRule") == "auto"
        assert size is not None
        assert size.get(f"{{{W_NS}}}val") == "18"

    document_root = _read_xml(output_docx, "word/document.xml")
    reference_entries = [
        p
        for p in document_root.findall(".//w:body/w:p", NS)
        if ("".join((t.text or "") for t in p.findall(".//w:t", NS))).strip().startswith("[")
    ]
    assert len(reference_entries) == 5
    for entry in reference_entries:
        spacing = entry.find("w:pPr/w:spacing", NS)
        fonts = entry.find(".//w:rPr/w:rFonts", NS)
        size = entry.find(".//w:rPr/w:sz", NS)
        assert spacing is not None
        assert spacing.get(f"{{{W_NS}}}line") == "500"
        assert spacing.get(f"{{{W_NS}}}lineRule") == "exact"
        assert fonts is not None
        assert fonts.get(f"{{{W_NS}}}ascii") == "Times New Roman"
        assert size is not None
        assert size.get(f"{{{W_NS}}}val") == "24"

    report = json.loads(output_docx.with_suffix(".report.json").read_text(encoding="utf-8"))
    assert any(item["rule_id"] == "FR-4.10-02" for item in report["sections"]["auto_fixed_footnotes"])
    assert any(item["rule_id"] == "FR-4.11-02" for item in report["sections"]["auto_fixed_bibliography"])
    references_diag = report["sections"]["references_diagnostics"]
    assert references_diag["references_heading_detected"] is True
    assert references_diag["reference_entries_detected"] == 5
    assert references_diag["reference_entries_fixed"] >= 1


def test_task006_reports_special_issues_without_content_rewrite(tmp_path: Path) -> None:
    input_docx = tmp_path / "issue.docx"
    output_docx = tmp_path / "out" / "issue.fixed.docx"

    _write_docx(
        input_docx,
        body_paragraphs=[
            "REFERENCES",
            "[1] 王强. 老旧文献. 2010.",
            "[3] Smith J. Old Journal, 2015.",
            "[2] 无年份条目",
        ],
        footnotes=["", "This footnote is valid."],
    )

    before_root = _read_xml(input_docx, "word/document.xml")
    before_texts = ["".join((t.text or "") for t in p.findall(".//w:t", NS)) for p in before_root.findall(".//w:body/w:p", NS)]

    code = run_fix(input_docx, output_docx)
    assert code == 0

    after_root = _read_xml(output_docx, "word/document.xml")
    after_texts = ["".join((t.text or "") for t in p.findall(".//w:t", NS)) for p in after_root.findall(".//w:body/w:p", NS)]
    assert before_texts == after_texts

    report = json.loads(output_docx.with_suffix(".report.json").read_text(encoding="utf-8"))
    special_rule_ids = {item["rule_id"] for item in report["sections"]["detected_special_issues_not_modified"]}
    assert "FR-4.11-04" in special_rule_ids
    assert "FR-4.11-05" in special_rule_ids
    assert "FR-4.11-06" in special_rule_ids

    detected_ids = {item["rule_id"] for item in report["sections"]["detected_not_auto_modified"]}
    assert "FR-4.10-02" in detected_ids
    assert "FR-4.10-03" in detected_ids
    assert "FR-4.10-04" in detected_ids


def test_reference_diagnostics_include_author_leading_fallback_counts(tmp_path: Path) -> None:
    input_docx = tmp_path / "author-leading.docx"
    report_json = tmp_path / "author-leading.report.json"

    _write_docx(
        input_docx,
        body_paragraphs=[
            "REFERENCES",
            "Smith, J. A practical test study. Journal of Testing, 2026.",
            "王强，李明. 测试方法综述. 测试学报, 2025.",
            "Brown, A., Lee, C., and Zhang, H. Multi-author report.",
            "Technical Validation Report, 2024.",
            "致谢",
        ],
    )

    assert run_check(input_docx, report_json_out=report_json) == 0

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    diag = payload["sections"]["references_diagnostics"]
    summary = payload["summary"]

    assert diag["references_heading_detected"] is True
    assert diag["reference_entry_total"] == 3
    assert diag["numbered_reference_entry_count"] == 0
    assert diag["author_leading_reference_entry_count"] == 3
    assert diag["suspicious_reference_candidate_count"] == 0
    assert summary["reference_entry_total"] == 3
    assert summary["author_leading_reference_entry_count"] == 3


def test_fix_removes_pages_from_d_type_reference_and_reports_auto_fix(tmp_path: Path) -> None:
    input_docx = tmp_path / "d-pages-in.docx"
    output_docx = tmp_path / "out" / "d-pages-out.fixed.docx"

    _write_docx(
        input_docx,
        body_paragraphs=[
            "REFERENCES",
            "[1] 王强. 基于语料库的翻译研究[D]. 太原: 太原学院, 2023, 98-100.",
            "致谢",
        ],
    )

    code = run_fix(input_docx, output_docx)
    assert code == 0

    document_root = _read_xml(output_docx, "word/document.xml")
    output_lines = [
        "".join((t.text or "") for t in p.findall(".//w:t", NS)).strip()
        for p in document_root.findall(".//w:body/w:p", NS)
    ]
    d_line = next(line for line in output_lines if "[D]" in line)
    assert "98-100" not in d_line

    report = json.loads(output_docx.with_suffix(".report.json").read_text(encoding="utf-8"))
    auto_fixed_ids = {item["rule_id"] for item in report["sections"]["auto_fixed"]}
    assert "FR-4.11-07" in auto_fixed_ids
