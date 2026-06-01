from __future__ import annotations

import pytest

from thesis_format_fixer.review.adapter import (
    TFF_AUTHOR,
    TFF_INITIALS,
    ReviewFinding,
    WordReviewAdapter,
)


def _load_docx_api():
    docx = pytest.importorskip("docx", reason="python-docx is required for real DOCX integration tests")
    Document = docx.Document
    probe = Document()
    if not hasattr(probe, "add_comment"):
        pytest.skip("python-docx version does not support Document.add_comment comments API")
    return Document


def _body_texts(document) -> list[str]:
    return [paragraph.text for paragraph in document.paragraphs]


def test_adapter_writes_comment_and_roundtrips_real_docx(tmp_path) -> None:
    Document = _load_docx_api()
    input_path = tmp_path / "review-input.docx"
    output_path = tmp_path / "review-output.docx"

    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("Alpha ")
    paragraph.add_run("Beta")
    before_texts = _body_texts(document)
    document.save(input_path)

    loaded = Document(input_path)
    adapter = WordReviewAdapter()
    finding = ReviewFinding(
        rule_id="FR-4.9-02",
        message="Use halfwidth punctuation.",
        paragraph_index=0,
        run_index=1,
    )
    result = adapter.apply_findings(loaded, [finding])

    assert result.total == 1
    assert result.added == 1
    assert result.duplicate == 0
    assert result.skipped == 0
    assert result.unsupported == 0
    assert _body_texts(loaded) == before_texts

    loaded.save(output_path)
    reopened = Document(output_path)

    assert _body_texts(reopened) == before_texts
    comments = list(reopened.comments)
    assert len(comments) == 1
    assert "[TFF-RULE:FR-4.9-02]" in comments[0].text
    assert comments[0].author == TFF_AUTHOR
    assert comments[0].initials == TFF_INITIALS


def test_adapter_idempotent_after_save_reopen_real_docx(tmp_path) -> None:
    Document = _load_docx_api()
    path = tmp_path / "idempotent.docx"

    document = Document()
    paragraph = document.add_paragraph("Heading sample")
    assert paragraph.runs
    document.save(path)

    adapter = WordReviewAdapter()
    finding = ReviewFinding(
        rule_id="FR-4.8-01",
        message="Heading format mismatch.",
        paragraph_index=0,
        run_index=0,
    )

    first = Document(path)
    first_result = adapter.apply_findings(first, [finding])
    first.save(path)
    assert first_result.added == 1

    second = Document(path)
    second_result = adapter.apply_findings(second, [finding])
    second.save(path)
    assert second_result.added == 0
    assert second_result.duplicate == 1

    reopened = Document(path)
    assert len(list(reopened.comments)) == 1
    assert reopened.paragraphs[0].text == "Heading sample"
