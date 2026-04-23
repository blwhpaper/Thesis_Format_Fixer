from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient

from thesis_format_fixer.api.app import create_app
from thesis_format_fixer.api.service import ApiJobService


def _build_minimal_docx_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Abstract</w:t></w:r></w:p>
    <w:p><w:r><w:t>Hello thesis.</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>""",
        )
    return buffer.getvalue()


def test_api_check_and_read_job(tmp_path: Path) -> None:
    app = create_app(service=ApiJobService(tmp_path / "jobs"))
    client = TestClient(app)

    response = client.post(
        "/api/jobs/check",
        files={"file": ("demo.docx", _build_minimal_docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["mode"] == "check"
    assert payload["input_filename"] == "demo.docx"
    assert payload["output_filename"] is None
    assert payload["artifacts"]["report_md"] is not None
    assert payload["user_summary"]["categorized"]["manual_review_required"] is not None

    job_id = payload["job_id"]
    job_response = client.get(f"/api/jobs/{job_id}")
    assert job_response.status_code == 200
    assert job_response.json()["job_id"] == job_id

    report_response = client.get(f"/api/jobs/{job_id}/download/report-md")
    assert report_response.status_code == 200
    assert "Thesis Format Fixer Report" in report_response.text


def test_api_fix_exposes_downloadable_docx(tmp_path: Path) -> None:
    app = create_app(service=ApiJobService(tmp_path / "jobs"))
    client = TestClient(app)

    response = client.post(
        "/api/jobs/fix",
        files={"file": ("demo.docx", _build_minimal_docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["mode"] == "fix"
    assert payload["output_filename"] == "demo.fixed.docx"
    assert payload["artifacts"]["fixed_docx"] is not None

    download_response = client.get(f"/api/jobs/{payload['job_id']}/download/fixed-docx")
    assert download_response.status_code == 200
    assert download_response.content[:2] == b"PK"


def test_api_rejects_non_docx_input(tmp_path: Path) -> None:
    app = create_app(service=ApiJobService(tmp_path / "jobs"))
    client = TestClient(app)

    response = client.post("/api/jobs/check", files={"file": ("demo.txt", b"hello", "text/plain")})

    assert response.status_code == 400
    payload = response.json()
    assert payload["status"] == "failed"
    assert "docx" in payload["error"]


def test_api_rejects_empty_docx_input(tmp_path: Path) -> None:
    app = create_app(service=ApiJobService(tmp_path / "jobs"))
    client = TestClient(app)

    response = client.post(
        "/api/jobs/check",
        files={"file": ("empty.docx", b"", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["status"] == "failed"
    assert "empty" in payload["error"]
