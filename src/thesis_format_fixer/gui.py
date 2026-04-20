"""Minimal single-file GUI wrapper for thesis-format-fixer."""

from __future__ import annotations

import json
import os
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
    lines = [
        f"mode: {result.mode}",
        f"input_file: {result.input_file}",
        f"output_dir: {result.output_dir}",
        f"status: {'success' if result.success else 'failure'} (exit_code={result.exit_code})",
        "generated_files:",
    ]
    if result.generated_files:
        lines.extend(f"- {path}" for path in result.generated_files)
    else:
        lines.append("- (none)")
    lines.append(f"result_location_hint: {result.output_dir}")

    if summary:
        lines.extend(
            [
                "summary:",
                f"- auto_fix_rule_count: {summary.get('auto_fix_rule_count', 0)}",
                "- "
                + f"detected_not_auto_modified_count: {summary.get('detected_not_auto_modified_count', 0)}",
                f"- manual_review_required_count: {summary.get('manual_review_required_count', 0)}",
                f"- reference_finding_count: {summary.get('reference_finding_count', 0)}",
                f"- reference_blocking_count: {summary.get('reference_blocking_count', 0)}",
                f"- block_low_confidence_count: {summary.get('block_low_confidence_count', 0)}",
            ]
        )

    if result.error_text:
        lines.extend(["error:", result.error_text.strip()])
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


def sys_platform_is_macos() -> bool:
    return os.sys.platform == "darwin"


class ThesisFormatFixerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Thesis Format Fixer - Minimal GUI")
        self.root.geometry("860x600")

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="check")
        self.input_label_var = tk.StringVar(value="Input .docx")
        self.status_var = tk.StringVar(value="Ready")
        self._last_output_dir: Path | None = None

        self._build_layout()

    def _build_layout(self) -> None:
        root = self.root
        root.columnconfigure(1, weight=1)
        root.rowconfigure(5, weight=1)

        tk.Label(root, textvariable=self.input_label_var).grid(row=0, column=0, padx=8, pady=8, sticky="w")
        tk.Entry(root, textvariable=self.input_var).grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        tk.Button(root, text="Browse", command=self._pick_input).grid(row=0, column=2, padx=8, pady=8)

        tk.Label(root, text="Output Dir").grid(row=1, column=0, padx=8, pady=8, sticky="w")
        tk.Entry(root, textvariable=self.output_var).grid(row=1, column=1, padx=8, pady=8, sticky="ew")
        tk.Button(root, text="Browse", command=self._pick_output_dir).grid(row=1, column=2, padx=8, pady=8)

        tk.Label(root, text="Mode").grid(row=2, column=0, padx=8, pady=8, sticky="w")
        mode_frame = tk.Frame(root)
        mode_frame.grid(row=2, column=1, padx=8, pady=8, sticky="w")
        tk.Radiobutton(
            mode_frame,
            text="check",
            variable=self.mode_var,
            value="check",
            command=self._on_mode_changed,
        ).pack(side="left")
        tk.Radiobutton(
            mode_frame,
            text="fix",
            variable=self.mode_var,
            value="fix",
            command=self._on_mode_changed,
        ).pack(side="left")
        tk.Radiobutton(
            mode_frame,
            text="batch-fix",
            variable=self.mode_var,
            value="batch-fix",
            command=self._on_mode_changed,
        ).pack(side="left")

        self.run_button = tk.Button(root, text="Execute", command=self._execute)
        self.run_button.grid(row=3, column=1, padx=8, pady=8, sticky="w")

        self.open_button = tk.Button(root, text="Open Output Dir", command=self._open_output_dir, state="disabled")
        self.open_button.grid(row=3, column=2, padx=8, pady=8, sticky="e")

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
            self.input_label_var.set("Input Dir")
            self.status_var.set("Batch mode: choose an input directory containing .docx files.")
        else:
            self.input_label_var.set("Input .docx")
            self.status_var.set("Single-file mode: choose one .docx file.")

    def _ensure_output_dir_writable(self, output_dir: Path) -> tuple[bool, str | None]:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False, f"Output directory cannot be created: {output_dir}"

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
            return False, f"Output directory is not writable: {output_dir}"
        finally:
            if probe is not None and probe.exists():
                probe.unlink(missing_ok=True)
        return True, None

    def _validate_before_run(self) -> tuple[Path, Path, str] | None:
        input_value = self.input_var.get().strip()
        output_value = self.output_var.get().strip()
        mode = self.mode_var.get().strip().lower()
        if not input_value:
            self.status_var.set("Please select input path.")
            return None
        if not output_value:
            self.status_var.set("Please select output directory.")
            return None
        input_path = Path(input_value)
        output_dir = Path(output_value)
        output_ok, output_error = self._ensure_output_dir_writable(output_dir)
        if not output_ok:
            self.status_var.set(output_error or "Output directory is not writable.")
            return None
        if mode == "batch-fix":
            if not input_path.exists() or not input_path.is_dir():
                self.status_var.set("Input path must be an existing directory for batch-fix")
                return None
            return input_path, output_dir, mode
        if not input_path.exists():
            self.status_var.set("Input file does not exist.")
            return None
        if input_path.is_dir():
            self.status_var.set("Input path must be a .docx file.")
            return None
        if input_path.suffix.lower() != ".docx":
            self.status_var.set("Input file must be .docx")
            return None
        return input_path, output_dir, mode

    def _execute(self) -> None:
        validated = self._validate_before_run()
        if validated is None:
            return

        input_path, output_dir, mode = validated
        self.run_button.config(state="disabled")
        self.status_var.set("Running...")
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
        else:
            single_result = execute_gui_task(
                input_file=input_path,
                output_dir=output_dir,
                mode=mode,
            )
            output_text = format_gui_result(single_result)
            run_success = single_result.success
            run_error = single_result.error_text

        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", output_text)
        self._last_output_dir = output_dir
        self.open_button.config(state="normal" if output_dir.exists() else "disabled")
        if run_success:
            self.status_var.set(f"Completed. Output saved in: {output_dir}")
        else:
            self.status_var.set("Failed. See details below.")

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
