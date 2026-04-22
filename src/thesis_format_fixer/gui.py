"""PySide6 desktop host for thesis-format-fixer."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from thesis_format_fixer.app.runner import run_batch_fix, run_check_with_details, run_fix_with_details
from thesis_format_fixer.reporters.report_builder import build_user_result_summary, render_user_summary_markdown
from thesis_format_fixer.runtime_paths import default_output_dir

try:
    from PySide6.QtCore import QObject, Qt, QThread, Signal
    from PySide6.QtGui import QAction, QTextOption
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QStatusBar,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:  # pragma: no cover - import environment dependent
    QApplication = None
    QCheckBox = None
    QComboBox = None
    QFileDialog = None
    QFormLayout = None
    QGroupBox = None
    QHBoxLayout = None
    QLabel = None
    QLineEdit = None
    QListWidget = None
    QListWidgetItem = None
    QMainWindow = object
    QMessageBox = None
    QObject = object
    QPushButton = None
    QSizePolicy = None
    QSplitter = None
    QStatusBar = None
    QTextEdit = None
    QTextOption = None
    QThread = None
    Qt = None
    QVBoxLayout = None
    QWidget = None
    QAction = None
    Signal = None
    _PYSIDE6_IMPORT_ERROR = exc
else:
    _PYSIDE6_IMPORT_ERROR = None


RunnerWithDetails = Callable[..., tuple[int, dict[str, Any], Path | None, Path | None]]
BatchRunner = Callable[..., int]


@dataclass(frozen=True, slots=True)
class GuiExecutionResult:
    mode: str
    input_file: Path
    output_dir: Path
    success: bool
    exit_code: int
    generated_files: tuple[Path, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    error_text: str | None = None


@dataclass(frozen=True, slots=True)
class GuiBatchExecutionResult:
    input_dir: Path
    output_dir: Path
    recursive: bool
    success: bool
    exit_code: int
    total_files: int
    succeeded: int
    failed: int
    items: tuple[dict[str, Any], ...] = ()
    summary_payload: dict[str, Any] = field(default_factory=dict)
    error_text: str | None = None


class _DialogBridge:
    def askopenfilename(self, **kwargs: object) -> str:
        if QFileDialog is None:
            return ""
        parent = kwargs.get("parent")
        title = str(kwargs.get("title", "选择文件"))
        filter_spec = "Word Document (*.docx);;All Files (*)"
        selected, _ = QFileDialog.getOpenFileName(parent, title, "", filter_spec)
        return selected

    def askdirectory(self, **kwargs: object) -> str:
        if QFileDialog is None:
            return ""
        parent = kwargs.get("parent")
        title = str(kwargs.get("title", "选择目录"))
        return QFileDialog.getExistingDirectory(parent, title)

    def asksaveasfilename(self, **kwargs: object) -> str:
        if QFileDialog is None:
            return ""
        parent = kwargs.get("parent")
        title = str(kwargs.get("title", "导出文件"))
        initial = str(kwargs.get("initialfile", "result.md"))
        selected, _ = QFileDialog.getSaveFileName(
            parent,
            title,
            initial,
            "Markdown (*.md);;All Files (*)",
        )
        return selected


class _MessageBoxBridge:
    def showerror(self, title: str, text: str, *, parent: object | None = None) -> None:
        if QMessageBox is None:
            return
        QMessageBox.critical(parent, title, text)

    def showwarning(self, title: str, text: str, *, parent: object | None = None) -> None:
        if QMessageBox is None:
            return
        QMessageBox.warning(parent, title, text)

    def showinformation(self, title: str, text: str, *, parent: object | None = None) -> None:
        if QMessageBox is None:
            return
        QMessageBox.information(parent, title, text)


class _StatusVarAdapter:
    def __init__(self, callback: Callable[[str], None] | None = None) -> None:
        self._value = ""
        self._callback = callback

    def set(self, value: str) -> None:
        self._value = value
        if self._callback is not None:
            self._callback(value)

    def get(self) -> str:
        return self._value


filedialog: object | None = _DialogBridge()
messagebox: object | None = _MessageBoxBridge()


def default_gui_output_dir() -> Path:
    return default_output_dir()


def _ensure_gui_output_directory_writable(output_dir: Path) -> None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except FileExistsError as exc:
        raise PermissionError(f"输出目录不可创建: {output_dir}") from exc
    except OSError as exc:
        raise PermissionError(f"输出目录不可创建: {output_dir}") from exc

    probe_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_dir,
            prefix=".gui_write_probe_",
            suffix=".tmp",
            delete=False,
        ) as handle:
            probe_path = Path(handle.name)
    except OSError as exc:
        raise PermissionError(f"输出目录不可写: {output_dir}") from exc
    finally:
        if probe_path is not None and probe_path.exists():
            probe_path.unlink(missing_ok=True)


def _localize_gui_error(exc: Exception) -> str:
    if isinstance(exc, PermissionError):
        return str(exc)
    if isinstance(exc, FileNotFoundError):
        return str(exc)
    if isinstance(exc, IsADirectoryError):
        return str(exc)
    if isinstance(exc, ValueError):
        return str(exc)
    return f"处理失败：{exc}"


def _default_report_paths(input_file: Path, output_dir: Path, mode: str) -> tuple[Path, Path]:
    if mode == "check":
        report_stem = f"{input_file.stem}.check.report"
        return output_dir / f"{report_stem}.json", output_dir / f"{report_stem}.md"
    output_docx = output_dir / f"{input_file.stem}.fixed.docx"
    return output_docx.with_suffix(".report.json"), output_docx.with_suffix(".report.md")


def execute_gui_task(
    *,
    input_file: Path,
    output_dir: Path,
    mode: str,
    check_runner: RunnerWithDetails = run_check_with_details,
    fix_runner: RunnerWithDetails = run_fix_with_details,
) -> GuiExecutionResult:
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"check", "fix"}:
        raise ValueError(f"Unsupported mode: {mode}")
    if not input_file.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_file}")
    if input_file.is_dir():
        raise ValueError(f"输入路径不能是目录: {input_file}")
    if input_file.suffix.lower() != ".docx":
        raise ValueError("输入文件必须是 .docx")

    try:
        _ensure_gui_output_directory_writable(output_dir)
        report_json, report_md = _default_report_paths(input_file, output_dir, normalized_mode)
        generated_files: list[Path] = []
        if normalized_mode == "check":
            code, payload, _, _ = check_runner(
                input_file,
                report_json_out=report_json,
                report_md_out=report_md,
            )
            generated_files.extend([report_json, report_md])
        else:
            output_docx = output_dir / f"{input_file.stem}.fixed.docx"
            code, payload, _, _ = fix_runner(
                input_file,
                output_docx,
                report_json_out=report_json,
                report_md_out=report_md,
            )
            generated_files.extend([output_docx, report_json, report_md])

        artifacts = payload.get("artifacts", {}) if isinstance(payload, dict) else {}
        user_summary_path_raw = artifacts.get("user_summary_md") if isinstance(artifacts, dict) else None
        if isinstance(user_summary_path_raw, str) and user_summary_path_raw.strip():
            generated_files.append(Path(user_summary_path_raw))
    except Exception as exc:
        return GuiExecutionResult(
            mode=normalized_mode,
            input_file=input_file,
            output_dir=output_dir,
            success=False,
            exit_code=1,
            generated_files=tuple(path for path in locals().get("generated_files", []) if path.exists()),
            payload={},
            error_text=_localize_gui_error(exc),
        )

    existing_files = tuple(path for path in generated_files if path.exists())
    return GuiExecutionResult(
        mode=normalized_mode,
        input_file=input_file,
        output_dir=output_dir,
        success=(code == 0),
        exit_code=code,
        generated_files=existing_files,
        payload=payload,
        error_text=None if code == 0 else f"Runner exit code: {code}",
    )


def format_gui_result(result: GuiExecutionResult) -> str:
    summary = result.payload.get("summary", {})
    user_summary = result.payload.get("user_summary", {})
    artifacts = result.payload.get("artifacts", {}) if isinstance(result.payload, dict) else {}
    processing_label = "修复" if result.mode == "fix" else "检查"
    lines = [
        "GUI 用户版结果面板",
        f"- 本次操作类型：{result.mode}",
        f"- 操作说明：{processing_label}",
        f"- 输入文件：{result.input_file}",
        f"- 输出目录：{result.output_dir}",
        f"- 执行状态：{'成功' if result.success else '失败'}（exit_code={result.exit_code}）",
    ]

    if isinstance(user_summary, dict) and user_summary:
        lines.extend(
            [
                "",
                "概览结果",
                f"- 总体状态：{user_summary.get('overall_status', '')}",
                "- 已自动修复 / 已自动处理："
                + str(user_summary.get('auto_fixed_count', summary.get('auto_fix_rule_count', 0))),
                "- "
                + "检测到异常但未自动修改："
                + str(
                    user_summary.get(
                        "detected_not_auto_modified_count",
                        summary.get("detected_not_auto_modified_count", 0),
                    )
                ),
                f"- 需要人工复核：{user_summary.get('manual_review_required_count', summary.get('manual_review_required_count', 0))}",
                f"- 参考文献相关提醒：{user_summary.get('reference_reminder_count', summary.get('reference_finding_count', 0))}",
                f"- 脚注相关提醒：{user_summary.get('footnote_reminder_count', 0)}",
                f"- 其他提示：{user_summary.get('other_reminder_count', 0)}",
            ]
        )
        category_summaries = user_summary.get("category_summaries", [])
        lines.extend(["", "分类结果"])
        if isinstance(category_summaries, list) and category_summaries:
            for item in category_summaries:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("category_title", "")).strip()
                count = item.get("count", 0)
                description = str(item.get("description", "")).strip()
                if title:
                    lines.append(f"- {title}：{count} 项。{description}")
        else:
            lines.extend(
                [
                    "- 已自动修复 / 已自动处理："
                    + str(user_summary.get("auto_fixed_count", summary.get("auto_fix_rule_count", 0))),
                    "- 检测到异常但未自动修改："
                    + str(
                        user_summary.get(
                            "detected_not_auto_modified_count",
                            summary.get("detected_not_auto_modified_count", 0),
                        )
                    ),
                    "- 需要人工复核："
                    + str(
                        user_summary.get(
                            "manual_review_required_count",
                            summary.get("manual_review_required_count", 0),
                        )
                    ),
                ]
            )
        key_issues = user_summary.get("key_issues", [])
        if isinstance(key_issues, list) and key_issues:
            lines.append("- 结果概览补充：")
            lines.extend(f"  - {item}" for item in key_issues if isinstance(item, str) and item.strip())
        next_steps = user_summary.get("next_steps", [])
        if isinstance(next_steps, list) and next_steps:
            lines.append("- 建议下一步：")
            lines.extend(f"  - {item}" for item in next_steps if isinstance(item, str) and item.strip())
    elif summary:
        lines.append(
            "\n概览结果\n"
            + f"- 已自动修复 / 已自动处理：{summary.get('auto_fix_rule_count', 0)}\n"
            + f"- 检测到异常但未自动修改：{summary.get('detected_not_auto_modified_count', 0)}\n"
            + f"- 需要人工复核：{summary.get('manual_review_required_count', 0)}\n"
            + f"- 参考文献相关提醒：{summary.get('reference_finding_count', 0)}"
        )

    lines.extend(["", "查看与导出"])
    fixed_docx = artifacts.get("fixed_docx") if isinstance(artifacts, dict) else None
    report_md = artifacts.get("technical_report_md") if isinstance(artifacts, dict) else None
    report_json = artifacts.get("technical_report_json") if isinstance(artifacts, dict) else None
    if not report_md and isinstance(artifacts, dict):
        report_md = artifacts.get("report_md")
    if not report_json and isinstance(artifacts, dict):
        report_json = artifacts.get("report_json")
    user_summary_md = artifacts.get("user_summary_md") if isinstance(artifacts, dict) else None
    if isinstance(fixed_docx, str) and fixed_docx.strip():
        lines.append(f"- 修复后 docx：{fixed_docx}")
    if isinstance(report_md, str) and report_md.strip():
        lines.append(f"- 技术版报告（Markdown）：{report_md}")
    if isinstance(report_json, str) and report_json.strip():
        lines.append(f"- 技术版报告（JSON）：{report_json}")
    if isinstance(user_summary_md, str) and user_summary_md.strip():
        lines.append(f"- 查看用户摘要：结果面板上方“用户版中文摘要”区域")
        lines.append(f"- 打开摘要文件：{user_summary_md}")
    if result.output_dir.exists():
        lines.append(f"- 打开输出目录：{result.output_dir}")

    technical_summary = user_summary.get("technical_summary", {}) if isinstance(user_summary, dict) else {}
    if isinstance(technical_summary, dict) and technical_summary:
        lines.extend(["", "技术字段（次级展示）"])
        for key in (
            "auto_fix_rule_count",
            "detected_not_auto_modified_count",
            "manual_review_required_count",
            "reference_finding_count",
            "reference_blocking_count",
            "block_low_confidence_count",
        ):
            lines.append(f"- {key}: {technical_summary.get(key, summary.get(key, 0))}")
    elif isinstance(summary, dict) and summary:
        lines.extend(["", "技术字段（次级展示）"])
        for key in (
            "auto_fix_rule_count",
            "detected_not_auto_modified_count",
            "manual_review_required_count",
            "reference_finding_count",
            "reference_blocking_count",
            "block_low_confidence_count",
        ):
            lines.append(f"- {key}: {summary.get(key, 0)}")

    lines.extend(["", "本次产物文件"])
    if result.generated_files:
        lines.extend(f"- {path}" for path in result.generated_files)
    else:
        lines.append("- (none)")

    if result.error_text:
        lines.extend(["", "错误信息", result.error_text.strip()])
    return "\n".join(lines) + "\n"


def execute_gui_batch_task(
    *,
    input_dir: Path,
    output_dir: Path,
    recursive: bool = True,
    batch_runner: BatchRunner = run_batch_fix,
) -> GuiBatchExecutionResult:
    if not input_dir.exists() or not input_dir.is_dir():
        raise ValueError(f"输入目录不存在或不可用: {input_dir}")

    try:
        _ensure_gui_output_directory_writable(output_dir)
    except PermissionError as exc:
        return GuiBatchExecutionResult(
            input_dir=input_dir,
            output_dir=output_dir,
            recursive=recursive,
            success=False,
            exit_code=1,
            total_files=0,
            succeeded=0,
            failed=0,
            items=(),
            summary_payload={},
            error_text=_localize_gui_error(exc),
        )
    summary_json = output_dir / "batch_summary.json"

    try:
        code = batch_runner(input_dir, output_dir, recursive=recursive)
    except Exception as exc:
        return GuiBatchExecutionResult(
            input_dir=input_dir,
            output_dir=output_dir,
            recursive=recursive,
            success=False,
            exit_code=1,
            total_files=0,
            succeeded=0,
            failed=0,
            items=(),
            summary_payload={},
            error_text=_localize_gui_error(exc),
        )

    payload: dict[str, Any] = {}
    parse_error: str | None = None
    if summary_json.exists():
        try:
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            parse_error = f"批处理摘要解析失败: {exc}"
    else:
        parse_error = f"缺少批处理摘要文件: {summary_json}"

    items_raw = payload.get("items", []) if isinstance(payload, dict) else []
    items = tuple(item for item in items_raw if isinstance(item, dict))
    total_files = int(payload.get("total_files", len(items))) if isinstance(payload, dict) else len(items)
    succeeded = int(payload.get("succeeded", 0)) if isinstance(payload, dict) else 0
    failed = int(payload.get("failed", 0)) if isinstance(payload, dict) else 0
    warning = payload.get("warning") if isinstance(payload, dict) else None
    success = (code == 0) and parse_error is None
    error_text = parse_error
    expected_empty_warning = bool(
        code == 2 and isinstance(warning, str) and warning.strip() and total_files == 0 and failed == 0
    )
    if code != 0 and not expected_empty_warning:
        error_text = (error_text + "\n" if error_text else "") + f"Runner exit code: {code}"

    return GuiBatchExecutionResult(
        input_dir=input_dir,
        output_dir=output_dir,
        recursive=recursive,
        success=success,
        exit_code=code,
        total_files=total_files,
        succeeded=succeeded,
        failed=failed,
        items=items,
        summary_payload=payload,
        error_text=error_text,
    )


def format_gui_batch_result(result: GuiBatchExecutionResult) -> str:
    warning = result.summary_payload.get("warning") if isinstance(result.summary_payload, dict) else None
    summary_json = result.output_dir / "batch_summary.json"
    summary_md = result.output_dir / "batch_summary.md"
    lines = [
        "GUI 批量修复结果面板",
        f"- 本次处理类型：批量修复",
        f"- 输入目录：{result.input_dir}",
        f"- 输出目录：{result.output_dir}",
        f"- 扫描方式：{'递归扫描子目录' if result.recursive else '仅扫描当前目录'}",
        f"- 执行状态：{'成功' if result.success else '未完全成功'}（exit_code={result.exit_code}）",
        "",
        "批量结果摘要",
        f"- 处理文件总数：{result.total_files}",
        f"- 成功数量：{result.succeeded}",
        f"- 失败数量：{result.failed}",
        f"- 批处理汇总 JSON：{summary_json}",
        f"- 批处理汇总 Markdown：{summary_md}",
        "",
        "逐文件结果",
    ]

    if result.items:
        for item in result.items:
            input_file = item.get("input_file")
            output_docx = item.get("output_docx")
            report_json = item.get("report_json")
            report_md = item.get("report_md")
            lines.append(
                "- "
                + f"exit_code={item.get('exit_code')} 输入={input_file} 修复后文件={output_docx}"
            )
            if report_md:
                lines.append(f"  报告 Markdown：{report_md}")
            if report_json:
                lines.append(f"  报告 JSON：{report_json}")
            if item.get("error"):
                lines.append(f"  错误：{item.get('error')}")
    else:
        lines.append("- 当前没有可展示的单文件结果。")

    if warning:
        lines.extend(["", f"提示：{warning}"])

    if result.error_text:
        lines.extend(["", "错误信息", result.error_text.strip()])
    return "\n".join(lines) + "\n"


def open_directory(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"目录不存在: {path}")
    if os.name == "nt":  # pragma: no cover - windows only
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    if sys_platform_is_macos():
        subprocess.run(["open", str(path)], check=True)
        return
    subprocess.run(["xdg-open", str(path)], check=True)


def open_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    if os.name == "nt":  # pragma: no cover - windows only
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    if sys_platform_is_macos():
        subprocess.run(["open", str(path)], check=True)
        return
    subprocess.run(["xdg-open", str(path)], check=True)


def export_user_summary_file(source: Path, destination: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"用户版摘要文件不存在: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def sys_platform_is_macos() -> bool:
    return os.sys.platform == "darwin"


def _set_widget_enabled(widget: object | None, enabled: bool) -> None:
    if widget is None:
        return
    if hasattr(widget, "setEnabled"):
        widget.setEnabled(enabled)  # type: ignore[call-arg]
        return
    if hasattr(widget, "config"):
        widget.config(state="normal" if enabled else "disabled")  # type: ignore[call-arg]


class _GuiActionsMixin:
    _last_output_dir: Path | None
    _last_report_file: Path | None
    _last_user_summary_file: Path | None
    _artifact_paths: tuple[Path, ...]
    status_var: _StatusVarAdapter

    def _status_parent(self) -> object | None:
        return self if isinstance(self, object) else None

    def _set_status_text(self, text: str) -> None:
        self.status_var.set(text)

    def _set_user_summary_action_state(self) -> None:
        summary_available = self._last_user_summary_file is not None and self._last_user_summary_file.exists()
        _set_widget_enabled(getattr(self, "open_user_summary_button", None), summary_available)
        _set_widget_enabled(getattr(self, "export_user_summary_button", None), summary_available)

    def _open_user_summary(self) -> None:
        if self._last_user_summary_file is None:
            self._set_status_text("当前没有可打开的用户版摘要，请先执行 check 或 fix。")
            return
        try:
            open_file(self._last_user_summary_file)
            self._set_status_text(f"已打开用户版摘要：{self._last_user_summary_file}")
        except Exception as exc:  # pragma: no cover - platform dependent
            if messagebox is not None:
                messagebox.showerror("打开用户版摘要失败", str(exc), parent=self._status_parent())
            else:
                self._set_status_text(str(exc))

    def _export_user_summary(self) -> None:
        if self._last_user_summary_file is None:
            self._set_status_text("当前没有可导出的用户版摘要，请先执行 check 或 fix。")
            return
        if filedialog is None:
            self._set_status_text("当前环境不支持文件对话框，无法导出用户版摘要。")
            return
        target_path_raw = filedialog.asksaveasfilename(
            parent=self._status_parent(),
            title="导出用户版摘要",
            defaultextension=".md",
            initialfile=self._last_user_summary_file.name,
            filetypes=[("Markdown", "*.md"), ("All Files", "*.*")],
        )
        if not target_path_raw:
            self._set_status_text("已取消导出用户版摘要。")
            return
        target_path = Path(target_path_raw)
        try:
            exported = export_user_summary_file(self._last_user_summary_file, target_path)
            self._set_status_text(f"用户版摘要已导出到：{exported}")
        except Exception as exc:  # pragma: no cover - platform dependent
            if messagebox is not None:
                messagebox.showerror("导出用户版摘要失败", str(exc), parent=self._status_parent())
            else:
                self._set_status_text(str(exc))


if _PYSIDE6_IMPORT_ERROR is None:

    class _GuiWorker(QObject):
        finished = Signal(object)

        def __init__(self, *, mode: str, input_path: Path, output_dir: Path, recursive: bool) -> None:
            super().__init__()
            self.mode = mode
            self.input_path = input_path
            self.output_dir = output_dir
            self.recursive = recursive

        def run(self) -> None:
            if self.mode == "batch-fix":
                result = execute_gui_batch_task(
                    input_dir=self.input_path,
                    output_dir=self.output_dir,
                    recursive=self.recursive,
                )
            else:
                result = execute_gui_task(
                    input_file=self.input_path,
                    output_dir=self.output_dir,
                    mode=self.mode,
                )
            self.finished.emit(result)


    class ThesisFormatFixerGUI(QMainWindow, _GuiActionsMixin):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Thesis Format Fixer")
            self.resize(1120, 760)

            self.status_var = _StatusVarAdapter(self._on_status_text_changed)
            self._last_output_dir: Path | None = None
            self._last_report_file: Path | None = None
            self._last_user_summary_file: Path | None = None
            self._artifact_paths: tuple[Path, ...] = ()
            self._worker_thread: QThread | None = None
            self._worker: _GuiWorker | None = None

            self._build_window()
            self.output_path_edit.setText(str(default_gui_output_dir()))
            self._refresh_mode_ui()
            self._refresh_execute_state()
            self._set_status_text("请选择输入文件；输出目录已默认指向用户主目录下的 ThesisFormatFixerOutput。")

        def _status_parent(self) -> object | None:
            return self

        def _build_window(self) -> None:
            central = QWidget(self)
            main_layout = QVBoxLayout(central)
            main_layout.setContentsMargins(14, 14, 14, 14)
            main_layout.setSpacing(12)

            main_layout.addWidget(self._build_input_group())
            main_layout.addWidget(self._build_actions_group())
            main_layout.addWidget(self._build_results_group(), stretch=1)

            self.setCentralWidget(central)
            self._build_status_bar()
            self._build_menu()

        def _build_input_group(self) -> QGroupBox:
            group = QGroupBox("输入与模式", self)
            layout = QFormLayout(group)

            self.input_label = QLabel("论文文件", group)
            self.input_path_edit = QLineEdit(group)
            self.input_path_edit.setPlaceholderText("选择待检查或修复的 .docx 文件")
            self.input_path_edit.textChanged.connect(self._refresh_execute_state)
            input_row = QHBoxLayout()
            input_row.addWidget(self.input_path_edit)
            self.input_browse_button = QPushButton("选择输入", group)
            self.input_browse_button.clicked.connect(self._pick_input)
            input_row.addWidget(self.input_browse_button)
            layout.addRow(self.input_label, self._wrap_row(input_row))

            self.output_path_edit = QLineEdit(group)
            self.output_path_edit.setPlaceholderText("选择输出目录，用于保存报告和修复结果")
            self.output_path_edit.textChanged.connect(self._refresh_execute_state)
            output_row = QHBoxLayout()
            output_row.addWidget(self.output_path_edit)
            self.output_browse_button = QPushButton("选择输出目录", group)
            self.output_browse_button.clicked.connect(self._pick_output_dir)
            output_row.addWidget(self.output_browse_button)
            layout.addRow("输出目录", self._wrap_row(output_row))

            mode_row = QHBoxLayout()
            self.mode_combo = QComboBox(group)
            self.mode_combo.addItem("仅检查", "check")
            self.mode_combo.addItem("检查并修复", "fix")
            self.mode_combo.addItem("批量修复（兼容入口）", "batch-fix")
            self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
            mode_row.addWidget(self.mode_combo)
            self.recursive_checkbox = QCheckBox("递归扫描子目录", group)
            self.recursive_checkbox.setChecked(True)
            self.recursive_checkbox.toggled.connect(self._refresh_execute_state)
            mode_row.addWidget(self.recursive_checkbox)
            mode_row.addStretch(1)
            layout.addRow("处理模式", self._wrap_row(mode_row))
            return group

        def _build_actions_group(self) -> QGroupBox:
            group = QGroupBox("操作", self)
            layout = QHBoxLayout(group)

            self.run_button = QPushButton("开始执行", group)
            self.run_button.clicked.connect(self._execute)
            layout.addWidget(self.run_button)

            self.reset_button = QPushButton("重置", group)
            self.reset_button.clicked.connect(self._reset_form)
            layout.addWidget(self.reset_button)

            self.open_output_button = QPushButton("打开输出目录", group)
            self.open_output_button.clicked.connect(self._open_output_dir)
            layout.addWidget(self.open_output_button)

            self.open_report_button = QPushButton("打开关键报告", group)
            self.open_report_button.clicked.connect(self._open_detailed_report)
            layout.addWidget(self.open_report_button)

            self.open_user_summary_button = QPushButton("打开摘要文件", group)
            self.open_user_summary_button.clicked.connect(self._open_user_summary)
            layout.addWidget(self.open_user_summary_button)

            self.export_user_summary_button = QPushButton("导出用户摘要", group)
            self.export_user_summary_button.clicked.connect(self._export_user_summary)
            layout.addWidget(self.export_user_summary_button)

            layout.addStretch(1)
            _set_widget_enabled(self.open_output_button, False)
            _set_widget_enabled(self.open_report_button, False)
            self._set_user_summary_action_state()
            return group

        def _build_results_group(self) -> QGroupBox:
            group = QGroupBox("结果", self)
            layout = QVBoxLayout(group)

            splitter = QSplitter(Qt.Vertical, group)

            summary_container = QWidget(splitter)
            summary_layout = QVBoxLayout(summary_container)
            summary_layout.setContentsMargins(0, 0, 0, 0)
            summary_layout.addWidget(QLabel("用户版中文摘要", summary_container))
            self.summary_text = QTextEdit(summary_container)
            self.summary_text.setReadOnly(True)
            self.summary_text.setPlaceholderText("执行成功后，这里会优先展示用户可直接阅读的中文摘要。")
            self.summary_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
            summary_layout.addWidget(self.summary_text)

            detail_container = QWidget(splitter)
            detail_layout = QVBoxLayout(detail_container)
            detail_layout.setContentsMargins(0, 0, 0, 0)
            detail_layout.addWidget(QLabel("详细结果 / 日志", detail_container))
            self.detail_text = QTextEdit(detail_container)
            self.detail_text.setReadOnly(True)
            self.detail_text.setPlaceholderText("这里显示详细结果、批处理摘要以及失败时的技术信息。")
            self.detail_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
            detail_layout.addWidget(self.detail_text, stretch=1)

            detail_layout.addWidget(QLabel("报告与输出文件快捷入口", detail_container))
            self.artifact_list = QListWidget(detail_container)
            self.artifact_list.itemDoubleClicked.connect(self._open_selected_artifact)
            detail_layout.addWidget(self.artifact_list, stretch=1)

            splitter.addWidget(summary_container)
            splitter.addWidget(detail_container)
            splitter.setStretchFactor(0, 3)
            splitter.setStretchFactor(1, 2)
            layout.addWidget(splitter)
            return group

        def _build_status_bar(self) -> None:
            bar = QStatusBar(self)
            self.setStatusBar(bar)
            self.status_label = QLabel("就绪", self)
            self.output_label = QLabel("最近输出：-", self)
            self.output_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            bar.addWidget(self.status_label, 1)
            bar.addPermanentWidget(self.output_label, 1)

        def _build_menu(self) -> None:
            file_menu = self.menuBar().addMenu("文件")
            run_action = QAction("开始执行", self)
            run_action.triggered.connect(self._execute)
            file_menu.addAction(run_action)

            open_output_action = QAction("打开输出目录", self)
            open_output_action.triggered.connect(self._open_output_dir)
            file_menu.addAction(open_output_action)

            exit_action = QAction("退出", self)
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)

        def _wrap_row(self, layout: QHBoxLayout) -> QWidget:
            container = QWidget(self)
            container.setLayout(layout)
            return container

        def _mode(self) -> str:
            return str(self.mode_combo.currentData())

        def _on_mode_changed(self) -> None:
            self._refresh_mode_ui()
            self._refresh_execute_state()

        def _refresh_mode_ui(self) -> None:
            batch_mode = self._mode() == "batch-fix"
            self.input_label.setText("输入目录" if batch_mode else "论文文件")
            self.input_path_edit.setPlaceholderText(
                "选择包含 .docx 的输入目录" if batch_mode else "选择待检查或修复的 .docx 文件"
            )
            self.recursive_checkbox.setVisible(batch_mode)
            self.input_browse_button.setText("选择目录" if batch_mode else "选择输入")

        def _refresh_execute_state(self) -> None:
            input_value = self.input_path_edit.text().strip()
            output_value = self.output_path_edit.text().strip()
            enabled = bool(input_value and output_value and self._worker_thread is None)
            _set_widget_enabled(self.run_button, enabled)

        def _pick_input(self) -> None:
            if filedialog is None:
                return
            if self._mode() == "batch-fix":
                path = filedialog.askdirectory(parent=self, title="选择输入目录")
            else:
                path = filedialog.askopenfilename(parent=self, title="选择论文文件")
            if path:
                self.input_path_edit.setText(path)
                if not self.output_path_edit.text().strip():
                    self.output_path_edit.setText(str(default_gui_output_dir()))

        def _pick_output_dir(self) -> None:
            if filedialog is None:
                return
            path = filedialog.askdirectory(parent=self, title="选择输出目录")
            if path:
                self.output_path_edit.setText(path)

        def _ensure_output_dir_writable(self, output_dir: Path) -> tuple[bool, str | None]:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                return False, f"输出目录不可创建: {output_dir}"

            probe: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=output_dir,
                    prefix=".gui_write_probe_",
                    suffix=".tmp",
                    delete=False,
                ) as handle:
                    probe = Path(handle.name)
            except OSError:
                return False, f"输出目录不可写: {output_dir}"
            finally:
                if probe is not None and probe.exists():
                    probe.unlink(missing_ok=True)
            return True, None

        def _validate_before_run(self) -> tuple[Path, Path, str, bool] | None:
            input_value = self.input_path_edit.text().strip()
            output_value = self.output_path_edit.text().strip()
            mode = self._mode()

            if not input_value:
                self._set_status_text("请先选择输入文件或输入目录。")
                if messagebox is not None:
                    messagebox.showwarning("缺少输入", "请先选择输入文件或输入目录。", parent=self)
                return None
            if not output_value:
                self._set_status_text("请先选择输出目录。")
                if messagebox is not None:
                    messagebox.showwarning("缺少输出目录", "请先选择输出目录。", parent=self)
                return None

            input_path = Path(input_value)
            output_dir = Path(output_value)
            output_ok, output_error = self._ensure_output_dir_writable(output_dir)
            if not output_ok:
                self._set_status_text(output_error or "输出目录不可写。")
                if messagebox is not None and output_error:
                    messagebox.showerror("输出目录不可用", output_error, parent=self)
                return None

            if mode == "batch-fix":
                if not input_path.exists() or not input_path.is_dir():
                    text = "批量修复模式下，输入路径必须是已存在目录。"
                    self._set_status_text(text)
                    if messagebox is not None:
                        messagebox.showwarning("输入目录无效", text, parent=self)
                    return None
                return input_path, output_dir, mode, self.recursive_checkbox.isChecked()

            if not input_path.exists():
                text = "输入文件不存在。"
                self._set_status_text(text)
                if messagebox is not None:
                    messagebox.showwarning("输入文件不存在", text, parent=self)
                return None
            if input_path.is_dir() or input_path.suffix.lower() != ".docx":
                text = "请输入有效的 .docx 论文文件。"
                self._set_status_text(text)
                if messagebox is not None:
                    messagebox.showwarning("输入文件无效", text, parent=self)
                return None
            return input_path, output_dir, mode, False

        def _set_busy(self, busy: bool) -> None:
            controls = (
                self.run_button,
                self.reset_button,
                self.input_browse_button,
                self.output_browse_button,
                self.mode_combo,
                self.recursive_checkbox,
                self.input_path_edit,
                self.output_path_edit,
            )
            for widget in controls:
                _set_widget_enabled(widget, not busy)
            if not busy:
                self._refresh_execute_state()

        def _execute(self) -> None:
            validated = self._validate_before_run()
            if validated is None:
                return

            input_path, output_dir, mode, recursive = validated
            self._set_busy(True)
            self.summary_text.clear()
            self.detail_text.clear()
            self.artifact_list.clear()
            self._set_status_text("正在执行，请稍候……")
            self.output_label.setText(f"最近输出：{output_dir}")

            self._worker_thread = QThread(self)
            self._worker = _GuiWorker(mode=mode, input_path=input_path, output_dir=output_dir, recursive=recursive)
            self._worker.moveToThread(self._worker_thread)
            self._worker_thread.started.connect(self._worker.run)
            self._worker.finished.connect(self._handle_worker_result)
            self._worker.finished.connect(self._worker_thread.quit)
            self._worker.finished.connect(self._worker.deleteLater)
            self._worker_thread.finished.connect(self._worker_thread.deleteLater)
            self._worker_thread.finished.connect(self._clear_worker_state)
            self._worker_thread.start()

        def _clear_worker_state(self) -> None:
            self._worker = None
            self._worker_thread = None
            self._set_busy(False)

        def _handle_worker_result(self, result: object) -> None:
            if isinstance(result, GuiBatchExecutionResult):
                self._apply_batch_result(result)
                return
            if isinstance(result, GuiExecutionResult):
                self._apply_single_result(result)

        def _apply_single_result(self, result: GuiExecutionResult) -> None:
            self.detail_text.setPlainText(format_gui_result(result))
            self._last_output_dir = result.output_dir
            self._last_report_file = None
            self._last_user_summary_file = None

            artifacts = result.payload.get("artifacts", {}) if isinstance(result.payload, dict) else {}
            self._artifact_paths = self._collect_artifacts(artifacts, result.generated_files)
            self._populate_artifacts()

            if isinstance(artifacts, dict):
                self._last_report_file = self._pick_existing_path(
                    artifacts.get("technical_report_md"),
                    artifacts.get("report_md"),
                    artifacts.get("technical_report_json"),
                    artifacts.get("report_json"),
                )
                self._last_user_summary_file = self._pick_existing_path(artifacts.get("user_summary_md"))

            self._set_user_summary_action_state()
            _set_widget_enabled(self.open_output_button, result.output_dir.exists())
            _set_widget_enabled(self.open_report_button, self._last_report_file is not None)

            summary_text = self._build_primary_summary_for_single(result)
            self.summary_text.setPlainText(summary_text)
            if result.success:
                self._set_status_text("执行完成。用户摘要已更新。")
            else:
                self._set_status_text("执行失败。请先查看中文提示，再根据详细结果排查。")
                if result.error_text and messagebox is not None:
                    messagebox.showerror("执行失败", f"本次处理未完成。\n\n{result.error_text}", parent=self)

        def _apply_batch_result(self, result: GuiBatchExecutionResult) -> None:
            self.detail_text.setPlainText(format_gui_batch_result(result))
            self._last_output_dir = result.output_dir
            self._last_report_file = self._pick_existing_path(
                result.output_dir / "batch_summary.md",
                result.output_dir / "batch_summary.json",
            )
            self._last_user_summary_file = None
            self._artifact_paths = tuple(
                path
                for path in (
                    result.output_dir / "batch_summary.md",
                    result.output_dir / "batch_summary.json",
                )
                if path.exists()
            )
            self._populate_artifacts()
            self._set_user_summary_action_state()
            _set_widget_enabled(self.open_output_button, result.output_dir.exists())
            _set_widget_enabled(self.open_report_button, self._last_report_file is not None)

            lines = [
                "批量修复已完成",
                "",
                f"总文件数：{result.total_files}",
                f"成功：{result.succeeded}",
                f"失败：{result.failed}",
                f"输出目录：{result.output_dir}",
            ]
            warning = result.summary_payload.get("warning") if isinstance(result.summary_payload, dict) else None
            if warning:
                lines.extend(["", f"提醒：{warning}"])
            if result.failed > 0:
                lines.extend(["", "建议：先打开批处理摘要，优先处理失败项。"])
            elif warning:
                lines.extend(["", "建议：请确认输入目录中是否放入了待处理的 .docx 文件。"])
            else:
                lines.extend(["", "建议：打开输出目录抽查关键文件和批处理摘要。"])
            self.summary_text.setPlainText("\n".join(lines))

            if result.success:
                self._set_status_text("批量修复完成。")
            elif warning and result.total_files == 0 and result.failed == 0:
                self._set_status_text("批量处理已完成，但输入目录中未找到 .docx 文件。")
            else:
                self._set_status_text("批量修复结束，但存在失败或摘要异常。")
                if result.error_text and messagebox is not None:
                    messagebox.showerror("批量修复未完全成功", result.error_text, parent=self)

        def _build_primary_summary_for_single(self, result: GuiExecutionResult) -> str:
            payload = result.payload if isinstance(result.payload, dict) else {}
            artifacts = payload.get("artifacts", {}) if isinstance(payload, dict) else {}
            artifact_paths = {
                key: value
                for key, value in (artifacts.items() if isinstance(artifacts, dict) else [])
                if isinstance(value, str) and value.strip()
            }
            user_summary = payload.get("user_summary")
            if isinstance(user_summary, dict) and user_summary:
                summary_obj = build_user_result_summary(
                    payload,
                    artifact_paths=artifact_paths,
                    processing_type=result.mode,
                )
                return render_user_summary_markdown(summary_obj, payload=payload)

            summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
            processing_label = "修复" if result.mode == "fix" else "检查"
            lines = [
                f"{processing_label}结果摘要",
                "",
                f"状态：{'成功' if result.success else '失败'}",
                f"自动修复数量：{summary.get('auto_fix_rule_count', 0)}",
                f"检测到但未自动修改数量：{summary.get('detected_not_auto_modified_count', 0)}",
                f"需要人工复核数量：{summary.get('manual_review_required_count', 0)}",
                f"参考文献相关提醒数量：{summary.get('reference_finding_count', 0)}",
            ]
            if result.mode == "fix":
                lines.extend(
                    [
                        "",
                        "本次 fix 重点",
                        f"- 已自动修复：{summary.get('auto_fix_rule_count', 0)} 项",
                        f"- 检测到异常但未自动修改：{summary.get('detected_not_auto_modified_count', 0)} 项",
                        f"- 需要人工复核：{summary.get('manual_review_required_count', 0)} 项",
                    ]
                )
            if result.error_text:
                lines.extend(["", f"失败原因：{result.error_text}"])
            return "\n".join(lines)

        def _collect_artifacts(self, artifacts: dict[str, Any], generated_files: tuple[Path, ...]) -> tuple[Path, ...]:
            collected: list[Path] = []
            if isinstance(artifacts, dict):
                for key in (
                    "fixed_docx",
                    "technical_report_md",
                    "report_md",
                    "technical_report_json",
                    "report_json",
                    "user_summary_md",
                ):
                    value = artifacts.get(key)
                    if isinstance(value, str) and value.strip():
                        path = Path(value)
                        if path.exists() and path not in collected:
                            collected.append(path)
            for path in generated_files:
                if path.exists() and path not in collected:
                    collected.append(path)
            return tuple(collected)

        def _populate_artifacts(self) -> None:
            self.artifact_list.clear()
            if not self._artifact_paths:
                return
            for path in self._artifact_paths:
                item = QListWidgetItem(path.name)
                item.setData(Qt.UserRole, str(path))
                self.artifact_list.addItem(item)

        def _pick_existing_path(self, *candidates: object) -> Path | None:
            for item in candidates:
                if isinstance(item, Path):
                    if item.exists():
                        return item
                    continue
                if isinstance(item, str) and item.strip():
                    path = Path(item)
                    if path.exists():
                        return path
            return None

        def _open_output_dir(self) -> None:
            if self._last_output_dir is None:
                self._set_status_text("当前还没有可打开的输出目录。")
                return
            try:
                open_directory(self._last_output_dir)
                self._set_status_text(f"已打开输出目录：{self._last_output_dir}")
            except Exception as exc:  # pragma: no cover - platform dependent
                if messagebox is not None:
                    messagebox.showerror("打开输出目录失败", str(exc), parent=self)
                else:
                    self._set_status_text(str(exc))

        def _open_detailed_report(self) -> None:
            if self._last_report_file is None:
                self._set_status_text("当前还没有可打开的关键报告。")
                return
            try:
                open_file(self._last_report_file)
                self._set_status_text(f"已打开关键报告：{self._last_report_file}")
            except Exception as exc:  # pragma: no cover - platform dependent
                if messagebox is not None:
                    messagebox.showerror("打开关键报告失败", str(exc), parent=self)
                else:
                    self._set_status_text(str(exc))

        def _open_selected_artifact(self, item: QListWidgetItem) -> None:
            raw_path = item.data(Qt.UserRole)
            if not isinstance(raw_path, str) or not raw_path.strip():
                return
            path = Path(raw_path)
            try:
                open_file(path)
                self._set_status_text(f"已打开文件：{path}")
            except Exception as exc:  # pragma: no cover - platform dependent
                if messagebox is not None:
                    messagebox.showerror("打开文件失败", str(exc), parent=self)
                else:
                    self._set_status_text(str(exc))

        def _reset_form(self) -> None:
            if self._worker_thread is not None:
                return
            self.input_path_edit.clear()
            self.output_path_edit.setText(str(default_gui_output_dir()))
            self.mode_combo.setCurrentIndex(0)
            self.recursive_checkbox.setChecked(True)
            self.summary_text.clear()
            self.detail_text.clear()
            self.artifact_list.clear()
            self._last_output_dir = None
            self._last_report_file = None
            self._last_user_summary_file = None
            self._artifact_paths = ()
            _set_widget_enabled(self.open_output_button, False)
            _set_widget_enabled(self.open_report_button, False)
            self._set_user_summary_action_state()
            self.output_label.setText("最近输出：-")
            self._set_status_text("已重置。请选择新的输入文件；输出目录已恢复为默认路径。")
            self._refresh_execute_state()

        def _on_status_text_changed(self, text: str) -> None:
            self.status_label.setText(text or "就绪")


else:

    class ThesisFormatFixerGUI(_GuiActionsMixin):
        def __init__(self) -> None:
            raise RuntimeError(f"PySide6 unavailable: {_PYSIDE6_IMPORT_ERROR}")


def main() -> int:
    if _PYSIDE6_IMPORT_ERROR is not None:
        raise RuntimeError(f"PySide6 unavailable: {_PYSIDE6_IMPORT_ERROR}")
    assert QApplication is not None
    app = QApplication.instance() or QApplication([])
    window = ThesisFormatFixerGUI()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
