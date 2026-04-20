from __future__ import annotations

import json
from pathlib import Path

from thesis_format_fixer.app.runner import run_batch_fix, run_fix
from thesis_format_fixer.cli import main


def _create_fake_docx(path: Path, *, text: str = "fake-docx") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def test_run_fix_writes_docx_and_reports(tmp_path: Path) -> None:
    input_file = tmp_path / "input.docx"
    output_file = tmp_path / "out" / "input.fixed.docx"
    _create_fake_docx(input_file)

    code = run_fix(input_file, output_file)
    assert code == 0
    assert output_file.exists()

    report_json = output_file.with_suffix(".report.json")
    report_md = output_file.with_suffix(".report.md")
    assert report_json.exists()
    assert report_md.exists()

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "task-006-report-v1"
    assert payload["input_file"] == str(input_file)
    assert payload["output_docx"] == str(output_file)
    assert "sections" in payload
    assert set(payload["sections"]) == {
        "auto_fixed",
        "auto_fixed_footnotes",
        "auto_fixed_bibliography",
        "detected_not_auto_modified",
        "detected_special_issues_not_modified",
        "a_class_hit_surface",
        "references_diagnostics",
        "reference_review",
        "manual_review_required",
    }


def test_run_batch_fix_outputs_per_file_and_summary(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    _create_fake_docx(input_dir / "a.docx")
    _create_fake_docx(input_dir / "nested" / "b.docx")
    (input_dir / "ignored.txt").write_text("skip", encoding="utf-8")

    code = run_batch_fix(input_dir, output_dir, recursive=True)
    assert code == 0

    assert (output_dir / "a.fixed.docx").exists()
    assert (output_dir / "a.report.json").exists()
    assert (output_dir / "nested" / "b.fixed.docx").exists()
    assert (output_dir / "nested" / "b.report.json").exists()

    summary_json = output_dir / "batch_summary.json"
    summary_md = output_dir / "batch_summary.md"
    assert summary_json.exists()
    assert summary_md.exists()

    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    assert summary["schema_version"] == "task-005-batch-summary-v1"
    assert summary["total_files"] == 2
    assert summary["succeeded"] == 2
    assert summary["failed"] == 0
    assert len(summary["items"]) == 2


def test_cli_batch_fix_non_recursive(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    _create_fake_docx(input_dir / "top.docx")
    _create_fake_docx(input_dir / "sub" / "nested.docx")

    code = main(
        [
            "batch-fix",
            str(input_dir),
            "--out-dir",
            str(output_dir),
            "--no-recursive",
        ]
    )
    assert code == 0

    assert (output_dir / "top.fixed.docx").exists()
    assert not (output_dir / "sub" / "nested.fixed.docx").exists()


def test_run_batch_fix_empty_input_dir_returns_2_and_writes_summary(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / "out"

    code = run_batch_fix(input_dir, output_dir, recursive=True)
    assert code == 2

    summary_json = output_dir / "batch_summary.json"
    assert summary_json.exists()
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    assert summary["total_files"] == 0
    assert summary["warning"] == "输入目录中未找到 .docx 文件"


def test_run_batch_fix_output_dir_not_writable_like_file_path(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir(parents=True, exist_ok=True)
    _create_fake_docx(input_dir / "a.docx")

    output_dir = tmp_path / "occupied"
    output_dir.write_text("not-a-dir", encoding="utf-8")

    code = run_batch_fix(input_dir, output_dir, recursive=True)
    assert code == 2


def test_run_fix_rejects_non_docx_output_path(tmp_path: Path) -> None:
    input_file = tmp_path / "input.docx"
    _create_fake_docx(input_file)
    output_file = tmp_path / "out" / "input.fixed.txt"

    code = run_fix(input_file, output_file)
    assert code == 2
