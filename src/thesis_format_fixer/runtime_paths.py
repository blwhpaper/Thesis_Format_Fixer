"""Runtime path helpers for source and bundled executions."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "ThesisFormatFixer"
APP_DISPLAY_NAME = "Thesis Format Fixer"
DEFAULT_OUTPUT_DIRNAME = "ThesisFormatFixerOutput"
REQUIRED_RULEBOOK_BASENAMES = (
    "FORMAT_RULEBOOK_v1.md",
    "FORMAT_RULEBOOK_v2.md",
    "FORMAT_RULEBOOK_v3.md",
)


def _macos_bundle_contents_dir(executable_path: Path) -> Path | None:
    for parent in executable_path.parents:
        if parent.name == "Contents" and parent.parent.suffix == ".app":
            return parent
    return None


def runtime_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root).resolve()
    if getattr(sys, "frozen", False):
        executable_path = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            bundle_contents = _macos_bundle_contents_dir(executable_path)
            if bundle_contents is not None:
                return (bundle_contents / "Resources").resolve()
        return executable_path.parent
    return Path(__file__).resolve().parents[2]


def runtime_rules_dir() -> Path:
    return runtime_root() / "rules"


def runtime_resources_dir() -> Path:
    resources_dir = runtime_root() / "resources"
    if resources_dir.exists():
        return resources_dir
    return runtime_root()


def resolve_app_icon_path() -> Path | None:
    candidates = (
        runtime_resources_dir() / "icons" / "macos" / "ThesisFormatFixer.icns",
        runtime_resources_dir() / "icons" / "macos" / "ThesisFormatFixer.png",
        runtime_root() / "ThesisFormatFixer.icns",
        runtime_root() / "icon-windowed.icns",
    )
    for path in candidates:
        if path.exists():
            return path
    return None


def default_reports_dir(output_dir: Path | None = None) -> Path:
    return output_dir or default_output_dir()


def default_temp_dir(output_dir: Path | None = None) -> Path:
    return (output_dir or default_output_dir()) / "temp"


def default_logs_dir(output_dir: Path | None = None) -> Path:
    return (output_dir or default_output_dir()) / "logs"


def default_output_dir() -> Path:
    return Path.home() / DEFAULT_OUTPUT_DIRNAME


def ensure_directory_writable(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except FileExistsError as exc:
        raise PermissionError(f"输出目录不可创建: {path}") from exc
    except OSError as exc:
        raise PermissionError(f"输出目录不可创建: {path}") from exc

    probe_name = f".write_probe_{os.getpid()}.tmp"
    probe_path = path / probe_name
    try:
        probe_path.write_text("ok", encoding="utf-8")
    except OSError as exc:
        raise PermissionError(f"输出目录不可写: {path}") from exc
    finally:
        probe_path.unlink(missing_ok=True)
    return path


def resolve_writable_output_dir(preferred: Path) -> tuple[Path, str | None]:
    try:
        return ensure_directory_writable(preferred), None
    except PermissionError as preferred_exc:
        fallback = default_output_dir()
        if fallback == preferred:
            raise preferred_exc
        try:
            ensure_directory_writable(fallback)
        except PermissionError:
            raise preferred_exc
        return fallback, f"输出目录不可写，已自动切换到默认目录：{fallback}"


def validate_runtime_rules() -> Path:
    rules_dir = runtime_rules_dir()
    if not rules_dir.exists():
        raise FileNotFoundError(
            "程序运行所需的 rules 目录不存在，请重新解压完整程序包或回到项目源码根目录运行。"
        )

    missing = [
        name
        for name in REQUIRED_RULEBOOK_BASENAMES
        if not (rules_dir / name).exists()
    ]
    if missing:
        raise FileNotFoundError(
            "程序运行所需规则文件缺失："
            + ", ".join(missing)
            + f"；当前 rules 目录：{rules_dir}"
        )
    return rules_dir
