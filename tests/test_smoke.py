from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


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
