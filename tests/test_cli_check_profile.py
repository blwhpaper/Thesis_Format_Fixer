from __future__ import annotations

import json
from pathlib import Path

from thesis_format_fixer.cli import main


def _create_fake_docx(path: Path, *, text: str = "fake-docx") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def test_cli_check_without_profile_keeps_compatible_behavior(tmp_path: Path) -> None:
    input_docx = tmp_path / "input.docx"
    report_json = tmp_path / "check.report.json"
    _create_fake_docx(input_docx)

    code = main(["check", str(input_docx), "--report-json", str(report_json)])
    assert code == 0

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert "profile_drift" in payload["sections"]


def test_cli_check_with_profile_outputs_profile_drift(tmp_path: Path) -> None:
    input_docx = tmp_path / "input.docx"
    report_json = tmp_path / "check.report.json"
    profile_yaml = tmp_path / "profile.yaml"
    _create_fake_docx(input_docx)
    profile_yaml.write_text(
        """
profile_id: cli_profile
display_name: CLI Profile
ruleset:
  base_rulebook: rules/FORMAT_RULEBOOK_v1.md
runtime:
  rule_decisions:
    FR-4.5-03: AUTO_CHECK
""".strip(),
        encoding="utf-8",
    )

    code = main(
        ["check", str(input_docx), "--report-json", str(report_json), "--profile", str(profile_yaml)]
    )
    assert code == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["sections"]["profile_drift"]["profile_id"] == "cli_profile"


def test_cli_check_with_missing_profile_reports_visible_finding(tmp_path: Path) -> None:
    input_docx = tmp_path / "input.docx"
    report_json = tmp_path / "check.report.json"
    missing = tmp_path / "missing.profile.yaml"
    _create_fake_docx(input_docx)

    code = main(["check", str(input_docx), "--report-json", str(report_json), "--profile", str(missing)])
    assert code == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    section = payload["sections"]["profile_drift"]
    assert section["enabled"] is False
    assert section["reason"] == "profile_not_found"
    assert any(item.startswith("profile_missing:") for item in section["drift_findings"])
