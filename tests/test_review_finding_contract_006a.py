from __future__ import annotations

from dataclasses import dataclass

from thesis_format_fixer.profiles.engine import FormatProfile, compose_profiles
from thesis_format_fixer.review.adapter import WordReviewAdapter
from thesis_format_fixer.review.contracts import (
    StructuredReviewFinding,
    build_review_finding_from_rule,
    to_adapter_finding,
)
from thesis_format_fixer.review.profiles import ReviewRule


@dataclass
class _FakeRun:
    text: str


@dataclass
class _FakeParagraph:
    runs: list[_FakeRun]


@dataclass
class _FakeComment:
    text: str
    author: str
    initials: str


class _FakeDocument:
    def __init__(self, paragraph_run_texts: list[list[str]]) -> None:
        self.paragraphs = [_FakeParagraph([_FakeRun(text) for text in runs]) for runs in paragraph_run_texts]
        self.comments: list[_FakeComment] = []

    def add_comment(self, *, runs, text: str, author: str, initials: str) -> _FakeComment:
        _ = runs
        comment = _FakeComment(text=text, author=author, initials=initials)
        self.comments.append(comment)
        return comment


def _rule() -> ReviewRule:
    return ReviewRule(
        rule_id="RP-ENG-001",
        category="language",
        severity="warning",
        message_template="Clarify tense consistency in this sentence.",
        anchor_strategy="paragraph_run",
        comment_allowed=True,
        auto_rewrite_allowed=False,
    )


def test_valid_rule_maps_to_adapter_finding_and_keeps_metadata() -> None:
    finding = build_review_finding_from_rule(
        _rule(),
        paragraph_index=3,
        run_index=1,
        anchor_text="has been",
    )

    mapped = to_adapter_finding(finding)

    assert finding.category == "language"
    assert finding.severity == "warning"
    assert mapped.status == "mapped"
    assert mapped.adapter_finding is not None
    assert mapped.adapter_finding.rule_id == "RP-ENG-001"
    assert mapped.adapter_finding.paragraph_index == 3
    assert mapped.adapter_finding.run_index == 1
    assert mapped.adapter_finding.anchor_text == "has been"


def test_auto_rewrite_allowed_true_is_rejected() -> None:
    bad = StructuredReviewFinding(
        rule_id="X",
        category="language",
        severity="warning",
        message="m",
        anchor_strategy="paragraph",
        paragraph_index=0,
        auto_rewrite_allowed=True,
    )

    mapped = to_adapter_finding(bad)

    assert mapped.status == "invalid"
    assert "auto_rewrite_allowed" in mapped.reason


def test_comment_allowed_false_is_rejected() -> None:
    bad = StructuredReviewFinding(
        rule_id="X",
        category="language",
        severity="warning",
        message="m",
        anchor_strategy="paragraph",
        paragraph_index=0,
        comment_allowed=False,
    )

    mapped = to_adapter_finding(bad)

    assert mapped.status == "invalid"
    assert "comment_allowed" in mapped.reason


def test_missing_anchor_is_skipped_without_fabrication() -> None:
    finding = build_review_finding_from_rule(_rule())

    mapped = to_adapter_finding(finding)

    assert mapped.status == "skipped"
    assert mapped.adapter_finding is None
    assert "missing:anchor.paragraph_index" == mapped.reason


def test_mapped_finding_is_consumable_by_word_review_adapter() -> None:
    finding = build_review_finding_from_rule(_rule(), paragraph_index=0, run_index=0)
    mapped = to_adapter_finding(finding)
    assert mapped.adapter_finding is not None

    adapter = WordReviewAdapter()
    doc = _FakeDocument([["Alpha"]])
    result = adapter.apply_findings(doc, [mapped.adapter_finding])

    assert result.added == 1
    assert len(doc.comments) == 1
    assert "[TFF-RULE:RP-ENG-001]" in doc.comments[0].text


def test_review_contract_mapping_does_not_affect_format_profile_engine() -> None:
    _ = build_review_finding_from_rule(_rule(), paragraph_index=0)

    format_profile = FormatProfile(
        profile_id="format_base",
        display_name="format",
        base_rulebook="rules/FORMAT_RULEBOOK_v1.md",
        rule_decisions={},
        raw={},
    )
    effective = compose_profiles(format_profile)

    assert effective.profile_id == "format_base"
    assert effective.effective_rule_decisions == {}
