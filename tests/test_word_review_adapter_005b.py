from __future__ import annotations

from dataclasses import dataclass

from thesis_format_fixer.review.adapter import (
    TFF_AUTHOR,
    TFF_INITIALS,
    ReviewFinding,
    WordReviewAdapter,
)


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
    def __init__(self, paragraph_run_texts: list[list[str]], *, supports_comments: bool = True) -> None:
        self.paragraphs = [_FakeParagraph([_FakeRun(text) for text in runs]) for runs in paragraph_run_texts]
        self.comments: list[_FakeComment] = []
        if supports_comments:
            self.add_comment = self._add_comment

    def _add_comment(self, *, runs, text: str, author: str, initials: str) -> _FakeComment:
        comment = _FakeComment(text=text, author=author, initials=initials)
        self.comments.append(comment)
        return comment


def _body_text(doc: _FakeDocument) -> list[str]:
    return ["".join(run.text for run in paragraph.runs) for paragraph in doc.paragraphs]


def test_add_single_comment_on_paragraph_run() -> None:
    doc = _FakeDocument([["Intro", " body"]])
    before = _body_text(doc)
    adapter = WordReviewAdapter()

    result = adapter.apply_findings(
        doc,
        [ReviewFinding(rule_id="FR-4.9-02", message="Use halfwidth punctuation.", paragraph_index=0, run_index=1)],
    )

    assert result.total == 1
    assert result.added == 1
    assert result.skipped == 0
    assert result.duplicate == 0
    assert result.unsupported == 0
    assert len(doc.comments) == 1
    assert doc.comments[0].author == TFF_AUTHOR
    assert doc.comments[0].initials == TFF_INITIALS
    assert doc.comments[0].text == "[TFF-RULE:FR-4.9-02] Use halfwidth punctuation."
    assert _body_text(doc) == before


def test_add_multiple_findings() -> None:
    doc = _FakeDocument([["P0R0"], ["P1R0", "P1R1"]])
    adapter = WordReviewAdapter()

    result = adapter.apply_findings(
        doc,
        [
            ReviewFinding(rule_id="A", message="m1", paragraph_index=0, run_index=0),
            ReviewFinding(rule_id="B", message="m2", paragraph_index=1, run_index=1),
        ],
    )

    assert result.added == 2
    assert len(doc.comments) == 2


def test_reapply_same_finding_is_idempotent_duplicate() -> None:
    doc = _FakeDocument([["R0"]])
    adapter = WordReviewAdapter()
    finding = ReviewFinding(rule_id="FR-4.8-01", message="Heading format mismatch.", paragraph_index=0, run_index=0)

    first = adapter.apply_findings(doc, [finding])
    second = adapter.apply_findings(doc, [finding])

    assert first.added == 1
    assert second.added == 0
    assert second.duplicate == 1
    assert len(doc.comments) == 1


def test_missing_anchor_skipped_and_body_unchanged() -> None:
    doc = _FakeDocument([["A"], ["B"]])
    before = _body_text(doc)
    adapter = WordReviewAdapter()

    result = adapter.apply_findings(
        doc,
        [ReviewFinding(rule_id="X", message="m", paragraph_index=10, run_index=0)],
    )

    assert result.added == 0
    assert result.skipped == 1
    assert len(doc.comments) == 0
    assert _body_text(doc) == before


def test_paragraph_level_fallback_when_run_index_missing() -> None:
    doc = _FakeDocument([["A", "B"]])
    adapter = WordReviewAdapter()

    result = adapter.apply_findings(
        doc,
        [ReviewFinding(rule_id="F", message="whole paragraph", paragraph_index=0, run_index=None)],
    )

    assert result.added == 1
    assert doc.comments[0].text == "[TFF-RULE:F] whole paragraph"


def test_unsupported_when_document_has_no_add_comment() -> None:
    doc = _FakeDocument([["A"]], supports_comments=False)
    adapter = WordReviewAdapter()

    result = adapter.apply_findings(
        doc,
        [ReviewFinding(rule_id="X", message="m", paragraph_index=0, run_index=0)],
    )

    assert result.unsupported == 1
    assert result.added == 0
