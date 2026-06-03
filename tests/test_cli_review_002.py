"""Tests for the new CLI review --findings subcommand."""
import json
from pathlib import Path
import pytest

def test_cli_review_happy_path(tmp_path: Path):
    docx = pytest.importorskip("docx")
    
    input_path = tmp_path / "input.docx"
    output_path = tmp_path / "reviewed.docx"
    findings_path = tmp_path / "findings.json"
    report_path = tmp_path / "report.json"
    
    # Create minimal doc
    doc = docx.Document()
    doc.add_paragraph("First paragraph.")
    doc.save(input_path)
    
    # Create findings
    findings = [
        {
            "rule_id": "FR-1.1",
            "category": "Format",
            "severity": "Medium",
            "message": "Use correct font.",
            "anchor_strategy": "paragraph",
            "paragraph_index": 0
        }
    ]
    findings_path.write_text(json.dumps(findings))
    
    # Run CLI
    from thesis_format_fixer.cli import main
    exit_code = main([
        "review",
        "--input", str(input_path),
        "--findings", str(findings_path),
        "--output", str(output_path),
        "--report", str(report_path)
    ])
    
    assert exit_code == 0
    
    # Verify outputs
    assert output_path.exists()
    assert report_path.exists()
    
    report_data = json.loads(report_path.read_text())
    assert report_data["schema_version"] == "review-report-v1"
    assert report_data["apply_summary"]["added"] == 1
    
    reopened = docx.Document(output_path)
    assert len(reopened.comments) == 1
    
def test_cli_review_missing_input(tmp_path: Path):
    from thesis_format_fixer.cli import main
    input_path = tmp_path / "missing.docx"
    findings_path = tmp_path / "findings.json"
    findings_path.write_text("[]")
    
    exit_code = main([
        "review",
        "--input", str(input_path),
        "--findings", str(findings_path),
        "--output", str(tmp_path / "out.docx"),
        "--report", str(tmp_path / "out.json")
    ])
    assert exit_code == 1
    
def test_cli_review_invalid_json(tmp_path: Path):
    docx = pytest.importorskip("docx")
    from thesis_format_fixer.cli import main
    input_path = tmp_path / "in.docx"
    docx.Document().save(input_path)
    
    findings_path = tmp_path / "findings.json"
    findings_path.write_text("NOT JSON")
    
    exit_code = main([
        "review",
        "--input", str(input_path),
        "--findings", str(findings_path),
        "--output", str(tmp_path / "out.docx"),
        "--report", str(tmp_path / "out.json")
    ])
    assert exit_code == 1

def test_cli_review_invalid_finding_format(tmp_path: Path):
    docx = pytest.importorskip("docx")
    from thesis_format_fixer.cli import main
    input_path = tmp_path / "in.docx"
    docx.Document().save(input_path)
    
    findings_path = tmp_path / "findings.json"
    findings_path.write_text('[{"missing": "required_fields"}]')
    
    exit_code = main([
        "review",
        "--input", str(input_path),
        "--findings", str(findings_path),
        "--output", str(tmp_path / "out.docx"),
        "--report", str(tmp_path / "out.json")
    ])
    assert exit_code == 1
