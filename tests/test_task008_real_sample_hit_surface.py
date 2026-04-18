from __future__ import annotations

import json
import shutil
from pathlib import Path

from thesis_format_fixer.app.runner import run_check, run_fix


def test_task008_real_sample_has_non_footnote_a_class_hits(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = repo_root / "runs" / "test_run_001" / "test_thesis_fixed.docx"
    assert source.exists(), "real sample docx is required for TASK-008 calibration"

    input_docx = tmp_path / "sample.docx"
    shutil.copy2(source, input_docx)

    check_json = tmp_path / "check.report.json"
    check_md = tmp_path / "check.report.md"
    assert run_check(input_docx, report_json_out=check_json, report_md_out=check_md) == 0

    output_docx = tmp_path / "sample.fixed.docx"
    fix_json = tmp_path / "sample.fixed.report.json"
    fix_md = tmp_path / "sample.fixed.report.md"
    assert run_fix(input_docx, output_docx, report_json_out=fix_json, report_md_out=fix_md) == 0

    payload = json.loads(fix_json.read_text(encoding="utf-8"))
    a_surface = payload["sections"]["a_class_hit_surface"]

    hit_ids = {item["rule_id"] for item in a_surface["hit"]}
    non_footnote_hits = hit_ids - {"FR-4.10-02", "FR-4.10-03", "FR-4.10-04"}

    assert len(non_footnote_hits) >= 3
    assert any(
        rule_id in hit_ids
        for rule_id in {
            "FR-4.2-01",
            "FR-4.2-03",
            "FR-4.4-01",
            "FR-4.4-03",
            "FR-4.6-01",
            "FR-4.7-01",
            "FR-4.8-03",
            "FR-4.9-01",
            "FR-4.11-01",
            "FR-4.11-02",
            "FR-4.12-01",
            "FR-4.12-02",
            "FR-4.13-02",
            "FR-4.14-01",
            "FR-4.14-02",
        }
    )
