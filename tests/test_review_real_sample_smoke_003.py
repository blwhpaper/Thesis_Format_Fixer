"""Real sample smoke test for review pipeline (TASK-THESIS-P2-003)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from thesis_format_fixer.cli import main


@pytest.fixture
def realistic_sample_docx(tmp_path: Path) -> Path:
    """Generates a realistic, sanitized .docx fixture for smoke testing."""
    docx = pytest.importorskip("docx")
    doc = docx.Document()

    # 1. Title / Cover
    doc.add_heading("Thesis Title", level=0)
    doc.add_paragraph("Originality Statement...")
    doc.add_paragraph("Authorization Statement...")
    
    # 2. Chinese Abstract & Keywords
    doc.add_heading("摘要", level=1)
    doc.add_paragraph("这是一篇测试论文。")
    doc.add_paragraph("关键词：测试，烟雾测试")
    
    # 3. English Abstract & Keywords
    doc.add_heading("Abstract", level=1)
    doc.add_paragraph("This is a test thesis.")
    doc.add_paragraph("Key Words: Test, Smoke Test")
    
    # 4. CONTENTS
    doc.add_heading("CONTENTS", level=1)
    
    # 5. Body
    doc.add_heading("1. Introduction", level=1)
    doc.add_paragraph("Introduction paragraph.")
    
    doc.add_heading("1.1 Subheading", level=2)
    doc.add_paragraph("This is the main body paragraph where we will anchor a finding.")
    
    # 6. References
    doc.add_heading("REFERENCES", level=1)
    doc.add_paragraph("[1] Smith J. Testing. 2020.")
    doc.add_paragraph("[2] 张三. 测试. 2021.")
    
    # 7. Appendix
    doc.add_heading("APPENDIX", level=1)
    
    # 8. Acknowledgement / 致谢
    doc.add_heading("Acknowledgements", level=1)
    doc.add_paragraph("Thank you.")
    
    output_path = tmp_path / "realistic_sample.docx"
    doc.save(output_path)
    return output_path


def test_review_real_sample_smoke(tmp_path: Path, realistic_sample_docx: Path) -> None:
    """Smoke test running the review --findings command against a realistic docx."""
    docx = pytest.importorskip("docx")
    
    # 1. Find the target paragraph index programmatically
    doc = docx.Document(realistic_sample_docx)
    target_index = -1
    for i, p in enumerate(doc.paragraphs):
        if "This is the main body paragraph where we will anchor a finding" in p.text:
            target_index = i
            break
            
    assert target_index != -1, "Target paragraph not found in fixture"
    
    # 2. Setup inputs and outputs
    findings_path = tmp_path / "findings.json"
    output_docx = tmp_path / "reviewed_sample.docx"
    report_json = tmp_path / "report.json"
    
    findings = [
        {
            "rule_id": "SMOKE-1",
            "category": "Format",
            "severity": "Medium",
            "message": "Smoke test finding on body paragraph.",
            "anchor_strategy": "paragraph",
            "paragraph_index": target_index
        }
    ]
    findings_path.write_text(json.dumps(findings, ensure_ascii=False), encoding="utf-8")
    
    # 3. Run CLI
    exit_code = main([
        "review",
        "--input", str(realistic_sample_docx),
        "--findings", str(findings_path),
        "--output", str(output_docx),
        "--report", str(report_json)
    ])
    
    assert exit_code == 0
    
    # 4. Verify report artifact
    assert report_json.exists()
    report_data = json.loads(report_json.read_text(encoding="utf-8"))
    
    assert report_data["schema_version"] == "review-report-v1"
    assert report_data["apply_summary"]["total"] == 1
    assert report_data["apply_summary"]["added"] == 1
    
    # 5. Verify the docx is valid and contains the comment
    assert output_docx.exists()
    reopened = docx.Document(output_docx)
    
    comments = list(reopened.comments)
    assert len(comments) == 1
    assert "[TFF-RULE:SMOKE-1]" in comments[0].text
    
    # Ensure all original content is preserved (smoke check)
    original_texts = [p.text for p in doc.paragraphs]
    reopened_texts = [p.text for p in reopened.paragraphs]
    assert original_texts == reopened_texts
