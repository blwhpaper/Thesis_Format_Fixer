"""Minimal single-file GUI wrapper for thesis-format-fixer."""

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

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except Exception as exc:  # pragma: no cover - environment dependent
    tk = None
    filedialog = None
    messagebox = None
    _TK_IMPORT_ERROR = exc
else:
    _TK_IMPORT_ERROR = None


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

    output_dir.mkdir(parents=True, exist_ok=True)
    report_json, report_md = _default_report_paths(input_file, output_dir, normalized_mode)
    generated_files: list[Path] = []

    try:
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
            generated_files=tuple(path for path in generated_files if path.exists()),
            payload={},
            error_text=str(exc),
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
        f"- 本次处理类型：{processing_label}",
        f"- 输入文件：{result.input_file}",
        f"- 输出目录：{result.output_dir}",
        f"- 执行状态：{'成功' if result.success else '失败'}（exit_code={result.exit_code}）",
    ]

    if isinstance(user_summary, dict) and user_summary:
        lines.extend(
            [
                "",
                "用户版中文摘要",
                f"- 总体状态：{user_summary.get('overall_status', '')}",
                f"- 自动修复数量：{user_summary.get('auto_fixed_count', summary.get('auto_fix_rule_count', 0))}",
                "- "
                + "检测到但未自动修改数量："
                + str(
                    user_summary.get(
                        "detected_not_auto_modified_count",
                        summary.get("detected_not_auto_modified_count", 0),
                    )
                ),
                f"- 需要人工复核数量：{user_summary.get('manual_review_required_count', summary.get('manual_review_required_count', 0))}",
                f"- 参考文献相关提醒数量：{user_summary.get('reference_reminder_count', summary.get('reference_finding_count', 0))}",
                f"- 脚注相关提醒数量：{user_summary.get('footnote_reminder_count', 0)}",
                f"- 其他提示数量：{user_summary.get('other_reminder_count', 0)}",
            ]
        )
        key_issues = user_summary.get("key_issues", [])
        if isinstance(key_issues, list) and key_issues:
            lines.append("- 关键问题清单：")
            lines.extend(f"  - {item}" for item in key_issues if isinstance(item, str) and item.strip())
        next_steps = user_summary.get("next_steps", [])
        if isinstance(next_steps, list) and next_steps:
            lines.append("- 建议下一步：")
            lines.extend(f"  - {item}" for item in next_steps if isinstance(item, str) and item.strip())
    elif summary:
        lines.append(
            "\n用户版中文摘要\n"
            + f"- 自动修复数量：{summary.get('auto_fix_rule_count', 0)}\n"
            + f"- 检测到但未自动修改数量：{summary.get('detected_not_auto_modified_count', 0)}\n"
            + f"- 需要人工复核数量：{summary.get('manual_review_required_count', 0)}\n"
            + f"- 参考文献相关提醒数量：{summary.get('reference_finding_count', 0)}"
        )

    lines.extend(["", "文件出口"])
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
        lines.append(f"- 用户版摘要文件：{user_summary_md}")

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

    output_dir.mkdir(parents=True, exist_ok=True)
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
            error_text=str(exc),
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
    success = (code == 0) and parse_error is None
    error_text = parse_error
    if code != 0:
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
    lines = [
        "mode: batch-fix",
        f"input_dir: {result.input_dir}",
        f"output_dir: {result.output_dir}",
        f"recursive: {result.recursive}",
        f"status: {'success' if result.success else 'failure'} (exit_code={result.exit_code})",
        f"batch_summary_json: {result.output_dir / 'batch_summary.json'}",
        f"batch_summary_md: {result.output_dir / 'batch_summary.md'}",
        "summary:",
        f"- total_files: {result.total_files}",
        f"- succeeded: {result.succeeded}",
        f"- failed: {result.failed}",
        "per_file_status:",
    ]
    if result.items:
        for item in result.items:
            lines.append(
                "- "
                + f"exit_code={item.get('exit_code')} "
                + f"input={item.get('input_file')} "
                + f"output={item.get('output_docx')}"
            )
    else:
        lines.append("- (none)")

    if warning:
        lines.append(f"warning: {warning}")

    if result.error_text:
        lines.extend(["error:", result.error_text.strip()])
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


class ThesisFormatFixerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("论文格式检查修复工具 - GUI 用户版")
        self.root.geometry("860x600")

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="check")
        self.input_label_var = tk.StringVar(value="输入 .docx")
        self.status_var = tk.StringVar(value="就绪")
        self._last_output_dir: Path | None = None
        self._last_report_file: Path | None = None
        self._last_user_summary_file: Path | None = None

        self._build_layout()

    def _build_layout(self) -> None:
        root = self.root
        root.columnconfigure(1, weight=1)
        root.rowconfigure(5, weight=1)

        tk.Label(root, textvariable=self.input_label_var).grid(row=0, column=0, padx=8, pady=8, sticky="w")
        tk.Entry(root, textvariable=self.input_var).grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        tk.Button(root, text="浏览", command=self._pick_input).grid(row=0, column=2, padx=8, pady=8)

        tk.Label(root, text="输出目录").grid(row=1, column=0, padx=8, pady=8, sticky="w")
        tk.Entry(root, textvariable=self.output_var).grid(row=1, column=1, padx=8, pady=8, sticky="ew")
        tk.Button(root, text="浏览", command=self._pick_output_dir).grid(row=1, column=2, padx=8, pady=8)

        tk.Label(root, text="处理模式").grid(row=2, column=0, padx=8, pady=8, sticky="w")
        mode_frame = tk.Frame(root)
        mode_frame.grid(row=2, column=1, padx=8, pady=8, sticky="w")
        tk.Radiobutton(
            mode_frame,
            text="仅检查",
            variable=self.mode_var,
            value="check",
            command=self._on_mode_changed,
        ).pack(side="left")
        tk.Radiobutton(
            mode_frame,
            text="检查并修复",
            variable=self.mode_var,
            value="fix",
            command=self._on_mode_changed,
        ).pack(side="left")
        tk.Radiobutton(
            mode_frame,
            text="批量修复",
            variable=self.mode_var,
            value="batch-fix",
            command=self._on_mode_changed,
        ).pack(side="left")

        button_frame = tk.Frame(root)
        button_frame.grid(row=3, column=1, columnspan=2, padx=8, pady=8, sticky="ew")
        self.run_button = tk.Button(button_frame, text="开始执行", command=self._execute)
        self.run_button.pack(side="left", padx=(0, 8))

        self.open_user_summary_button = tk.Button(
            button_frame,
            text="打开用户版摘要",
            command=self._open_user_summary,
            state="disabled",
        )
        self.open_user_summary_button.pack(side="left", padx=(0, 8))

        self.export_user_summary_button = tk.Button(
            button_frame,
            text="导出用户版摘要",
            command=self._export_user_summary,
            state="disabled",
        )
        self.export_user_summary_button.pack(side="left", padx=(0, 8))

        self.open_report_button = tk.Button(
            button_frame,
            text="打开技术报告",
            command=self._open_detailed_report,
            state="disabled",
        )
        self.open_report_button.pack(side="left", padx=(0, 8))

        self.open_button = tk.Button(button_frame, text="打开输出目录", command=self._open_output_dir, state="disabled")
        self.open_button.pack(side="left")

        tk.Label(root, textvariable=self.status_var, anchor="w").grid(
            row=4, column=0, columnspan=3, padx=8, pady=8, sticky="ew"
        )

        self.result_text = tk.Text(root, wrap="word")
        self.result_text.grid(row=5, column=0, columnspan=3, padx=8, pady=8, sticky="nsew")

    def _pick_input(self) -> None:
        assert filedialog is not None
        if self.mode_var.get() == "batch-fix":
            path = filedialog.askdirectory(title="Select Input Directory")
        else:
            path = filedialog.askopenfilename(
                title="Select DOCX",
                filetypes=[("Word Document", "*.docx"), ("All Files", "*.*")],
            )
        if path:
            self.input_var.set(path)

    def _pick_output_dir(self) -> None:
        assert filedialog is not None
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_var.set(path)

    def _on_mode_changed(self) -> None:
        mode = self.mode_var.get()
        if mode == "batch-fix":
            self.input_label_var.set("输入目录")
            self.status_var.set("批量模式：请选择包含 .docx 的输入目录。")
        else:
            self.input_label_var.set("输入 .docx")
            self.status_var.set("单文件模式：请选择一个 .docx 文件。")

    def _set_user_summary_action_state(self) -> None:
        summary_available = self._last_user_summary_file is not None and self._last_user_summary_file.exists()
        state = "normal" if summary_available else "disabled"
        self.open_user_summary_button.config(state=state)
        self.export_user_summary_button.config(state=state)

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

    def _validate_before_run(self) -> tuple[Path, Path, str] | None:
        input_value = self.input_var.get().strip()
        output_value = self.output_var.get().strip()
        mode = self.mode_var.get().strip().lower()
        if not input_value:
            self.status_var.set("请选择输入路径。")
            return None
        if not output_value:
            self.status_var.set("请选择输出目录。")
            return None
        input_path = Path(input_value)
        output_dir = Path(output_value)
        output_ok, output_error = self._ensure_output_dir_writable(output_dir)
        if not output_ok:
            self.status_var.set(output_error or "输出目录不可写。")
            return None
        if mode == "batch-fix":
            if not input_path.exists() or not input_path.is_dir():
                self.status_var.set("批量修复模式下，输入路径必须是已存在目录。")
                return None
            return input_path, output_dir, mode
        if not input_path.exists():
            self.status_var.set("输入文件不存在。")
            return None
        if input_path.is_dir():
            self.status_var.set("输入路径必须是 .docx 文件。")
            return None
        if input_path.suffix.lower() != ".docx":
            self.status_var.set("输入文件必须是 .docx。")
            return None
        return input_path, output_dir, mode

    def _execute(self) -> None:
        validated = self._validate_before_run()
        if validated is None:
            return

        input_path, output_dir, mode = validated
        self.run_button.config(state="disabled")
        self.status_var.set("正在执行，请稍候...")
        self.root.update_idletasks()

        if mode == "batch-fix":
            batch_result = execute_gui_batch_task(
                input_dir=input_path,
                output_dir=output_dir,
                recursive=True,
            )
            output_text = format_gui_batch_result(batch_result)
            run_success = batch_result.success
            run_error = batch_result.error_text
            self._last_report_file = None
            self._last_user_summary_file = None
        else:
            single_result = execute_gui_task(
                input_file=input_path,
                output_dir=output_dir,
                mode=mode,
            )
            output_text = format_gui_result(single_result)
            run_success = single_result.success
            run_error = single_result.error_text
            artifacts = single_result.payload.get("artifacts", {})
            self._last_report_file = None
            self._last_user_summary_file = None
            if isinstance(artifacts, dict):
                report_md = artifacts.get("report_md")
                report_json = artifacts.get("report_json")
                user_summary_md = artifacts.get("user_summary_md")
                if isinstance(report_md, str) and report_md.strip():
                    path = Path(report_md)
                    if path.exists():
                        self._last_report_file = path
                if self._last_report_file is None and isinstance(report_json, str) and report_json.strip():
                    path = Path(report_json)
                    if path.exists():
                        self._last_report_file = path
                if isinstance(user_summary_md, str) and user_summary_md.strip():
                    path = Path(user_summary_md)
                    if path.exists():
                        self._last_user_summary_file = path

        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", output_text)
        self._last_output_dir = output_dir
        self.open_button.config(state="normal" if output_dir.exists() else "disabled")
        self.open_report_button.config(state="normal" if self._last_report_file is not None else "disabled")
        self._set_user_summary_action_state()
        if run_success:
            self.status_var.set(f"执行完成。结果已保存到：{output_dir}")
        else:
            self.status_var.set("执行失败，请查看下方详细信息。")

        if run_error and messagebox is not None:
            messagebox.showerror("Execution Error", run_error)
        self.run_button.config(state="normal")

    def _open_output_dir(self) -> None:
        if self._last_output_dir is None:
            return
        try:
            open_directory(self._last_output_dir)
        except Exception as exc:  # pragma: no cover - platform dependent
            if messagebox is not None:
                messagebox.showerror("Open Directory Failed", str(exc))
            else:
                self.status_var.set(str(exc))

    def _open_detailed_report(self) -> None:
        if self._last_report_file is None:
            return
        try:
            open_file(self._last_report_file)
        except Exception as exc:  # pragma: no cover - platform dependent
            if messagebox is not None:
                messagebox.showerror("Open Report Failed", str(exc))
            else:
                self.status_var.set(str(exc))

    def _open_user_summary(self) -> None:
        if self._last_user_summary_file is None:
            self.status_var.set("当前没有可打开的用户版摘要，请先执行 check 或 fix。")
            return
        try:
            open_file(self._last_user_summary_file)
            self.status_var.set(f"已打开用户版摘要：{self._last_user_summary_file}")
        except Exception as exc:  # pragma: no cover - platform dependent
            if messagebox is not None:
                messagebox.showerror("打开用户版摘要失败", str(exc))
            else:
                self.status_var.set(str(exc))

    def _export_user_summary(self) -> None:
        if self._last_user_summary_file is None:
            self.status_var.set("当前没有可导出的用户版摘要，请先执行 check 或 fix。")
            return
        if filedialog is None:
            self.status_var.set("当前环境不支持文件对话框，无法导出用户版摘要。")
            return
        target_path_raw = filedialog.asksaveasfilename(
            title="导出用户版摘要",
            defaultextension=".md",
            initialfile=self._last_user_summary_file.name,
            filetypes=[("Markdown", "*.md"), ("All Files", "*.*")],
        )
        if not target_path_raw:
            self.status_var.set("已取消导出用户版摘要。")
            return
        target_path = Path(target_path_raw)
        try:
            exported = export_user_summary_file(self._last_user_summary_file, target_path)
            self.status_var.set(f"用户版摘要已导出到：{exported}")
        except Exception as exc:  # pragma: no cover - platform dependent
            if messagebox is not None:
                messagebox.showerror("导出用户版摘要失败", str(exc))
            else:
                self.status_var.set(str(exc))


def main() -> int:
    if _TK_IMPORT_ERROR is not None:
        raise RuntimeError(f"tkinter unavailable: {_TK_IMPORT_ERROR}")
    assert tk is not None
    root = tk.Tk()
    app = ThesisFormatFixerGUI(root)
    app.root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
