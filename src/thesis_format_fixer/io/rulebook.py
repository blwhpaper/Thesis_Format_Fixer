"""Rulebook loader used by smoke tests in TASK-001."""

from __future__ import annotations

from pathlib import Path

from thesis_format_fixer.runtime_paths import runtime_rules_dir


def resolve_rulebook_path(path: Path | None = None) -> Path:
    if path is not None:
        return path
    rules_dir = runtime_rules_dir()
    target = rules_dir / "FORMAT_RULEBOOK_v1.md"
    if target.exists():
        return target
    raise FileNotFoundError(
        f"Rulebook not found at expected runtime path: {target} (rules_dir={rules_dir})"
    )


RULEBOOK_PATH = resolve_rulebook_path()


def load_rulebook_text(path: Path | None = None) -> str:
    target = resolve_rulebook_path(path)
    return target.read_text(encoding="utf-8")
