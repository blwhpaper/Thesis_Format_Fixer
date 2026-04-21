from __future__ import annotations

import json
from pathlib import Path

import thesis_format_fixer.gui as gui


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("ok", encoding="utf-8")


class _FakeVar:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class _FakeButton:
    def __init__(self) -> None:
        self.state = "disabled"

    def config(self, *, state: str) -> None:
        self.state = state


def _build_headless_gui() -> gui.ThesisFormatFixerGUI:
    app = gui.ThesisFormatFixerGUI.__new__(gui.ThesisFormatFixerGUI)
    app.status_var = _FakeVar()
    app.open_user_summary_button = _FakeButton()
    app.export_user_summary_button = _FakeButton()
    app._last_user_summary_file = None
    return app


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
        user_summary_md = output_dir / "demo.check.user_summary.md"
        _touch(user_summary_md)
        return (
            0,
            {
                "summary": {"reference_finding_count": 2},
                "user_summary": {"overall_status": "已完成", "top_actions": [{"title": "人工复核", "reason": "有未自动修改项"}]},
                "artifacts": {"user_summary_md": str(user_summary_md)},
            },
            report_json_out,
            report_md_out,
        )

    result = gui.execute_gui_task(
        input_file=input_docx,
        output_dir=output_dir,
        mode="check",
        check_runner=_stub_check_runner,
    )

    assert result.success is True
    assert result.mode == "check"
    assert result.exit_code == 0
    assert len(result.generated_files) == 3
    assert result.error_text is None
    formatted = gui.format_gui_result(result)
    assert "中文结果面板" in formatted
    assert "用户版中文摘要" in formatted
    assert "参考文献相关提醒数量" in formatted
    assert "打开用户版摘要" in formatted


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
    assert "Traceback" not in result.error_text


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
    assert "batch_summary_json:" in formatted
    assert "exit_code=0" in formatted
    assert "exit_code=1" in formatted


def test_execute_gui_task_raises_for_missing_input_file(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    missing_docx = tmp_path / "missing.docx"
    try:
        gui.execute_gui_task(input_file=missing_docx, output_dir=output_dir, mode="check")
    except FileNotFoundError as exc:
        assert "输入文件不存在" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected FileNotFoundError")


def test_open_user_summary_when_present(monkeypatch, tmp_path: Path) -> None:
    app = _build_headless_gui()
    summary_file = tmp_path / "demo.user_summary.md"
    summary_file.write_text("summary", encoding="utf-8")
    app._last_user_summary_file = summary_file

    opened: dict[str, Path] = {}

    def _stub_open_file(path: Path) -> None:
        opened["path"] = path

    monkeypatch.setattr(gui, "open_file", _stub_open_file)
    app._open_user_summary()

    assert opened["path"] == summary_file
    assert "已打开用户版摘要" in app.status_var.value


def test_export_user_summary_when_present(monkeypatch, tmp_path: Path) -> None:
    app = _build_headless_gui()
    source_file = tmp_path / "demo.user_summary.md"
    source_file.write_text("summary", encoding="utf-8")
    export_file = tmp_path / "exports" / "copied.user_summary.md"
    app._last_user_summary_file = source_file

    class _Dialog:
        @staticmethod
        def asksaveasfilename(**_kwargs: object) -> str:
            return str(export_file)

    monkeypatch.setattr(gui, "filedialog", _Dialog())
    app._export_user_summary()

    assert export_file.exists()
    assert export_file.read_text(encoding="utf-8") == "summary"
    assert "用户版摘要已导出到" in app.status_var.value


def test_user_summary_actions_show_clear_message_when_missing() -> None:
    app = _build_headless_gui()
    app._last_user_summary_file = None
    app._open_user_summary()
    assert app.status_var.value == "当前没有可打开的用户版摘要，请先执行 check 或 fix。"

    app._export_user_summary()
    assert app.status_var.value == "当前没有可导出的用户版摘要，请先执行 check 或 fix。"


def test_user_summary_action_buttons_state_sync(tmp_path: Path) -> None:
    app = _build_headless_gui()
    app._set_user_summary_action_state()
    assert app.open_user_summary_button.state == "disabled"
    assert app.export_user_summary_button.state == "disabled"

    summary_file = tmp_path / "demo.user_summary.md"
    summary_file.write_text("ok", encoding="utf-8")
    app._last_user_summary_file = summary_file
    app._set_user_summary_action_state()
    assert app.open_user_summary_button.state == "normal"
    assert app.export_user_summary_button.state == "normal"
