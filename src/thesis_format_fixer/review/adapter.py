"""Word review adapter (TASK-THESIS-OSS-005B, comment-only V1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

TFF_AUTHOR = "ThesisFormatFixer"
TFF_INITIALS = "TFF"


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    """Minimal stable finding contract for Word comment anchoring."""

    rule_id: str
    message: str
    paragraph_index: int
    run_index: int | None = None
    anchor_text: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewApplyResult:
    total: int = 0
    added: int = 0
    skipped: int = 0
    duplicate: int = 0
    unsupported: int = 0
    details: tuple[dict[str, Any], ...] = field(default_factory=tuple)


class WordReviewAdapter:
    """Adds review findings as Word comments through python-docx high-level API only."""

    def __init__(self, *, author: str = TFF_AUTHOR, initials: str = TFF_INITIALS) -> None:
        self._author = author
        self._initials = initials

    def apply_findings(self, document: Any, findings: Iterable[ReviewFinding]) -> ReviewApplyResult:
        finding_list = list(findings)
        added = 0
        skipped = 0
        duplicate = 0
        unsupported = 0
        details: list[dict[str, Any]] = []

        for item in finding_list:
            status, detail = self.add_comment_for_finding(document, item)
            details.append(detail)
            if status == "added":
                added += 1
            elif status == "skipped":
                skipped += 1
            elif status == "duplicate":
                duplicate += 1
            elif status == "unsupported":
                unsupported += 1

        return ReviewApplyResult(
            total=len(finding_list),
            added=added,
            skipped=skipped,
            duplicate=duplicate,
            unsupported=unsupported,
            details=tuple(details),
        )

    def add_comment_for_finding(self, document: Any, finding: ReviewFinding) -> tuple[str, dict[str, Any]]:
        if not hasattr(document, "add_comment") or not hasattr(document, "paragraphs"):
            return "unsupported", self._detail(finding, "unsupported", "document_add_comment_unavailable")

        paragraph = self._resolve_paragraph(document, finding.paragraph_index)
        if paragraph is None:
            return "skipped", self._detail(finding, "skipped", "paragraph_not_found")

        runs = self._resolve_runs(paragraph, finding)
        if not runs:
            return "skipped", self._detail(finding, "skipped", "anchor_run_not_found")

        comment_text = self._format_comment_text(finding)
        if self._is_duplicate(document, comment_text):
            return "duplicate", self._detail(finding, "duplicate", "same_tff_comment_exists")

        document.add_comment(
            runs=runs,
            text=comment_text,
            author=self._author,
            initials=self._initials,
        )
        return "added", self._detail(finding, "added", "ok")

    def _resolve_paragraph(self, document: Any, paragraph_index: int) -> Any | None:
        if paragraph_index < 0:
            return None
        paragraphs = getattr(document, "paragraphs", [])
        if paragraph_index >= len(paragraphs):
            return None
        return paragraphs[paragraph_index]

    def _resolve_runs(self, paragraph: Any, finding: ReviewFinding) -> list[Any]:
        runs = list(getattr(paragraph, "runs", []))
        if not runs:
            return []
        if finding.run_index is None:
            return runs
        if finding.run_index < 0 or finding.run_index >= len(runs):
            return []
        return [runs[finding.run_index]]

    def _format_comment_text(self, finding: ReviewFinding) -> str:
        return f"[TFF-RULE:{finding.rule_id}] {finding.message}"

    def _is_duplicate(self, document: Any, comment_text: str) -> bool:
        comments = getattr(document, "comments", None)
        if comments is None:
            return False
        for comment in comments:
            if getattr(comment, "text", "") != comment_text:
                continue
            if getattr(comment, "author", "") != self._author:
                continue
            if getattr(comment, "initials", "") != self._initials:
                continue
            return True
        return False

    def _detail(self, finding: ReviewFinding, status: str, reason: str) -> dict[str, Any]:
        return {
            "status": status,
            "reason": reason,
            "rule_id": finding.rule_id,
            "paragraph_index": finding.paragraph_index,
            "run_index": finding.run_index,
        }
