from pathlib import Path

from thesis_format_fixer.profiles.engine import (
    compose_profiles,
    detect_rulebook_registry_drift,
    load_profile,
    validate_profile_keys,
)


def _write_profile(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "profile.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_compose_profiles_priority_and_conflict_report(tmp_path: Path) -> None:
    base = load_profile(
        _write_profile(
            tmp_path,
            """
profile_id: generic
display_name: Generic
ruleset:
  base_rulebook: rules/FORMAT_RULEBOOK_v1.md
runtime:
  rule_decisions:
    FR-4.5-03: AUTO_CHECK
""".strip(),
        )
    )
    institution = load_profile(
        _write_profile(
            tmp_path,
            """
profile_id: institution
display_name: Institution
ruleset:
  base_rulebook: rules/FORMAT_RULEBOOK_v1.md
runtime:
  rule_decisions:
    FR-4.5-03: REPORT_ONLY
""".strip(),
        )
    )
    effective = compose_profiles(base, institution, overrides={"FR-4.5-03": "AUTO_CHECK"})
    assert effective.effective_rule_decisions["FR-4.5-03"].name == "AUTO_CHECK"
    assert any(item.startswith("FR-4.5-03:") for item in effective.conflicts)


def test_validate_profile_keys_reports_unknown_key(tmp_path: Path) -> None:
    profile = load_profile(
        _write_profile(
            tmp_path,
            """
profile_id: generic
display_name: Generic
ruleset:
  base_rulebook: rules/FORMAT_RULEBOOK_v1.md
runtime:
  rule_decisions:
    FR-UNKNOWN-001: AUTO_CHECK
""".strip(),
        )
    )
    unknown = validate_profile_keys(profile)
    assert unknown == ("FR-UNKNOWN-001",)


def test_compose_profiles_respects_a_b_c_boundary(tmp_path: Path) -> None:
    base = load_profile(
        _write_profile(
            tmp_path,
            """
profile_id: generic
display_name: Generic
ruleset:
  base_rulebook: rules/FORMAT_RULEBOOK_v1.md
runtime:
  rule_decisions:
    FR-4.10-05: OUT_OF_V1
""".strip(),
        )
    )
    effective = compose_profiles(base, overrides={"FR-4.10-05": "AUTO_FIX"})
    assert "FR-4.10-05" in effective.boundary_violations
    assert effective.effective_rule_decisions["FR-4.10-05"].name == "OUT_OF_V1"


def test_compose_profiles_reports_invalid_override_decision(tmp_path: Path) -> None:
    base = load_profile(
        _write_profile(
            tmp_path,
            """
profile_id: generic
display_name: Generic
ruleset:
  base_rulebook: rules/FORMAT_RULEBOOK_v1.md
runtime:
  rule_decisions: {}
""".strip(),
        )
    )
    effective = compose_profiles(base, overrides={"FR-4.5-03": "NOT_A_DECISION"})
    assert effective.invalid_decisions == {"FR-4.5-03": "NOT_A_DECISION"}


def test_detect_rulebook_registry_drift_reports_rulebook_mismatch(tmp_path: Path) -> None:
    profile = load_profile(
        _write_profile(
            tmp_path,
            """
profile_id: generic
display_name: Generic
ruleset:
  base_rulebook: rules/FORMAT_RULEBOOK_v3.md
runtime:
  rule_decisions: {}
""".strip(),
        )
    )
    issues = detect_rulebook_registry_drift(profile)
    assert any(item.startswith("base_rulebook_mismatch:") for item in issues)
