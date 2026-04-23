from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from thesis_format_fixer.app.runner import run_check
from thesis_format_fixer.io.rulebook import resolve_rulebook_path
from thesis_format_fixer.runtime_paths import (
    default_logs_dir,
    default_output_dir,
    default_reports_dir,
    default_temp_dir,
    resolve_app_icon_path,
    resolve_writable_output_dir,
    runtime_root,
    runtime_rules_dir,
    validate_runtime_rules,
)


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


def test_runtime_output_strategy_helpers(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    assert default_reports_dir(output_dir) == output_dir
    assert default_temp_dir(output_dir) == output_dir / "temp"
    assert default_logs_dir(output_dir) == output_dir / "logs"


def test_resolve_writable_output_dir_falls_back_to_default(monkeypatch, tmp_path: Path) -> None:
    preferred = tmp_path / "blocked"
    fallback = tmp_path / "ThesisFormatFixerOutput"

    def _stub_home() -> Path:
        return tmp_path

    original_mkdir = Path.mkdir

    def _stub_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        if self == preferred:
            raise OSError("blocked")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "home", staticmethod(_stub_home))
    monkeypatch.setattr(Path, "mkdir", _stub_mkdir)

    resolved, notice = resolve_writable_output_dir(preferred)

    assert resolved == fallback
    assert notice is not None
    assert "已自动切换到默认目录" in notice


def test_validate_runtime_rules_requires_all_rulebooks(monkeypatch, tmp_path: Path) -> None:
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    (rules_dir / "FORMAT_RULEBOOK_v1.md").write_text("v1", encoding="utf-8")
    (rules_dir / "FORMAT_RULEBOOK_v2.md").write_text("v2", encoding="utf-8")

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    try:
        validate_runtime_rules()
    except FileNotFoundError as exc:
        assert "FORMAT_RULEBOOK_v3.md" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected FileNotFoundError")
