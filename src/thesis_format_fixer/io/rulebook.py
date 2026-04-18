"""Rulebook loader used by smoke tests in TASK-001."""

from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
RULEBOOK_PATH = ROOT_DIR / "rules" / "FORMAT_RULEBOOK_v1.md"


def load_rulebook_text(path: Path | None = None) -> str:
    target = path or RULEBOOK_PATH
    return target.read_text(encoding="utf-8")
