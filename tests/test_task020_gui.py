from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def test_default_gui_output_dir_uses_stable_user_path() -> None:
    output_dir = gui.default_gui_output_dir()
    assert output_dir.is_absolute()
    assert output_dir.name == "ThesisFormatFixerOutput"


def test_main_raises_clear_error_when_pyside6_is_unavailable() -> None:
    if gui._PYSIDE6_IMPORT_ERROR is None:
        return

    try:
        gui.main()
    except RuntimeError as exc:
        assert "PySide6 unavailable" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected RuntimeError")


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
                "summary": {
                    "reference_finding_count": 2,
                    "reference_blocking_count": 1,
                    "block_low_confidence_count": 0,
                },
                "user_summary": {
                    "overall_status": "已完成",
                    "reference_blocking_count": 1,
                    "top_actions": [{"title": "人工复核", "reason": "有未自动修改项"}],
                },
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
    assert "GUI 用户版结果面板" in formatted
    assert "概览结果" in formatted
    assert "分类结果" in formatted
    assert "参考文献相关提醒" in formatted
    assert "参考文献阻断" in formatted
    assert "打开摘要文件" in formatted
    assert "技术字段（次级展示）" in formatted


def test_format_gui_result_fix_shows_three_artifact_exits(tmp_path: Path) -> None:
    input_docx = tmp_path / "demo.docx"
    output_dir = tmp_path / "out"
    fixed_docx = output_dir / "demo.fixed.docx"
    report_md = output_dir / "demo.report.md"
    report_json = output_dir / "demo.report.json"
    user_summary_md = output_dir / "demo.user_summary.md"
    for path in (fixed_docx, report_md, report_json, user_summary_md):
        _touch(path)

    result = gui.GuiExecutionResult(
        mode="fix",
        input_file=input_docx,
        output_dir=output_dir,
        success=True,
        exit_code=0,
        generated_files=(fixed_docx, report_json, report_md, user_summary_md),
        payload={
            "summary": {
                "auto_fix_rule_count": 1,
                "detected_not_auto_modified_count": 0,
                "manual_review_required_count": 0,
                "reference_finding_count": 0,
                "reference_blocking_count": 0,
                "block_low_confidence_count": 0,
            },
            "user_summary": {
                "processing_type": "fix",
                "processing_label": "修复",
                "overall_status": "已完成修复",
                "reference_blocking_count": 0,
                "category_summaries": [
                    {"category_title": "已自动修复 / 已自动处理", "count": 1, "description": "系统已完成安全范围内的自动处理。"}
                ],
                "technical_summary": {
                    "auto_fix_rule_count": 1,
                    "detected_not_auto_modified_count": 0,
                    "manual_review_required_count": 0,
                    "reference_finding_count": 0,
                    "reference_blocking_count": 0,
                    "block_low_confidence_count": 0,
                },
            },
            "artifacts": {
                "fixed_docx": str(fixed_docx),
                "technical_report_md": str(report_md),
                "technical_report_json": str(report_json),
                "user_summary_md": str(user_summary_md),
            },
        },
    )
    formatted = gui.format_gui_result(result)
    assert "查看与导出" in formatted
    assert "修复后 docx" in formatted
    assert "技术版报告（Markdown）" in formatted
    assert "打开摘要文件" in formatted
    assert "打开输出目录" in formatted


def test_execute_gui_task_rejects_non_docx_input(tmp_path: Path) -> None:
    input_txt = tmp_path / "demo.txt"
    input_txt.write_text("fake", encoding="utf-8")

    with pytest.raises(ValueError, match=r"\.docx"):
        gui.execute_gui_task(
            input_file=input_txt,
            output_dir=tmp_path / "out",
            mode="check",
        )


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
    assert "GUI 批量修复结果面板" in formatted
    assert "处理文件总数：2" in formatted
    assert "成功数量：1" in formatted
    assert "失败数量：1" in formatted
    assert "批处理汇总 JSON：" in formatted
    assert "逐文件结果" in formatted
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


def test_execute_gui_task_raises_for_non_docx_input(tmp_path: Path) -> None:
    input_file = tmp_path / "demo.txt"
    input_file.write_text("hello", encoding="utf-8")

    try:
        gui.execute_gui_task(input_file=input_file, output_dir=tmp_path / "out", mode="check")
    except ValueError as exc:
        assert "输入文件必须是 .docx" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected ValueError")


def test_execute_gui_task_returns_localized_error_for_invalid_output_path(tmp_path: Path) -> None:
    input_docx = tmp_path / "demo.docx"
    input_docx.write_bytes(b"fake")
    output_as_file = tmp_path / "occupied"
    output_as_file.write_text("not-a-dir", encoding="utf-8")

    result = gui.execute_gui_task(input_file=input_docx, output_dir=output_as_file, mode="check")

    assert result.success is False
    assert result.error_text is not None
    assert "输出目录不可创建" in result.error_text


