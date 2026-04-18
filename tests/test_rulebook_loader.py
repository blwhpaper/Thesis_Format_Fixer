from thesis_format_fixer.io.rulebook import RULEBOOK_PATH, load_rulebook_text


def test_rulebook_path_exists() -> None:
    assert RULEBOOK_PATH.exists()


def test_load_rulebook_text_smoke() -> None:
    text = load_rulebook_text()
    assert "FORMAT_RULEBOOK_v1" in text
