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


@dataclass(frozen=True, slots=True)
class _AnchorRange:
    paragraph_index: int
    start_run_index: int
    end_run_index: int


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

        runs, reason = self._resolve_runs(paragraph, finding)
        if not runs:
            return "skipped", self._detail(finding, "skipped", reason)

        comment_text = self._format_comment_text(finding)
        anchor_range = self._anchor_range_for_finding(paragraph, finding, runs)
        if anchor_range is None:
            return "skipped", self._detail(finding, "skipped", "anchor_range_unresolved")
        if self._is_duplicate(document, comment_text, anchor_range):
            return "duplicate", self._detail(finding, "duplicate", "same_tff_comment_exists_at_anchor")

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

    def _resolve_runs(self, paragraph: Any, finding: ReviewFinding) -> tuple[list[Any], str]:
        runs = self._content_runs(paragraph)
        if not runs:
            return [], "anchor_run_not_found"
        if finding.run_index is None:
            if finding.anchor_text and finding.anchor_text not in "".join(getattr(run, "text", "") for run in runs):
                return [], "anchor_text_not_found_in_paragraph"
            return runs, "ok"
        if finding.run_index < 0 or finding.run_index >= len(runs):
            return [], "anchor_run_not_found"
        target_run = runs[finding.run_index]
        if finding.anchor_text and finding.anchor_text not in getattr(target_run, "text", ""):
            return [], "anchor_text_not_found_in_run"
        return [target_run], "ok"

    def _format_comment_text(self, finding: ReviewFinding) -> str:
        return f"[TFF-RULE:{finding.rule_id}] {finding.message}"

    def _is_duplicate(self, document: Any, comment_text: str, anchor_range: _AnchorRange) -> bool:
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
            existing_anchor = self._anchor_range_for_comment(document, comment)
            if existing_anchor != anchor_range:
                continue
            return True
        return False

    def _content_runs(self, paragraph: Any) -> list[Any]:
        return [run for run in getattr(paragraph, "runs", []) if not self._is_comment_reference_run(run)]

    def _anchor_range_for_finding(
        self,
        paragraph: Any,
        finding: ReviewFinding,
        runs: list[Any],
    ) -> _AnchorRange | None:
        paragraph_runs = self._content_runs(paragraph)
        if not paragraph_runs:
            return None
        run_positions = {id(getattr(run, "_r", run)): index for index, run in enumerate(paragraph_runs)}
        positions: list[int] = []
        for run in runs:
            position = run_positions.get(id(getattr(run, "_r", run)))
            if position is None:
                return None
            positions.append(position)
        return _AnchorRange(
            paragraph_index=finding.paragraph_index,
            start_run_index=min(positions),
            end_run_index=max(positions),
        )

    def _anchor_range_for_comment(self, document: Any, comment: Any) -> _AnchorRange | None:
        direct = self._anchor_range_from_direct_attrs(comment)
        if direct is not None:
            return direct
        comment_id = getattr(comment, "comment_id", None)
        if comment_id is None:
            return None
        return self._scan_comment_anchor_ranges(document).get(int(comment_id))

    def _anchor_range_from_direct_attrs(self, comment: Any) -> _AnchorRange | None:
        paragraph_index = getattr(comment, "paragraph_index", None)
        start_run_index = getattr(comment, "start_run_index", None)
        end_run_index = getattr(comment, "end_run_index", None)
        if not all(isinstance(value, int) for value in (paragraph_index, start_run_index, end_run_index)):
            return None
        return _AnchorRange(
            paragraph_index=paragraph_index,
            start_run_index=start_run_index,
            end_run_index=end_run_index,
        )

    def _scan_comment_anchor_ranges(self, document: Any) -> dict[int, _AnchorRange]:
        anchor_ranges: dict[int, _AnchorRange] = {}
        for paragraph_index, paragraph in enumerate(getattr(document, "paragraphs", [])):
            paragraph_ranges = self._scan_paragraph_comment_anchor_ranges(paragraph, paragraph_index)
            anchor_ranges.update(paragraph_ranges)
        return anchor_ranges

    def _scan_paragraph_comment_anchor_ranges(self, paragraph: Any, paragraph_index: int) -> dict[int, _AnchorRange]:
        paragraph_element = getattr(paragraph, "_p", None)
        if paragraph_element is None:
            return {}

        active_starts: dict[int, int] = {}
        anchor_ranges: dict[int, _AnchorRange] = {}
        content_run_index = -1
        for child in paragraph_element.iterchildren():
            local_name = self._local_name(child)
            if local_name == "commentRangeStart":
                comment_id = self._comment_id_from_element(child)
                if comment_id is not None:
                    active_starts[comment_id] = content_run_index + 1
                continue
            if local_name == "r":
                if not self._is_comment_reference_element(child):
                    content_run_index += 1
                continue
            if local_name == "commentRangeEnd":
                comment_id = self._comment_id_from_element(child)
                start_run_index = active_starts.pop(comment_id, None) if comment_id is not None else None
                if comment_id is None or start_run_index is None or content_run_index < start_run_index:
                    continue
                anchor_ranges[comment_id] = _AnchorRange(
                    paragraph_index=paragraph_index,
                    start_run_index=start_run_index,
                    end_run_index=content_run_index,
                )
        return anchor_ranges

    def _is_comment_reference_run(self, run: Any) -> bool:
        run_element = getattr(run, "_r", None)
        if run_element is None:
            return False
        return self._is_comment_reference_element(run_element)

    def _is_comment_reference_element(self, element: Any) -> bool:
        return any(self._local_name(child) == "commentReference" for child in element.iterchildren())

    def _comment_id_from_element(self, element: Any) -> int | None:
        value = element.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _local_name(self, element: Any) -> str:
        tag = getattr(element, "tag", "")
        if "}" in tag:
            return tag.rsplit("}", 1)[1]
        return str(tag)

    def _detail(self, finding: ReviewFinding, status: str, reason: str) -> dict[str, Any]:
        return {
            "status": status,
            "reason": reason,
            "rule_id": finding.rule_id,
            "paragraph_index": finding.paragraph_index,
            "run_index": finding.run_index,
        }
