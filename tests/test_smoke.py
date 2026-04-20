from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from thesis_format_fixer.app.runner import run_check


def test_package_import() -> None:
    import thesis_format_fixer  # noqa: F401


def test_cli_help_runs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src")

    result = subprocess.run(
        [sys.executable, "-m", "thesis_format_fixer.cli", "--help"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert "thesis-format-fixer" in result.stdout


def test_run_check_rejects_non_docx_input(tmp_path: Path) -> None:
    txt_file = tmp_path / "demo.txt"
    txt_file.write_text("hello", encoding="utf-8")
    assert run_check(txt_file) == 2
