from __future__ import annotations

from pathlib import Path

import pytest

from thesis_format_fixer.profiles.engine import FormatProfile, compose_profiles
from thesis_format_fixer.review.profiles import (
    ReviewProfileValidationError,
    load_review_profile,
)


def test_load_three_review_profiles() -> None:
    root = Path("rules/review_profiles")
    profiles = [
        load_review_profile(root / "english_academic.yaml"),
        load_review_profile(root / "humanities_thesis.yaml"),
        load_review_profile(root / "science_engineering_thesis.yaml"),
    ]

    assert [item.profile_id for item in profiles] == [
        "english_academic",
        "humanities_thesis",
        "science_engineering_thesis",
    ]


def test_review_profile_missing_required_fields_raises(tmp_path: Path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        """
profile_id: bad
schema_version: 1
display_name: Broken
language: en
scope: test
review_rules:
  - rule_id: X
    category: language
    severity: warning
    anchor_strategy: paragraph
    comment_allowed: true
    auto_rewrite_allowed: false
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ReviewProfileValidationError, match="message_template"):
        load_review_profile(broken)


def test_review_profile_auto_rewrite_must_be_false(tmp_path: Path) -> None:
    broken = tmp_path / "broken-rewrite.yaml"
    broken.write_text(
        """
profile_id: bad_rewrite
schema_version: 1
display_name: Broken Rewrite
language: en
scope: test
review_rules:
  - rule_id: X
    category: language
    severity: warning
    message_template: m
    anchor_strategy: paragraph
    comment_allowed: true
    auto_rewrite_allowed: true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ReviewProfileValidationError, match="auto_rewrite_allowed"):
        load_review_profile(broken)


def test_review_profile_category_and_severity_validation(tmp_path: Path) -> None:
    broken = tmp_path / "broken-category.yaml"
    broken.write_text(
        """
profile_id: bad_category
schema_version: 1
display_name: Broken Category
language: en
scope: test
review_rules:
  - rule_id: X
    category: unsupported
    severity: bad
    message_template: m
    anchor_strategy: paragraph
    comment_allowed: true
    auto_rewrite_allowed: false
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ReviewProfileValidationError, match="category"):
        load_review_profile(broken)


def test_review_profile_comment_allowed_must_be_explicit(tmp_path: Path) -> None:
    broken = tmp_path / "broken-comment-allowed.yaml"
    broken.write_text(
        """
profile_id: bad_comment_allowed
schema_version: 1
display_name: Broken Comment Allowed
language: en
scope: test
review_rules:
  - rule_id: X
    category: language
    severity: warning
    message_template: m
    anchor_strategy: paragraph
    auto_rewrite_allowed: false
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ReviewProfileValidationError, match="comment_allowed"):
        load_review_profile(broken)


def test_review_profile_layer_does_not_affect_format_profile_engine() -> None:
    review_profile = load_review_profile(Path("rules/review_profiles/english_academic.yaml"))

    format_profile = FormatProfile(
        profile_id="format_base",
        display_name="format",
        base_rulebook="rules/FORMAT_RULEBOOK_v1.md",
        rule_decisions={},
        raw={},
    )
    effective = compose_profiles(format_profile)

    assert review_profile.profile_id == "english_academic"
    assert effective.profile_id == "format_base"
    assert effective.effective_rule_decisions == {}
