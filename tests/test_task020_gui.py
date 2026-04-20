from __future__ import annotations

import json
from pathlib import Path

import thesis_format_fixer.gui as gui


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("ok", encoding="utf-8")


def test_gui_module_importable() -> None:
    assert gui is not None


def test_execute_gui_task_check_success_path(tmp_path: Path) -> None:
    input_docx = tmp_path / "demo.docx"
    input_docx.write_bytes(b"fake")
    output_dir = tmp_path / "out"

    def _stub_check_runner(
        input_file: Path,
        *,
        report_json_out: Path | None = None,
        report_md_out: Path | None = None,
    ) -> tuple[int, dict, Path | None, Path | None]:
        assert input_file == input_docx
        assert report_json_out is not None
        assert report_md_out is not None
        _touch(report_json_out)
        _touch(report_md_out)
        return 0, {"summary": {"reference_finding_count": 2}}, report_json_out, report_md_out

    result = gui.execute_gui_task(
        input_file=input_docx,
        output_dir=output_dir,
        mode="check",
        check_runner=_stub_check_runner,
    )

    assert result.success is True
    assert result.mode == "check"
    assert result.exit_code == 0
    assert len(result.generated_files) == 2
    assert result.error_text is None
    assert "reference_finding_count" in gui.format_gui_result(result)


def test_execute_gui_task_fix_failure_path(tmp_path: Path) -> None:
    input_docx = tmp_path / "demo.docx"
    input_docx.write_bytes(b"fake")
    output_dir = tmp_path / "out"

    def _stub_fix_runner(
        input_file: Path,
        output_file: Path,
        *,
        report_json_out: Path | None = None,
        report_md_out: Path | None = None,
    ) -> tuple[int, dict, Path | None, Path | None]:
        raise RuntimeError(f"boom: {input_file} -> {output_file}")

    result = gui.execute_gui_task(
        input_file=input_docx,
        output_dir=output_dir,
        mode="fix",
        fix_runner=_stub_fix_runner,
    )

    assert result.success is False
    assert result.mode == "fix"
    assert result.exit_code == 1
    assert result.error_text is not None
    assert "boom:" in result.error_text


def test_execute_gui_batch_task_and_format_result(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "a.docx").write_bytes(b"a")
    (input_dir / "b.docx").write_bytes(b"b")
    output_dir = tmp_path / "out"

    def _stub_batch_runner(
        _input_dir: Path,
        _output_dir: Path,
        *,
        recursive: bool = True,
    ) -> int:
        assert _input_dir == input_dir
        assert _output_dir == output_dir
        assert recursive is True
        payload = {
            "schema_version": "task-005-batch-summary-v1",
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "total_files": 2,
            "succeeded": 1,
            "failed": 1,
            "items": [
                {
                    "input_file": str(input_dir / "a.docx"),
                    "output_docx": str(output_dir / "a.fixed.docx"),
                    "exit_code": 0,
                },
                {
                    "input_file": str(input_dir / "b.docx"),
                    "output_docx": str(output_dir / "b.fixed.docx"),
                    "exit_code": 1,
                },
            ],
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "batch_summary.json").write_text(json.dumps(payload), encoding="utf-8")
        return 1

    result = gui.execute_gui_batch_task(
        input_dir=input_dir,
        output_dir=output_dir,
        batch_runner=_stub_batch_runner,
    )

    assert result.success is False
    assert result.exit_code == 1
    assert result.total_files == 2
    assert result.succeeded == 1
    assert result.failed == 1
    assert len(result.items) == 2

    formatted = gui.format_gui_batch_result(result)
    assert "mode: batch-fix" in formatted
    assert "total_files: 2" in formatted
    assert "succeeded: 1" in formatted
    assert "failed: 1" in formatted
    assert "exit_code=0" in formatted
    assert "exit_code=1" in formatted
