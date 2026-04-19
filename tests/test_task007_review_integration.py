from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from thesis_format_fixer.app.runner import _build_single_payload
from thesis_format_fixer.review.model_adapter import StubModelAdapter


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


def _sample_docx(tmp_path: Path) -> Path:
    path = tmp_path / "sample.docx"
    _write_min_docx(
        path,
        body=[
            "CONTENTS",
            "1 Intro",
            "1.1 Scope",
            "REFERENCES",
            "[1] Smith J. Journal of Tests, 2025.",
            "[2] 王强. 测试出版社, 2024.",
        ],
        footer_text="-1-",
    )
    return path


def test_review_mode_off_does_not_change_existing_sections(tmp_path: Path) -> None:
    docx = _sample_docx(tmp_path)
    payload = _build_single_payload(docx, review_mode="off")

    assert "intelligent_review" not in payload["sections"]


def test_review_mode_llm_without_model_degrades_gracefully(tmp_path: Path) -> None:
    docx = _sample_docx(tmp_path)
    payload = _build_single_payload(docx, review_mode="llm")

    review = payload["sections"]["intelligent_review"]
    assert review["status"] == "degraded"
    assert "local_model_not_configured" in review["degraded_reasons"]
    assert review["findings"]


def test_mock_model_valid_verdict_merged_into_report(tmp_path: Path) -> None:
    docx = _sample_docx(tmp_path)
    adapter = StubModelAdapter(
        responses={
            "heading_structure_review": [
                {
                    "rule_id": "FR-4.8-01",
                    "block_id": "body",
                    "block_type": "body.headings",
                    "target": "heading_structure",
                    "decision": "warn",
                    "confidence": 0.61,
                    "evidence": [{"reason": "mock_heading_alert", "snippet": "1.1 Scope", "paragraph_index": 2}],
                    "suggestion": "mock suggestion",
                    "auto_fix_allowed": False,
                    "source": "local_model",
                }
            ],
            "reference_structure_review": [],
            "pagination_review": [],
        }
    )

    payload = _build_single_payload(
        docx,
        review_mode="llm",
        review_local_model="mock",
        model_adapter=adapter,
    )
    review = payload["sections"]["intelligent_review"]

    assert any(item["source"] == "local_model" for item in review["findings"])
    assert any(item["target"] == "heading_structure" for item in review["findings"])


def test_mock_model_invalid_payload_degrades_to_rule_engine(tmp_path: Path) -> None:
    docx = _sample_docx(tmp_path)
    adapter = StubModelAdapter(
        responses={
            "heading_structure_review": "{invalid-json",
            "reference_structure_review": [],
            "pagination_review": [],
        }
    )

    payload = _build_single_payload(
        docx,
        review_mode="llm",
        review_local_model="mock",
        model_adapter=adapter,
    )
    review = payload["sections"]["intelligent_review"]

    assert review["status"] == "degraded"
    assert any(reason.startswith("invalid_json") for reason in review["degraded_reasons"])
    assert any(item["source"] == "rule_engine" for item in review["findings"])


def test_review_pipeline_does_not_modify_input_docx(tmp_path: Path) -> None:
    docx = _sample_docx(tmp_path)
    before = docx.read_bytes()

    _build_single_payload(docx, review_mode="basic")

    after = docx.read_bytes()
    assert after == before


def test_review_mode_basic_reports_body_english_punctuation_findings(tmp_path: Path) -> None:
    docx = tmp_path / "body-punctuation.docx"
    _write_min_docx(
        docx,
        body=[
            "CONTENTS",
            "1 Intro",
            "This line has fullwidth space　inside.",
            "REFERENCES",
            "[1] Smith J. Journal of Tests, 2025.",
        ],
    )

    payload = _build_single_payload(docx, review_mode="basic")
    review = payload["sections"]["intelligent_review"]

    assert any(item["rule_id"] == "FR-4.9-02" for item in review["findings"])
