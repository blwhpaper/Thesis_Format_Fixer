"""PySide6 desktop host for thesis-format-fixer."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from thesis_format_fixer.app.runner import run_batch_fix, run_check_with_details, run_fix_with_details
from thesis_format_fixer.reporters.report_builder import build_user_result_summary, render_user_summary_markdown
from thesis_format_fixer.runtime_paths import APP_DISPLAY_NAME, default_output_dir, resolve_app_icon_path

try:
    from PySide6.QtCore import QObject, Qt, QThread, Signal
    from PySide6.QtGui import QAction, QIcon, QTextOption
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QFormLayout,
        QGridLayout,
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
    QGridLayout = None
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
    QIcon = None
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
BatchProgressCallback = Callable[["BatchTaskRecord"], None]


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


@dataclass(frozen=True, slots=True)
class BatchTaskRecord:
    file_name: str
    file_path: Path
    mode: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    summary: str = ""
    artifact_paths: dict[str, str] = field(default_factory=dict)
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class GuiBatchQueueExecutionResult:
    mode: str
    output_dir: Path
    total_files: int
    succeeded: int
    failed: int
    tasks: tuple[BatchTaskRecord, ...] = ()
    ignored_files: tuple[str, ...] = ()
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

    def askopenfilenames(self, **kwargs: object) -> list[str]:
        if QFileDialog is None:
            return []
        parent = kwargs.get("parent")
        title = str(kwargs.get("title", "选择文件"))
        filter_spec = "Word Document (*.docx);;All Files (*)"
        selected, _ = QFileDialog.getOpenFileNames(parent, title, "", filter_spec)
        return list(selected)

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


def apply_gui_application_metadata(app: object) -> None:
    if hasattr(app, "setApplicationDisplayName"):
        app.setApplicationDisplayName(APP_DISPLAY_NAME)  # type: ignore[call-arg]
    if hasattr(app, "setApplicationName"):
        app.setApplicationName(APP_DISPLAY_NAME)  # type: ignore[call-arg]
    if hasattr(app, "setOrganizationName"):
        app.setOrganizationName("Thesis Format Fixer")  # type: ignore[call-arg]

    icon_path = resolve_app_icon_path()
    if icon_path is None or QIcon is None or not hasattr(app, "setWindowIcon"):
        return

    icon = QIcon(str(icon_path))
    if icon.isNull():
        return
    app.setWindowIcon(icon)  # type: ignore[call-arg]


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


def _batch_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def filter_batch_import_paths(paths: list[Path] | tuple[Path, ...]) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    docx_paths: list[Path] = []
    ignored: list[str] = []
    seen: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path)
        normalized = str(path)
        if path.suffix.lower() != ".docx":
            ignored.append(path.name)
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        docx_paths.append(path)
    return tuple(docx_paths), tuple(ignored)


def collect_docx_files_from_directory(input_dir: Path, *, recursive: bool = True) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    if recursive:
        candidates = sorted(path for path in input_dir.rglob("*") if path.is_file())
    else:
        candidates = sorted(path for path in input_dir.iterdir() if path.is_file())
    return filter_batch_import_paths(candidates)


def _build_batch_task_output_dir(base_output_dir: Path, input_file: Path, *, index: int) -> Path:
    safe_stem = input_file.stem.replace(" ", "_") or "document"
    return base_output_dir / f"{index:03d}_{safe_stem}"


def _extract_task_summary(result: GuiExecutionResult) -> str:
    payload = result.payload if isinstance(result.payload, dict) else {}
    user_summary = payload.get("user_summary", {}) if isinstance(payload, dict) else {}
    if isinstance(user_summary, dict):
        overall_status = str(user_summary.get("overall_status", "")).strip()
        if overall_status:
            return overall_status
    if result.success:
        return "处理完成。"
    return result.error_text or "处理失败。"


def _extract_task_artifact_paths(result: GuiExecutionResult) -> dict[str, str]:
    payload = result.payload if isinstance(result.payload, dict) else {}
    artifacts = payload.get("artifacts", {}) if isinstance(payload, dict) else {}
    artifact_paths: dict[str, str] = {}
    if isinstance(artifacts, dict):
        for key, value in artifacts.items():
            if isinstance(value, str) and value.strip():
                artifact_paths[key] = value
    if "output_dir" not in artifact_paths:
        artifact_paths["output_dir"] = str(result.output_dir)
    return artifact_paths


def execute_gui_batch_queue(
    *,
    input_files: tuple[Path, ...],
    output_dir: Path,
    mode: str,
    progress_callback: BatchProgressCallback | None = None,
    check_runner: RunnerWithDetails = run_check_with_details,
    fix_runner: RunnerWithDetails = run_fix_with_details,
) -> GuiBatchQueueExecutionResult:
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"check", "fix"}:
        raise ValueError(f"Unsupported batch mode: {mode}")

    filtered_files, ignored_files = filter_batch_import_paths(input_files)
    try:
        _ensure_gui_output_directory_writable(output_dir)
    except PermissionError as exc:
        return GuiBatchQueueExecutionResult(
            mode=normalized_mode,
            output_dir=output_dir,
            total_files=0,
            succeeded=0,
            failed=0,
            tasks=(),
            ignored_files=ignored_files,
            error_text=_localize_gui_error(exc),
        )

    tasks: list[BatchTaskRecord] = []
    for path in filtered_files:
        tasks.append(
            BatchTaskRecord(
                file_name=path.name,
                file_path=path,
                mode=normalized_mode,
                status="pending",
            )
        )

    succeeded = 0
    failed = 0

    for index, task in enumerate(tasks, start=1):
        running_task = BatchTaskRecord(
            file_name=task.file_name,
            file_path=task.file_path,
            mode=task.mode,
            status="running",
            started_at=_batch_timestamp(),
        )
        tasks[index - 1] = running_task
        if progress_callback is not None:
            progress_callback(running_task)

        task_output_dir = _build_batch_task_output_dir(output_dir, task.file_path, index=index)
        result = execute_gui_task(
            input_file=task.file_path,
            output_dir=task_output_dir,
            mode=normalized_mode,
            check_runner=check_runner,
            fix_runner=fix_runner,
        )

        finished_task = BatchTaskRecord(
            file_name=task.file_name,
            file_path=task.file_path,
            mode=task.mode,
            status="success" if result.success else "failed",
            started_at=running_task.started_at,
            finished_at=_batch_timestamp(),
            summary=_extract_task_summary(result),
            artifact_paths=_extract_task_artifact_paths(result),
            error_message=result.error_text,
        )
        tasks[index - 1] = finished_task
        if result.success:
            succeeded += 1
        else:
            failed += 1
        if progress_callback is not None:
            progress_callback(finished_task)

    return GuiBatchQueueExecutionResult(
        mode=normalized_mode,
        output_dir=output_dir,
        total_files=len(filtered_files),
        succeeded=succeeded,
        failed=failed,
        tasks=tuple(tasks),
        ignored_files=ignored_files,
        error_text=None,
    )


def format_batch_task_detail(task: BatchTaskRecord) -> str:
    processing_label = "修复" if task.mode == "fix" else "检查"
    lines = [
        "批量任务详情",
        f"- 文件名：{task.file_name}",
        f"- 处理方式：{processing_label}",
        f"- 状态：{task.status}",
        f"- 开始时间：{task.started_at or '-'}",
        f"- 完成时间：{task.finished_at or '-'}",
    ]
    if task.summary:
        lines.extend(["", "中文结果摘要", task.summary])
    if task.error_message:
        lines.extend(["", "错误信息", task.error_message])
    if task.artifact_paths:
        lines.extend(["", "产物入口"])
        for key, value in task.artifact_paths.items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def format_gui_batch_queue_result(result: GuiBatchQueueExecutionResult) -> str:
    processing_label = "批量修复" if result.mode == "fix" else "批量检查"
    lines = [
        "GUI 批量任务结果面板",
        f"- 本次处理类型：{processing_label}",
        f"- 输出目录：{result.output_dir}",
        f"- 总文件数：{result.total_files}",
        f"- 成功数量：{result.succeeded}",
        f"- 失败数量：{result.failed}",
    ]
    if result.ignored_files:
        lines.append(f"- 已忽略的非 docx 文件：{', '.join(result.ignored_files)}")
    lines.extend(["", "任务列表"])
    if result.tasks:
        for task in result.tasks:
            lines.append(f"- {task.file_name} | {task.status} | {task.summary or '-'}")
    else:
        lines.append("- 当前没有可执行的 .docx 文件。")
    if result.error_text:
        lines.extend(["", "错误信息", result.error_text])
    return "\n".join(lines) + "\n"


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
        f"- 执行模式：{processing_label}（{result.mode}）",
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
                f"- 参考文献阻断：{user_summary.get('reference_blocking_count', summary.get('reference_blocking_count', 0))}",
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
            + f"- 参考文献相关提醒：{summary.get('reference_finding_count', 0)}\n"
            + f"- 参考文献阻断：{summary.get('reference_blocking_count', 0)}"
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
    _last_fixed_docx_file: Path | None
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
        task_updated = Signal(object)

        def __init__(
            self,
            *,
            mode: str,
            input_path: Path | None,
            output_dir: Path,
            recursive: bool,
            batch_input_files: tuple[Path, ...] = (),
        ) -> None:
            super().__init__()
            self.mode = mode
            self.input_path = input_path
            self.output_dir = output_dir
            self.recursive = recursive
            self.batch_input_files = batch_input_files

        def run(self) -> None:
            if self.mode == "batch-fix" and self.input_path is not None:
                result = execute_gui_batch_task(
                    input_dir=self.input_path,
                    output_dir=self.output_dir,
                    recursive=self.recursive,
                )
            elif self.mode in {"batch-check", "batch-fix"}:
                result = execute_gui_batch_queue(
                    input_files=self.batch_input_files,
                    output_dir=self.output_dir,
                    mode="fix" if self.mode == "batch-fix" else "check",
                    progress_callback=self.task_updated.emit,
                )
            else:
                assert self.input_path is not None
                result = execute_gui_task(
                    input_file=self.input_path,
                    output_dir=self.output_dir,
                    mode=self.mode,
                )
            self.finished.emit(result)


    class ThesisFormatFixerGUI(QMainWindow, _GuiActionsMixin):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(APP_DISPLAY_NAME)
            self.resize(1120, 760)
            icon_path = resolve_app_icon_path()
            if icon_path is not None and QIcon is not None:
                icon = QIcon(str(icon_path))
                if not icon.isNull():
                    self.setWindowIcon(icon)

            self.status_var = _StatusVarAdapter(self._on_status_text_changed)
            self._last_output_dir: Path | None = None
            self._last_report_file: Path | None = None
            self._last_fixed_docx_file: Path | None = None
            self._last_user_summary_file: Path | None = None
            self._artifact_paths: tuple[Path, ...] = ()
            self._batch_input_files: tuple[Path, ...] = ()
            self._batch_ignored_files: tuple[str, ...] = ()
            self._task_records: list[BatchTaskRecord] = []
            self._selected_task_file_name: str | None = None
            self._worker_thread: QThread | None = None
            self._worker: _GuiWorker | None = None

            self._build_window()
            self.output_path_edit.setText(str(default_gui_output_dir()))
            self._refresh_mode_ui()
            self._refresh_execute_state()
            self._set_status_text("请选择单个 .docx 文件，或切换到批量模式后导入多个文件 / 文件夹。")

        def _status_parent(self) -> object | None:
            return self

        def _build_window(self) -> None:
            central = QWidget(self)
            main_layout = QVBoxLayout(central)
            main_layout.setContentsMargins(18, 18, 18, 18)
            main_layout.setSpacing(14)

            main_layout.addWidget(self._build_header())
            main_layout.addWidget(self._build_input_group())
            main_layout.addWidget(self._build_actions_group())
            main_layout.addWidget(self._build_results_group(), stretch=1)

            self.setCentralWidget(central)
            self._build_status_bar()
            self._build_menu()
            self._apply_window_style()

        def _build_header(self) -> QWidget:
            container = QWidget(self)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)

            title = QLabel("论文格式处理工作台", container)
            title.setObjectName("heroTitle")
            layout.addWidget(title)

            subtitle = QLabel(
                "主流程保持线性：先导入单个或多个 .docx，再选择检查或修复，最后查看中文摘要、任务状态和产物入口。",
                container,
            )
            subtitle.setObjectName("heroSubtitle")
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)
            return container

        def _build_input_group(self) -> QGroupBox:
            group = QGroupBox("第 1 步：选择论文文件或批量来源", self)
            layout = QFormLayout(group)
            layout.setHorizontalSpacing(12)
            layout.setVerticalSpacing(12)

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

            batch_row = QHBoxLayout()
            self.batch_files_button = QPushButton("导入多个文件", group)
            self.batch_files_button.clicked.connect(self._pick_batch_files)
            batch_row.addWidget(self.batch_files_button)
            self.batch_folder_button = QPushButton("导入文件夹", group)
            self.batch_folder_button.clicked.connect(self._pick_batch_directory)
            batch_row.addWidget(self.batch_folder_button)
            self.clear_batch_button = QPushButton("清空批量列表", group)
            self.clear_batch_button.clicked.connect(self._clear_batch_inputs)
            batch_row.addWidget(self.clear_batch_button)
            batch_row.addStretch(1)
            self.batch_actions_container = self._wrap_row(batch_row)
            layout.addRow("批量导入", self.batch_actions_container)

            self.output_path_edit = QLineEdit(group)
            self.output_path_edit.setPlaceholderText("选择输出目录，用于保存报告和修复结果")
            self.output_path_edit.textChanged.connect(self._refresh_execute_state)
            output_row = QHBoxLayout()
            output_row.addWidget(self.output_path_edit)
            self.output_browse_button = QPushButton("选择输出目录", group)
            self.output_browse_button.clicked.connect(self._pick_output_dir)
            output_row.addWidget(self.output_browse_button)
            layout.addRow("输出目录", self._wrap_row(output_row))

            self.mode_combo = QComboBox(group)
            self.mode_combo.addItem("检查格式", "check")
            self.mode_combo.addItem("修复格式", "fix")
            self.mode_combo.addItem("批量检查", "batch-check")
            self.mode_combo.addItem("批量修复", "batch-fix")
            self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
            self.recursive_checkbox = QCheckBox("递归扫描子目录", group)
            self.recursive_checkbox.setChecked(True)
            self.recursive_checkbox.toggled.connect(self._refresh_execute_state)
            self.mode_combo.hide()

            self.mode_hint_label = QLabel(group)
            self.mode_hint_label.setObjectName("modeHintLabel")
            self.mode_hint_label.setWordWrap(True)
            layout.addRow("文件要求", self.mode_hint_label)
            return group

        def _build_actions_group(self) -> QGroupBox:
            group = QGroupBox("第 2 步：选择操作并执行", self)
            layout = QVBoxLayout(group)
            layout.setSpacing(10)

            helper = QLabel(
                "先选择“检查格式”或“修复格式”，再点击“开始执行”。完成后可直接打开修复后文档、用户摘要、技术报告和输出目录。",
                group,
            )
            helper.setObjectName("sectionHelper")
            helper.setWordWrap(True)
            layout.addWidget(helper)

            mode_row = QHBoxLayout()
            mode_row.setSpacing(10)
            self.check_mode_button = QPushButton("检查格式", group)
            self.check_mode_button.setCheckable(True)
            self.check_mode_button.clicked.connect(lambda: self._set_single_file_mode("check"))
            mode_row.addWidget(self.check_mode_button)

            self.fix_mode_button = QPushButton("修复格式", group)
            self.fix_mode_button.setCheckable(True)
            self.fix_mode_button.clicked.connect(lambda: self._set_single_file_mode("fix"))
            mode_row.addWidget(self.fix_mode_button)

            self.batch_check_mode_button = QPushButton("批量检查", group)
            self.batch_check_mode_button.setCheckable(True)
            self.batch_check_mode_button.clicked.connect(lambda: self._set_single_file_mode("batch-check"))
            mode_row.addWidget(self.batch_check_mode_button)

            self.batch_fix_mode_button = QPushButton("批量修复", group)
            self.batch_fix_mode_button.setCheckable(True)
            self.batch_fix_mode_button.clicked.connect(lambda: self._set_single_file_mode("batch-fix"))
            mode_row.addWidget(self.batch_fix_mode_button)
            mode_row.addStretch(1)
            layout.addLayout(mode_row)

            primary_row = QHBoxLayout()
            primary_row.setSpacing(10)

            self.run_button = QPushButton("开始执行", group)
            self.run_button.setObjectName("primaryActionButton")
            self.run_button.clicked.connect(self._execute)
            primary_row.addWidget(self.run_button)

            self.reset_button = QPushButton("重置", group)
            self.reset_button.clicked.connect(self._reset_form)
            primary_row.addWidget(self.reset_button)
            primary_row.addStretch(1)
            layout.addLayout(primary_row)

            secondary_row = QHBoxLayout()
            secondary_row.setSpacing(8)

            self.open_output_button = QPushButton("打开输出目录", group)
            self.open_output_button.clicked.connect(self._open_output_dir)
            secondary_row.addWidget(self.open_output_button)

            self.open_fixed_docx_button = QPushButton("打开修复后文件", group)
            self.open_fixed_docx_button.clicked.connect(self._open_fixed_docx)
            secondary_row.addWidget(self.open_fixed_docx_button)

            self.open_report_button = QPushButton("打开关键报告", group)
            self.open_report_button.clicked.connect(self._open_detailed_report)
            secondary_row.addWidget(self.open_report_button)

            self.open_user_summary_button = QPushButton("打开用户摘要", group)
            self.open_user_summary_button.clicked.connect(self._open_user_summary)
            secondary_row.addWidget(self.open_user_summary_button)

            self.export_user_summary_button = QPushButton("导出用户摘要", group)
            self.export_user_summary_button.clicked.connect(self._export_user_summary)
            secondary_row.addWidget(self.export_user_summary_button)

            secondary_row.addStretch(1)
            layout.addLayout(secondary_row)
            _set_widget_enabled(self.open_output_button, False)
            _set_widget_enabled(self.open_fixed_docx_button, False)
            _set_widget_enabled(self.open_report_button, False)
            self._set_user_summary_action_state()
            return group

        def _build_results_group(self) -> QGroupBox:
            group = QGroupBox("第 3 步：查看结果摘要与产物入口", self)
            layout = QVBoxLayout(group)
            layout.setSpacing(10)

            overview = QWidget(group)
            overview_layout = QVBoxLayout(overview)
            overview_layout.setContentsMargins(0, 0, 0, 0)
            overview_layout.setSpacing(8)

            self.result_state_label = QLabel("等待执行", overview)
            self.result_state_label.setObjectName("resultStateLabel")
            self.result_state_label.setWordWrap(True)
            overview_layout.addWidget(self.result_state_label)

            metrics_grid = QGridLayout()
            metrics_grid.setContentsMargins(0, 0, 0, 0)
            metrics_grid.setHorizontalSpacing(10)
            metrics_grid.setVerticalSpacing(10)
            self.auto_fixed_value_label = self._build_metric_card("已自动处理", "0")
            self.not_fixed_value_label = self._build_metric_card("未自动修改", "0")
            self.manual_review_value_label = self._build_metric_card("人工复核", "0")
            self.reference_reminder_value_label = self._build_metric_card("参考文献提醒", "0")
            self.reference_blocking_value_label = self._build_metric_card("参考文献阻断", "0")
            metrics_grid.addWidget(self.auto_fixed_value_label.parentWidget(), 0, 0)
            metrics_grid.addWidget(self.not_fixed_value_label.parentWidget(), 0, 1)
            metrics_grid.addWidget(self.manual_review_value_label.parentWidget(), 0, 2)
            metrics_grid.addWidget(self.reference_reminder_value_label.parentWidget(), 1, 0)
            metrics_grid.addWidget(self.reference_blocking_value_label.parentWidget(), 1, 1)
            overview_layout.addLayout(metrics_grid)

            self.next_step_label = QLabel("执行完成后，这里会直接告诉你最重要的结果和下一步。", overview)
            self.next_step_label.setObjectName("nextStepLabel")
            self.next_step_label.setWordWrap(True)
            overview_layout.addWidget(self.next_step_label)

            layout.addWidget(overview)

            task_panel = QWidget(group)
            task_panel_layout = QHBoxLayout(task_panel)
            task_panel_layout.setContentsMargins(0, 0, 0, 0)
            task_panel_layout.setSpacing(8)
            task_panel_layout.addWidget(QLabel("任务状态筛选", task_panel))
            self.task_filter_combo = QComboBox(task_panel)
            self.task_filter_combo.addItem("全部任务", "all")
            self.task_filter_combo.addItem("待处理", "pending")
            self.task_filter_combo.addItem("处理中", "running")
            self.task_filter_combo.addItem("已完成", "success")
            self.task_filter_combo.addItem("失败", "failed")
            self.task_filter_combo.currentIndexChanged.connect(self._refresh_task_list)
            task_panel_layout.addWidget(self.task_filter_combo)
            task_panel_layout.addStretch(1)
            layout.addWidget(task_panel)

            self.task_list = QListWidget(group)
            self.task_list.itemSelectionChanged.connect(self._on_task_selection_changed)
            layout.addWidget(self.task_list)

            splitter = QSplitter(Qt.Vertical, group)

            summary_container = QWidget(splitter)
            summary_layout = QVBoxLayout(summary_container)
            summary_layout.setContentsMargins(0, 0, 0, 0)
            summary_layout.addWidget(QLabel("用户版中文摘要", summary_container))
            self.summary_text = QTextEdit(summary_container)
            self.summary_text.setReadOnly(True)
            self.summary_text.setPlaceholderText("执行成功后，这里会优先展示面向普通用户的中文摘要。")
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
            splitter.setStretchFactor(0, 2)
            splitter.setStretchFactor(1, 2)
            layout.addWidget(splitter)
            return group

        def _build_metric_card(self, title: str, value: str) -> QLabel:
            card = QWidget(self)
            card.setObjectName("metricCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(4)

            title_label = QLabel(title, card)
            title_label.setObjectName("metricTitleLabel")
            layout.addWidget(title_label)

            value_label = QLabel(value, card)
            value_label.setObjectName("metricValueLabel")
            layout.addWidget(value_label)
            return value_label

        def _apply_window_style(self) -> None:
            self.setStyleSheet(
                """
                QMainWindow {
                    background: #f4f1ea;
                }
                QGroupBox {
                    border: 1px solid #d9d2c5;
                    border-radius: 10px;
                    margin-top: 12px;
                    padding: 12px;
                    background: #fffdf8;
                    font-weight: 600;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 4px;
                }
                QLabel#heroTitle {
                    font-size: 24px;
                    font-weight: 700;
                    color: #2c241d;
                }
                QLabel#heroSubtitle, QLabel#sectionHelper, QLabel#modeHintLabel {
                    color: #66594c;
                    line-height: 1.4;
                }
                QPushButton {
                    min-height: 34px;
                    padding: 6px 14px;
                }
                QPushButton#primaryActionButton {
                    background: #2f6f5e;
                    color: white;
                    border: 1px solid #2f6f5e;
                    border-radius: 8px;
                    font-weight: 700;
                    min-width: 132px;
                }
                QPushButton#primaryActionButton:disabled {
                    background: #9db6ad;
                    border-color: #9db6ad;
                }
                QPushButton:checked {
                    background: #d8ebe4;
                    border: 1px solid #2f6f5e;
                    color: #234c40;
                    font-weight: 700;
                }
                QWidget#metricCard {
                    background: #f7f4ed;
                    border: 1px solid #e0d9cd;
                    border-radius: 10px;
                }
                QLabel#metricTitleLabel {
                    color: #7b6a58;
                }
                QLabel#metricValueLabel {
                    font-size: 24px;
                    font-weight: 700;
                    color: #2f6f5e;
                }
                QLabel#resultStateLabel {
                    background: #efe7d8;
                    border: 1px solid #e0d2b8;
                    border-radius: 8px;
                    padding: 10px 12px;
                    color: #4b3e30;
                    font-weight: 600;
                }
                QLabel#nextStepLabel {
                    color: #4b3e30;
                    background: #f7f4ed;
                    border-radius: 8px;
                    padding: 8px 10px;
                }
                QTextEdit, QListWidget, QLineEdit, QComboBox {
                    background: white;
                    border: 1px solid #d8d1c6;
                    border-radius: 8px;
                }
                QListWidget::item {
                    padding: 8px 6px;
                }
                """
            )

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
            batch_queue_mode = self._mode() in {"batch-check", "batch-fix"}
            self.input_label.setText("批量来源" if batch_queue_mode else "论文文件")
            self.input_path_edit.setPlaceholderText(
                "导入多个 .docx 文件，或从文件夹中批量读取" if batch_queue_mode else "选择待检查或修复的 .docx 文件"
            )
            self.recursive_checkbox.setVisible(batch_queue_mode)
            self.batch_actions_container.setVisible(batch_queue_mode)
            self.input_browse_button.setVisible(not batch_queue_mode)
            self.input_path_edit.setReadOnly(batch_queue_mode)
            self.input_browse_button.setText("选择目录" if batch_mode else "选择输入")
            if batch_queue_mode:
                hint = "批量处理会先生成任务队列，再逐个复用现有单文件能力执行。可按状态筛选，并查看每个任务的中文摘要与产物入口。"
                self.mode_hint_label.setText(hint)
                self._refresh_batch_input_display()
            elif self._mode() == "fix":
                self.mode_hint_label.setText("仅支持单个 .docx 文件。修复格式会生成修复后文档，并同时保留用户摘要和技术报告。")
            else:
                self.mode_hint_label.setText("仅支持单个 .docx 文件。检查格式不会修改原文档，适合先看异常项和人工复核项。")
            self.check_mode_button.setChecked(self._mode() == "check")
            self.fix_mode_button.setChecked(self._mode() == "fix")
            self.batch_check_mode_button.setChecked(self._mode() == "batch-check")
            self.batch_fix_mode_button.setChecked(self._mode() == "batch-fix")

        def _refresh_execute_state(self) -> None:
            input_value = self.input_path_edit.text().strip()
            output_value = self.output_path_edit.text().strip()
            batch_queue_mode = self._mode() in {"batch-check", "batch-fix"}
            has_input = bool(self._batch_input_files) if batch_queue_mode else bool(input_value)
            enabled = bool(has_input and output_value and self._worker_thread is None)
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

        def _pick_batch_files(self) -> None:
            if filedialog is None:
                return
            raw_paths = filedialog.askopenfilenames(parent=self, title="选择多个论文文件")
            if not raw_paths:
                return
            selected, ignored = filter_batch_import_paths(tuple(Path(item) for item in raw_paths))
            self._batch_input_files = selected
            self._batch_ignored_files = ignored
            self._refresh_batch_input_display()

        def _pick_batch_directory(self) -> None:
            if filedialog is None:
                return
            raw_path = filedialog.askdirectory(parent=self, title="选择批量导入文件夹")
            if not raw_path:
                return
            source_path = Path(raw_path)
            selected, ignored = collect_docx_files_from_directory(
                source_path,
                recursive=self.recursive_checkbox.isChecked(),
            )
            self._batch_input_files = selected
            self._batch_ignored_files = ignored
            self._refresh_batch_input_display(source_path=source_path)

        def _clear_batch_inputs(self) -> None:
            self._batch_input_files = ()
            self._batch_ignored_files = ()
            self.input_path_edit.clear()
            self.input_path_edit.setToolTip("")
            self._refresh_execute_state()
            self._set_status_text("批量导入列表已清空。")

        def _refresh_batch_input_display(self, *, source_path: Path | None = None) -> None:
            if not self._batch_input_files:
                self.input_path_edit.setText("")
                self.input_path_edit.setToolTip("")
                self._refresh_execute_state()
                return
            prefix = f"{source_path}：" if source_path is not None else ""
            text = f"{prefix}已导入 {len(self._batch_input_files)} 个 .docx 文件"
            if self._batch_ignored_files:
                text += f"，已忽略 {len(self._batch_ignored_files)} 个非 docx 文件"
            self.input_path_edit.setText(text)
            tooltip = [str(path) for path in self._batch_input_files[:20]]
            if self._batch_ignored_files:
                tooltip.extend(["", "已忽略：", *self._batch_ignored_files[:20]])
            self.input_path_edit.setToolTip("\n".join(tooltip))
            self._refresh_execute_state()

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

        def _validate_before_run(self) -> tuple[Path | None, Path, str, bool, tuple[Path, ...]] | None:
            input_value = self.input_path_edit.text().strip()
            output_value = self.output_path_edit.text().strip()
            mode = self._mode()
            batch_queue_mode = mode in {"batch-check", "batch-fix"}

            if not input_value and not batch_queue_mode:
                self._set_status_text("请先选择输入文件或输入目录。")
                if messagebox is not None:
                    messagebox.showwarning("缺少输入", "请先选择输入文件或输入目录。", parent=self)
                return None
            if batch_queue_mode and not self._batch_input_files:
                text = "请先导入至少一个 .docx 文件，或从文件夹中批量读取。"
                self._set_status_text(text)
                if messagebox is not None:
                    messagebox.showwarning("缺少批量输入", text, parent=self)
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

            if batch_queue_mode:
                return None, output_dir, mode, self.recursive_checkbox.isChecked(), self._batch_input_files

            if not input_path.exists():
                text = "输入文件不存在。"
                self._set_status_text(text)
                if messagebox is not None:
                    messagebox.showwarning("输入文件不存在", text, parent=self)
                return None
            if input_path.is_dir() or input_path.suffix.lower() != ".docx":
                text = "仅支持 .docx 论文文件，请重新选择。"
                self._set_status_text(text)
                if messagebox is not None:
                    messagebox.showwarning("输入文件无效", text, parent=self)
                return None
            return input_path, output_dir, mode, False, ()

        def _set_single_file_mode(self, mode: str) -> None:
            index = self.mode_combo.findData(mode)
            if index >= 0:
                self.mode_combo.setCurrentIndex(index)

        def _set_busy(self, busy: bool) -> None:
            controls = (
                self.check_mode_button,
                self.fix_mode_button,
                self.batch_check_mode_button,
                self.batch_fix_mode_button,
                self.run_button,
                self.reset_button,
                self.input_browse_button,
                self.batch_files_button,
                self.batch_folder_button,
                self.clear_batch_button,
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

            input_path, output_dir, mode, recursive, batch_input_files = validated
            self._set_busy(True)
            self.summary_text.clear()
            self.detail_text.clear()
            self.task_list.clear()
            self.artifact_list.clear()
            self._task_records = []
            self._selected_task_file_name = None
            self._set_result_overview(
                state_text="正在执行，请稍候……",
                auto_fixed=0,
                not_fixed=0,
                manual_review=0,
                reference_reminder=0,
                reference_blocking=0,
                next_step="处理过程中会生成适合普通用户阅读的摘要，并在完成后集中提供文件入口。",
            )
            self._set_status_text("正在执行，请稍候……")
            self.output_label.setText(f"最近输出：{output_dir}")

            self._worker_thread = QThread(self)
            self._worker = _GuiWorker(
                mode=mode,
                input_path=input_path,
                output_dir=output_dir,
                recursive=recursive,
                batch_input_files=batch_input_files,
            )
            self._worker.moveToThread(self._worker_thread)
            self._worker_thread.started.connect(self._worker.run)
            self._worker.task_updated.connect(self._handle_task_progress)
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
            if isinstance(result, GuiBatchQueueExecutionResult):
                self._apply_batch_queue_result(result)
                return
            if isinstance(result, GuiBatchExecutionResult):
                self._apply_batch_result(result)
                return
            if isinstance(result, GuiExecutionResult):
                self._apply_single_result(result)

        def _handle_task_progress(self, task: object) -> None:
            if not isinstance(task, BatchTaskRecord):
                return
            for index, current in enumerate(self._task_records):
                if current.file_name == task.file_name and current.file_path == task.file_path:
                    self._task_records[index] = task
                    break
            else:
                self._task_records.append(task)
            if self._selected_task_file_name is None:
                self._selected_task_file_name = task.file_name
            self._refresh_task_list()
            self._apply_batch_queue_overview_from_tasks()

        def _apply_single_result(self, result: GuiExecutionResult) -> None:
            self.detail_text.setPlainText(format_gui_result(result))
            self._last_output_dir = result.output_dir
            self._last_report_file = None
            self._last_fixed_docx_file = None
            self._last_user_summary_file = None

            artifacts = result.payload.get("artifacts", {}) if isinstance(result.payload, dict) else {}
            self._artifact_paths = self._collect_artifacts(artifacts, result.generated_files)
            self._populate_artifacts()

            if isinstance(artifacts, dict):
                self._last_fixed_docx_file = self._pick_existing_path(artifacts.get("fixed_docx"))
                self._last_report_file = self._pick_existing_path(
                    artifacts.get("technical_report_md"),
                    artifacts.get("report_md"),
                    artifacts.get("technical_report_json"),
                    artifacts.get("report_json"),
                )
                self._last_user_summary_file = self._pick_existing_path(artifacts.get("user_summary_md"))

            self._set_user_summary_action_state()
            _set_widget_enabled(self.open_output_button, result.output_dir.exists())
            _set_widget_enabled(self.open_fixed_docx_button, self._last_fixed_docx_file is not None)
            _set_widget_enabled(self.open_report_button, self._last_report_file is not None)

            summary_text = self._build_primary_summary_for_single(result)
            self.summary_text.setPlainText(summary_text)
            self._apply_single_result_overview(result)
            if result.success:
                self._set_status_text("执行完成。用户摘要已更新。")
            else:
                self._set_status_text("执行失败。请先查看中文提示，再根据详细结果排查。")
                if result.error_text and messagebox is not None:
                    messagebox.showerror("执行失败", f"本次处理未完成。\n\n{result.error_text}", parent=self)

        def _apply_batch_result(self, result: GuiBatchExecutionResult) -> None:
            self.detail_text.setPlainText(format_gui_batch_result(result))
            self._last_output_dir = result.output_dir
            self._last_fixed_docx_file = None
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
            _set_widget_enabled(self.open_fixed_docx_button, False)
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
            self._apply_batch_result_overview(result)

            if result.success:
                self._set_status_text("批量修复完成。")
            elif warning and result.total_files == 0 and result.failed == 0:
                self._set_status_text("批量处理已完成，但输入目录中未找到 .docx 文件。")
            else:
                self._set_status_text("批量修复结束，但存在失败或摘要异常。")
                if result.error_text and messagebox is not None:
                    messagebox.showerror("批量修复未完全成功", result.error_text, parent=self)

        def _apply_batch_queue_result(self, result: GuiBatchQueueExecutionResult) -> None:
            self._task_records = list(result.tasks)
            self.detail_text.setPlainText(format_gui_batch_queue_result(result))
            self._last_output_dir = result.output_dir
            self._last_fixed_docx_file = None
            self._last_report_file = None
            self._last_user_summary_file = None
            self._artifact_paths = ()
            self._refresh_task_list()
            self._apply_batch_queue_overview_from_tasks()
            if self._task_records:
                if self._selected_task_file_name is None:
                    self._selected_task_file_name = self._task_records[0].file_name
                self._show_task_detail_by_name(self._selected_task_file_name)
            else:
                self.summary_text.setPlainText("当前没有可执行的 .docx 文件。")
                self.artifact_list.clear()
            _set_widget_enabled(self.open_output_button, result.output_dir.exists())
            _set_widget_enabled(self.open_fixed_docx_button, False)
            _set_widget_enabled(self.open_report_button, False)
            self._set_user_summary_action_state()

            if result.failed > 0:
                self._set_status_text("批量任务已完成，但存在失败文件。")
            elif result.total_files == 0:
                self._set_status_text("批量任务已完成，但没有可处理的 .docx 文件。")
            else:
                self._set_status_text("批量任务已完成，可按状态筛选并查看单任务摘要。")

        def _apply_batch_queue_overview_from_tasks(self) -> None:
            total = len(self._task_records)
            pending = sum(1 for item in self._task_records if item.status == "pending")
            running = sum(1 for item in self._task_records if item.status == "running")
            succeeded = sum(1 for item in self._task_records if item.status == "success")
            failed = sum(1 for item in self._task_records if item.status == "failed")
            if running > 0:
                state_text = f"批量任务执行中：{running} 个处理中，{pending} 个待处理。"
                next_step = "下一步：可先观察任务状态，完成后点选单个任务查看中文摘要。"
            elif failed > 0:
                state_text = f"批量任务已完成，但有 {failed} 个失败，{succeeded} 个成功。"
                next_step = "下一步：按“失败”筛选，先查看错误信息，再回到成功任务查看对应产物。"
            elif total == 0:
                state_text = "当前还没有批量任务。"
                next_step = "下一步：导入多个 .docx 文件或选择一个包含论文的文件夹。"
            else:
                state_text = f"批量任务已完成，{succeeded} 个任务处理成功。"
                next_step = "下一步：点选任一任务，查看用户版摘要，并按需要打开产物。"
            self._set_result_overview(
                state_text=state_text,
                auto_fixed=succeeded,
                not_fixed=failed,
                manual_review=pending + running,
                reference_reminder=0,
                reference_blocking=0,
                next_step=next_step,
            )

        def _refresh_task_list(self) -> None:
            filter_value = str(self.task_filter_combo.currentData())
            self.task_list.clear()
            for task in self._task_records:
                if filter_value != "all" and task.status != filter_value:
                    continue
                item = QListWidgetItem(f"{task.file_name} | {task.status}")
                item.setData(Qt.UserRole, task.file_name)
                item.setToolTip(str(task.file_path))
                self.task_list.addItem(item)
                if self._selected_task_file_name == task.file_name:
                    item.setSelected(True)

        def _on_task_selection_changed(self) -> None:
            item = self.task_list.currentItem()
            if item is None:
                return
            task_name = item.data(Qt.UserRole)
            if not isinstance(task_name, str):
                return
            self._selected_task_file_name = task_name
            self._show_task_detail_by_name(task_name)

        def _show_task_detail_by_name(self, task_name: str | None) -> None:
            if not task_name:
                return
            task = next((item for item in self._task_records if item.file_name == task_name), None)
            if task is None:
                return
            self.summary_text.setPlainText(self._build_batch_task_summary_text(task))
            self.detail_text.setPlainText(format_batch_task_detail(task))
            self._apply_task_artifacts(task)

        def _build_batch_task_summary_text(self, task: BatchTaskRecord) -> str:
            summary_path_raw = task.artifact_paths.get("user_summary_md")
            if isinstance(summary_path_raw, str) and summary_path_raw.strip():
                summary_path = Path(summary_path_raw)
                if summary_path.exists():
                    return summary_path.read_text(encoding="utf-8")
            return format_batch_task_detail(task)

        def _apply_task_artifacts(self, task: BatchTaskRecord) -> None:
            self.artifact_list.clear()
            self._last_fixed_docx_file = self._pick_existing_path(task.artifact_paths.get("fixed_docx"))
            self._last_report_file = self._pick_existing_path(
                task.artifact_paths.get("technical_report_md"),
                task.artifact_paths.get("report_md"),
                task.artifact_paths.get("technical_report_json"),
                task.artifact_paths.get("report_json"),
            )
            self._last_user_summary_file = self._pick_existing_path(task.artifact_paths.get("user_summary_md"))
            self._last_output_dir = self._pick_existing_path(task.artifact_paths.get("output_dir")) or self._last_output_dir
            self._set_user_summary_action_state()
            _set_widget_enabled(self.open_fixed_docx_button, self._last_fixed_docx_file is not None)
            _set_widget_enabled(self.open_report_button, self._last_report_file is not None)
            _set_widget_enabled(self.open_output_button, self._last_output_dir is not None)
            for key, value in task.artifact_paths.items():
                path = Path(value)
                if not path.exists() or path.is_dir():
                    continue
                item = QListWidgetItem(f"{key} | {path.name}")
                item.setData(Qt.UserRole, str(path))
                item.setToolTip(str(path))
                self.artifact_list.addItem(item)

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
                f"参考文献阻断数量：{summary.get('reference_blocking_count', 0)}",
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

        def _apply_single_result_overview(self, result: GuiExecutionResult) -> None:
            summary = result.payload.get("summary", {}) if isinstance(result.payload, dict) else {}
            user_summary = result.payload.get("user_summary", {}) if isinstance(result.payload, dict) else {}
            auto_fixed = int(user_summary.get("auto_fixed_count", summary.get("auto_fix_rule_count", 0)))
            not_fixed = int(
                user_summary.get(
                    "detected_not_auto_modified_count",
                    summary.get("detected_not_auto_modified_count", 0),
                )
            )
            manual_review = int(
                user_summary.get(
                    "manual_review_required_count",
                    summary.get("manual_review_required_count", 0),
                )
            )
            reference_reminder = int(
                user_summary.get("reference_reminder_count", summary.get("reference_finding_count", 0))
            )
            reference_blocking = int(
                user_summary.get("reference_blocking_count", summary.get("reference_blocking_count", 0))
            )
            overall_status = str(user_summary.get("overall_status", "")).strip()
            if not overall_status:
                overall_status = "执行成功。" if result.success else "执行失败。"

            next_step = "建议先阅读上方中文摘要，再按需要打开报告或输出目录。"
            next_steps = user_summary.get("next_steps", [])
            if isinstance(next_steps, list) and next_steps:
                first_step = next((item for item in next_steps if isinstance(item, str) and item.strip()), "")
                if first_step:
                    next_step = f"下一步：{first_step}"
            elif result.error_text:
                next_step = f"下一步：先根据失败提示排查输入文件、输出目录或详细日志。"

            state_prefix = "本次结果"
            if result.mode == "fix":
                state_prefix = "修复结果"
            elif result.mode == "check":
                state_prefix = "检查结果"
            self._set_result_overview(
                state_text=f"{state_prefix}：{overall_status}",
                auto_fixed=auto_fixed,
                not_fixed=not_fixed,
                manual_review=manual_review,
                reference_reminder=reference_reminder,
                reference_blocking=reference_blocking,
                next_step=next_step,
            )

        def _apply_batch_result_overview(self, result: GuiBatchExecutionResult) -> None:
            if result.failed > 0:
                state_text = f"批量修复已完成，但有 {result.failed} 个文件处理失败。"
                next_step = "下一步：先打开批处理摘要，优先查看失败文件与对应报告。"
            elif result.total_files == 0:
                state_text = "批量处理已完成，但当前输入目录中没有可处理的 .docx 文件。"
                next_step = "下一步：请确认输入目录路径是否正确，并放入待处理论文文件。"
            else:
                state_text = f"批量修复已完成，{result.succeeded} 个文件处理成功。"
                next_step = "下一步：抽查修复后文件，并结合批处理摘要确认是否仍有人工复核项。"
            self._set_result_overview(
                state_text=state_text,
                auto_fixed=result.succeeded,
                not_fixed=result.failed,
                manual_review=max(result.total_files - result.succeeded - result.failed, 0),
                reference_reminder=0,
                reference_blocking=0,
                next_step=next_step,
            )

        def _set_result_overview(
            self,
            *,
            state_text: str,
            auto_fixed: int,
            not_fixed: int,
            manual_review: int,
            reference_reminder: int,
            reference_blocking: int,
            next_step: str,
        ) -> None:
            self.result_state_label.setText(state_text)
            self.auto_fixed_value_label.setText(str(auto_fixed))
            self.not_fixed_value_label.setText(str(not_fixed))
            self.manual_review_value_label.setText(str(manual_review))
            self.reference_reminder_value_label.setText(str(reference_reminder))
            self.reference_blocking_value_label.setText(str(reference_blocking))
            self.next_step_label.setText(next_step)

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
                label = self._artifact_label(path)
                item = QListWidgetItem(f"{label} | {path.name}")
                item.setData(Qt.UserRole, str(path))
                item.setToolTip(str(path))
                self.artifact_list.addItem(item)

        def _artifact_label(self, path: Path) -> str:
            name = path.name
            if name == "batch_summary.md":
                return "批处理摘要"
            if name == "batch_summary.json":
                return "批处理数据"
            if name.endswith(".fixed.docx"):
                return "修复后文件"
            if name.endswith(".report.md"):
                return "技术报告"
            if name.endswith(".report.json"):
                return "技术数据"
            if name.endswith(".user_summary.md"):
                return "用户摘要"
            return "输出文件"

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

        def _open_fixed_docx(self) -> None:
            if self._last_fixed_docx_file is None:
                self._set_status_text("当前还没有可打开的修复后文件。")
                return
            try:
                open_file(self._last_fixed_docx_file)
                self._set_status_text(f"已打开修复后文件：{self._last_fixed_docx_file}")
            except Exception as exc:  # pragma: no cover - platform dependent
                if messagebox is not None:
                    messagebox.showerror("打开修复后文件失败", str(exc), parent=self)
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
            self._batch_input_files = ()
            self._batch_ignored_files = ()
            self._task_records = []
            self._selected_task_file_name = None
            self.summary_text.clear()
            self.detail_text.clear()
            self.task_list.clear()
            self.artifact_list.clear()
            self._last_output_dir = None
            self._last_report_file = None
            self._last_fixed_docx_file = None
            self._last_user_summary_file = None
            self._artifact_paths = ()
            _set_widget_enabled(self.open_output_button, False)
            _set_widget_enabled(self.open_fixed_docx_button, False)
            _set_widget_enabled(self.open_report_button, False)
            self._set_user_summary_action_state()
            self.output_label.setText("最近输出：-")
            self._set_result_overview(
                state_text="等待执行",
                auto_fixed=0,
                not_fixed=0,
                manual_review=0,
                reference_reminder=0,
                reference_blocking=0,
                next_step="执行完成后，这里会直接告诉你最重要的结果和下一步。",
            )
            self._set_status_text("已重置。请选择新的 .docx 文件；输出目录已恢复为默认路径。")
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
    apply_gui_application_metadata(app)
    window = ThesisFormatFixerGUI()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