def test_execute_gui_batch_task_empty_input_dir_shows_warning_without_raw_runner_error(tmp_path: Path) -> None:
    input_dir = tmp_path / "empty"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / "out"

    def _stub_batch_runner(
        _input_dir: Path,
        _output_dir: Path,
        *,
        recursive: bool = True,
    ) -> int:
        payload = {
            "schema_version": "task-005-batch-summary-v1",
            "input_dir": str(_input_dir),
            "output_dir": str(_output_dir),
            "total_files": 0,
            "succeeded": 0,
            "failed": 0,
            "warning": "输入目录中未找到 .docx 文件",
            "items": [],
        }
        _output_dir.mkdir(parents=True, exist_ok=True)
        (_output_dir / "batch_summary.json").write_text(json.dumps(payload), encoding="utf-8")
        return 2

    result = gui.execute_gui_batch_task(
        input_dir=input_dir,
        output_dir=output_dir,
        batch_runner=_stub_batch_runner,
    )

    assert result.success is False
    assert result.total_files == 0
    assert result.error_text is None
    formatted = gui.format_gui_batch_result(result)
    assert "提示：输入目录中未找到 .docx 文件" in formatted
    assert "Runner exit code" not in formatted


def test_execute_gui_batch_task_returns_localized_error_for_invalid_output_path(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_as_file = tmp_path / "occupied"
    output_as_file.write_text("not-a-dir", encoding="utf-8")

    result = gui.execute_gui_batch_task(input_dir=input_dir, output_dir=output_as_file)

    assert result.success is False
    assert result.error_text is not None
    assert "输出目录不可创建" in result.error_text


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


def test_filter_batch_import_paths_ignores_non_docx_files(tmp_path: Path) -> None:
    paths = (
        tmp_path / "a.docx",
        tmp_path / "b.txt",
        tmp_path / "c.DOCX",
        tmp_path / "d.md",
    )
    selected, ignored = gui.filter_batch_import_paths(paths)

    assert selected == (tmp_path / "a.docx", tmp_path / "c.DOCX")
    assert ignored == ("b.txt", "d.md")


def test_execute_gui_batch_queue_tracks_status_flow_and_result_visibility(tmp_path: Path) -> None:
    input_a = tmp_path / "a.docx"
    input_b = tmp_path / "b.docx"
    input_a.write_bytes(b"a")
    input_b.write_bytes(b"b")
    output_dir = tmp_path / "out"

    progress: list[gui.BatchTaskRecord] = []

    def _stub_check_runner(
        input_file: Path,
        *,
        report_json_out: Path | None = None,
        report_md_out: Path | None = None,
    ) -> tuple[int, dict, Path | None, Path | None]:
        assert report_json_out is not None
        assert report_md_out is not None
        _touch(report_json_out)
        _touch(report_md_out)
        if input_file.name == "a.docx":
            user_summary_md = report_md_out.parent / "a.user_summary.md"
            user_summary_md.write_text("# 用户版结果摘要\n\n已完成检查，当前未发现需要你额外处理的问题", encoding="utf-8")
            return (
                0,
                {
                    "summary": {
                        "auto_fix_rule_count": 0,
                        "detected_not_auto_modified_count": 0,
                        "manual_review_required_count": 0,
                    },
                    "user_summary": {
                        "overall_status": "已完成检查，当前未发现需要你额外处理的问题",
                    },
                    "artifacts": {
                        "technical_report_md": str(report_md_out),
                        "technical_report_json": str(report_json_out),
                        "user_summary_md": str(user_summary_md),
                    },
                },
                report_json_out,
                report_md_out,
            )
        raise RuntimeError("boom: 模拟失败")

    result = gui.execute_gui_batch_queue(
        input_files=(input_a, input_b),
        output_dir=output_dir,
        mode="check",
        progress_callback=progress.append,
        check_runner=_stub_check_runner,
    )

    assert result.total_files == 2
    assert result.succeeded == 1
    assert result.failed == 1
    assert [item.status for item in result.tasks] == ["success", "failed"]
    assert result.tasks[0].started_at is not None
    assert result.tasks[0].finished_at is not None
    assert result.tasks[0].summary == "已完成检查，当前未发现需要你额外处理的问题"
    assert result.tasks[1].error_message is not None
    assert "boom:" in result.tasks[1].error_message

    progress_statuses = [(item.file_name, item.status) for item in progress]
    assert ("a.docx", "running") in progress_statuses
    assert ("a.docx", "success") in progress_statuses
    assert ("b.docx", "running") in progress_statuses
    assert ("b.docx", "failed") in progress_statuses

    queue_text = gui.format_gui_batch_queue_result(result)
    assert "a.docx | success | 已完成检查" in queue_text
    assert "b.docx | failed | 处理失败：boom:" in queue_text

    success_detail = gui.format_batch_task_detail(result.tasks[0])
    failed_detail = gui.format_batch_task_detail(result.tasks[1])
    assert "中文结果摘要" in success_detail
    assert "已完成检查，当前未发现需要你额外处理的问题" in success_detail
    assert "错误信息" in failed_detail
    assert "boom: 模拟失败" in failed_detail
