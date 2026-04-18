from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from thesis_format_fixer.app.runner import run_check


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


def test_task008_report_exposes_unhit_a_rules(tmp_path: Path) -> None:
    input_docx = tmp_path / "minimal.docx"
    _write_min_docx(input_docx, body=["Only one paragraph."])

    report_json = tmp_path / "minimal.report.json"
    report_md = tmp_path / "minimal.report.md"
    assert run_check(input_docx, report_json_out=report_json, report_md_out=report_md) == 0

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    a_surface = payload["sections"]["a_class_hit_surface"]

    unhit_ids = {item["rule_id"] for item in a_surface["unhit"]}
    assert "FR-4.2-01" in unhit_ids
    assert "FR-4.12-01" in unhit_ids
    assert len(unhit_ids) >= 5

    md = report_md.read_text(encoding="utf-8")
    assert "## A 类命中面" in md
    assert "未命中" in md
