from pathlib import Path

import pytest

from thesis_format_fixer.io.rulebook import (
    DEFAULT_PROFILE_PATH,
    RULEBOOK_PATH,
    SAMPLE_PROFILE_PATH,
    load_profile_text,
    load_rulebook_text,
)


def test_rulebook_path_exists() -> None:
    assert RULEBOOK_PATH.exists()


def test_load_rulebook_text_smoke() -> None:
    text = load_rulebook_text()
    assert "FORMAT_RULEBOOK_v1" in text


def test_default_profile_exists_and_loads() -> None:
    assert DEFAULT_PROFILE_PATH.exists()
    text = load_profile_text()
    assert "profile_id: generic_university_zh" in text
    assert "base_rulebook: rules/FORMAT_RULEBOOK_v1.md" in text


def test_sample_profile_loads() -> None:
    text = load_profile_text(SAMPLE_PROFILE_PATH)
    assert "profile_id: sample_institution_zh" in text
    assert "base_rulebook: rules/FORMAT_RULEBOOK_v1.md" in text


def test_missing_profile_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_profile_text(tmp_path / "missing.yaml")


def test_invalid_profile_raises_value_error(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("profile_id: only_id\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_profile_text(invalid)
