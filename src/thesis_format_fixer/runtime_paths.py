"""Runtime path helpers for source and bundled executions."""

from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "ThesisFormatFixer"
DEFAULT_OUTPUT_DIRNAME = "ThesisFormatFixerOutput"


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


def default_output_dir() -> Path:
    return Path.home() / DEFAULT_OUTPUT_DIRNAME
