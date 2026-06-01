"""Rule/profile loader utilities used by smoke tests and defaults."""

from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
RULEBOOK_PATH = ROOT_DIR / "rules" / "FORMAT_RULEBOOK_v1.md"
DEFAULT_PROFILE_PATH = ROOT_DIR / "rules" / "profiles" / "generic_university_zh.yaml"
SAMPLE_PROFILE_PATH = ROOT_DIR / "rules" / "profiles" / "sample_institution_zh.yaml"


def load_rulebook_text(path: Path | None = None) -> str:
    target = path or RULEBOOK_PATH
    return target.read_text(encoding="utf-8")


def load_profile_text(path: Path | None = None) -> str:
    """Load institution profile text with lightweight structural validation.

    The project keeps profiles as repository-local YAML text. To avoid introducing
    external parser dependencies in runtime, this function validates minimal
    required anchors in plain text.
    """

    target = path or DEFAULT_PROFILE_PATH
    if not target.exists():
        raise FileNotFoundError(f"profile not found: {target}")

    text = target.read_text(encoding="utf-8")
    required_markers = (
        "profile_id:",
        "display_name:",
        "applicability:",
        "ruleset:",
    )
    if any(marker not in text for marker in required_markers):
        raise ValueError(f"invalid profile format: {target}")
    return text
