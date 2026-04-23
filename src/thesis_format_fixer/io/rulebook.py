"""Rulebook loader used by smoke tests in TASK-001."""

from __future__ import annotations

from pathlib import Path

from thesis_format_fixer.runtime_paths import runtime_rules_dir


def resolve_rulebook_path(path: Path | None = None) -> Path:
    if path is not None:
        return path
    rules_dir = runtime_rules_dir()
    candidates = (
        rules_dir / "FORMAT_RULEBOOK_v1.md",
        rules_dir / "sources" / "FORMAT_RULEBOOK_v1.md",
    )
    for target in candidates:
        if target.exists():
            return target
    raise FileNotFoundError(
        "Rulebook not found at expected runtime paths: "
        + ", ".join(str(item) for item in candidates)
        + f" (rules_dir={rules_dir})"
    )


RULEBOOK_PATH = resolve_rulebook_path()


def load_rulebook_text(path: Path | None = None) -> str:
    target = resolve_rulebook_path(path)
    return target.read_text(encoding="utf-8")
