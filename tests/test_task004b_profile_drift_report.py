from __future__ import annotations

import json
from pathlib import Path

from thesis_format_fixer.app.runner import run_check, run_fix
from thesis_format_fixer.profiles import engine as profile_engine


def _create_fake_docx(path: Path, *, text: str = "fake-docx") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def test_check_report_includes_default_profile_drift_section(tmp_path: Path) -> None:
    input_docx = tmp_path / "input.docx"
    report_json = tmp_path / "check.report.json"
    _create_fake_docx(input_docx)

    assert run_check(input_docx, report_json_out=report_json) == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))

    assert "profile_drift" in payload["sections"]
    section = payload["sections"]["profile_drift"]
    assert section["enabled"] is True
    assert section["profile_id"] == "generic_university_zh"
    assert "profile_drift_finding_count" in payload["summary"]


def test_check_report_exposes_profile_drift_findings(tmp_path: Path, monkeypatch) -> None:
    input_docx = tmp_path / "input.docx"
    report_json = tmp_path / "check.report.json"
    profile_yaml = tmp_path / "drift.profile.yaml"
    _create_fake_docx(input_docx)
    profile_yaml.write_text(
        """
profile_id: drift_profile
display_name: Drift Profile
ruleset:
  base_rulebook: rules/FORMAT_RULEBOOK_v9.md
runtime:
  required_rule_keys:
    - FR-4.5-03
    - FR-4.6-03
  rule_decisions:
    FR-4.10-05: AUTO_FIX
    FR-UNKNOWN-001: AUTO_CHECK
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(profile_engine, "SOURCE_OF_TRUTH", "docs/NOT_EXISTING_SOURCE.md")

    assert run_check(input_docx, report_json_out=report_json, profile_path=profile_yaml) == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    findings = set(payload["sections"]["profile_drift"]["drift_findings"])

    assert "profile_rulebook_missing:rules/FORMAT_RULEBOOK_v9.md" in findings
    assert "unknown_rule_key:FR-UNKNOWN-001" in findings
    assert "missing_rule_key:FR-4.5-03" in findings
    assert "missing_rule_key:FR-4.6-03" in findings
    assert "boundary_violation:FR-4.10-05" in findings
    assert "registry_source_missing:docs/NOT_EXISTING_SOURCE.md" in findings


def test_fix_report_does_not_add_profile_drift_section(tmp_path: Path) -> None:
    input_docx = tmp_path / "input.docx"
    output_docx = tmp_path / "output.fixed.docx"
    _create_fake_docx(input_docx)

    assert run_fix(input_docx, output_docx) == 0
    payload = json.loads(output_docx.with_suffix(".report.json").read_text(encoding="utf-8"))

    assert "profile_drift" not in payload["sections"]
