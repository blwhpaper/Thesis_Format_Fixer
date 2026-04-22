from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from thesis_format_fixer.app.runner import run_check
from thesis_format_fixer.io.rulebook import resolve_rulebook_path
from thesis_format_fixer.runtime_paths import default_output_dir, resolve_app_icon_path, runtime_root, runtime_rules_dir


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


def test_default_output_dir_is_absolute() -> None:
    output_dir = default_output_dir()
    assert output_dir.is_absolute()
    assert output_dir.name == "ThesisFormatFixerOutput"


def test_rulebook_path_supports_bundled_runtime(monkeypatch, tmp_path: Path) -> None:
    bundled_rules = tmp_path / "rules"
    bundled_rules.mkdir(parents=True, exist_ok=True)
    (bundled_rules / "FORMAT_RULEBOOK_v1.md").write_text("bundled rulebook", encoding="utf-8")

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    assert resolve_rulebook_path() == bundled_rules / "FORMAT_RULEBOOK_v1.md"


def test_runtime_paths_support_macos_app_bundle(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "ThesisFormatFixer.app"
    macos_dir = app_root / "Contents" / "MacOS"
    resources_dir = app_root / "Contents" / "Resources"
    bundled_rules = resources_dir / "rules"
    bundled_icons = resources_dir / "resources" / "icons" / "macos"
    macos_dir.mkdir(parents=True, exist_ok=True)
    bundled_rules.mkdir(parents=True, exist_ok=True)
    bundled_icons.mkdir(parents=True, exist_ok=True)
    executable = macos_dir / "ThesisFormatFixer"
    executable.write_text("", encoding="utf-8")
    (bundled_rules / "FORMAT_RULEBOOK_v1.md").write_text("bundle rulebook", encoding="utf-8")
    (bundled_icons / "ThesisFormatFixer.icns").write_text("icon", encoding="utf-8")

    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable), raising=False)

    assert runtime_root() == resources_dir
    assert runtime_rules_dir() == bundled_rules
    assert resolve_app_icon_path() == bundled_icons / "ThesisFormatFixer.icns"
    assert resolve_rulebook_path() == bundled_rules / "FORMAT_RULEBOOK_v1.md"
