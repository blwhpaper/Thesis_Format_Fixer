"""Block locator with TASK-008 A-class hit-surface coverage."""

from __future__ import annotations

from dataclasses import dataclass
import re

from thesis_format_fixer.contracts.report_types import BlockDetection, Evidence
from thesis_format_fixer.io.document_loader import DocumentContext


@dataclass(frozen=True, slots=True)
class BlockMap:
    blocks: dict[str, BlockDetection]


@dataclass(frozen=True, slots=True)
class ReferenceScanResult:
    entry_groups: tuple[tuple[int, ...], ...]
    entry_group_sources: tuple[str, ...]
    skipped_indices: tuple[int, ...]
    suspicious_unrecognized_indices: tuple[int, ...]
    stop_reason: str


BLOCK_ANCHORS: dict[str, tuple[str, ...]] = {
    "abstract_cn_title": ("摘 要", "摘要"),
    "keywords_cn": ("关键词",),
    "abstract_en_title": ("Abstract",),
    "keywords_en": ("Keywords",),
    "contents_title": ("CONTENTS",),
    "references_title": ("REFERENCES", "参考文献"),
    "ack_title": ("致谢",),
}


HEADING_1_RE = re.compile(r"^\s*\d+\s+\S+")
HEADING_2_RE = re.compile(r"^\s*\d+\.\d+\s+\S+")
HEADING_3_RE = re.compile(r"^\s*\d+\.\d+\.\d+\s+\S+")
REFERENCE_ENTRY_STRONG_RE = re.compile(r"^\s*\[(\d+)\]\s*\S+")
SHORT_HEADING_RE = re.compile(r"^[A-Z][A-Z\s]{2,30}$")
AUTHOR_ENTRY_EN_RE = re.compile(
    r"^[A-Z][A-Za-z'`\-]*(?:\s+[A-Z](?:\.)?)*"
    r"(?:\s*,\s*[A-Z][A-Za-z'`\-]*(?:\s+[A-Z](?:\.)?)*)*"
    r"(?:\s+(?:and|&)\s+[A-Z][A-Za-z'`\-]*(?:\s+[A-Z](?:\.)?)*)?"
    r"(?:\s+et\s+al\.?)?"
    r"\s*[，,.;。:：]"
)
AUTHOR_ENTRY_ZH_RE = re.compile(
    r"^[\u4e00-\u9fff]{1,4}"
    r"(?:\s*[、，,]\s*[\u4e00-\u9fff]{1,4}){0,8}"
    r"(?:\s*[，,]\s*[A-Z][A-Za-z'`\-]*(?:\s+[A-Z](?:\.)?)*)*"
    r"\s*[，,.;。:：]"
)
AUTHOR_LEADING_EN_EXCLUDE_PREFIXES: frozenset[str] = frozenset(
    {
        "master",
        "thesis",
        "dissertation",
        "journal",
        "technical",
        "report",
        "proceedings",
        "vol",
        "volume",
    }
)

REFERENCE_SECTION_STOP_HEADINGS: frozenset[str] = frozenset(
    {
        "致谢",
        "acknowledgements",
        "acknowledgments",
        "appendix",
        "附录",
        "contents",
        "目录",
        "abstract",
        "摘 要",
        "摘要",
        "references",
        "参考文献",
    }
)


def _match_anchor(line: str, anchors: tuple[str, ...]) -> tuple[float, str] | None:
    stripped = line.strip()
    lowered = stripped.lower()

    for anchor in anchors:
        if stripped == anchor:
            return 0.99, f"exact_match:{anchor}"
        if lowered == anchor.lower():
            return 0.98, f"casefold_match:{anchor}"
        if anchor in stripped:
            return 0.90, f"substring_match:{anchor}"
    return None


def _find_best_anchor_index(paragraphs: tuple[str, ...], anchors: tuple[str, ...]) -> tuple[int, float, str] | None:
    best: tuple[int, float, str] | None = None
    for idx, line in enumerate(paragraphs):
        match = _match_anchor(line, anchors)
        if not match:
            continue
        confidence, reason = match
        candidate = (idx, confidence, reason)
        if best is None or candidate[1] > best[1]:
            best = candidate
    return best


def _find_references_heading_index(paragraphs: tuple[str, ...]) -> tuple[int, float, str] | None:
    for idx, line in enumerate(paragraphs):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "REFERENCES":
            return idx, 0.99, "exact_match:REFERENCES"
        if stripped.casefold() == "references":
            return idx, 0.98, "casefold_match:REFERENCES"
        if stripped == "参考文献":
            return idx, 0.96, "exact_match:参考文献"
    return None


def _is_reference_stop_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.casefold() in REFERENCE_SECTION_STOP_HEADINGS:
        return True
    if stripped in REFERENCE_SECTION_STOP_HEADINGS:
        return True
    return False


def _looks_like_new_section_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _is_reference_stop_heading(stripped):
        return True
    if HEADING_3_RE.match(stripped) or HEADING_2_RE.match(stripped) or HEADING_1_RE.match(stripped):
        return True
    if SHORT_HEADING_RE.match(stripped):
        words = [item for item in stripped.split() if item]
        if len(words) <= 4:
            return True
    return False


def _looks_like_author_leading_entry_start(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if REFERENCE_ENTRY_STRONG_RE.match(stripped):
        return False
    if _looks_like_new_section_heading(stripped):
        return False
    first_word_match = re.match(r"^([A-Za-z]+)", stripped)
    if first_word_match is not None and first_word_match.group(1).casefold() in AUTHOR_LEADING_EN_EXCLUDE_PREFIXES:
        return False
    if AUTHOR_ENTRY_EN_RE.match(stripped):
        return True
    if AUTHOR_ENTRY_ZH_RE.match(stripped):
        return True
    return False


def scan_reference_entries(
    paragraphs: tuple[str, ...],
    *,
    heading_index: int,
    hard_stop_index: int | None = None,
) -> ReferenceScanResult:
    start = heading_index + 1
    end = hard_stop_index if hard_stop_index is not None else len(paragraphs)
    end = max(start, min(end, len(paragraphs)))

    entry_groups: list[list[int]] = []
    entry_group_sources: list[str] = []
    current_group: list[int] = []
    current_source: str | None = None
    skipped: list[int] = []
    suspicious_unrecognized: list[int] = []
    stop_reason = "scan_end"
    pre_entry_noise = 0
    blank_noise = 0

    def _flush_current() -> None:
        nonlocal current_group, current_source
        if not current_group:
            return
        entry_groups.append(current_group)
        entry_group_sources.append(current_source or "numbered_entry")
        current_group = []
        current_source = None

    for idx in range(start, end):
        text = paragraphs[idx].strip()
        if not text:
            if current_group:
                blank_noise += 1
                if blank_noise > 1:
                    stop_reason = "blank_noise_after_entries"
                    break
            continue

        blank_noise = 0
        if _is_reference_stop_heading(text):
            stop_reason = "explicit_stop_heading"
            break

        if REFERENCE_ENTRY_STRONG_RE.match(text):
            _flush_current()
            current_group = [idx]
            current_source = "numbered_entry"
            continue

        if _looks_like_author_leading_entry_start(text):
            _flush_current()
            current_group = [idx]
            current_source = "author_leading_fallback"
            continue

        if not entry_groups and not current_group:
            pre_entry_noise += 1
            skipped.append(idx)
            suspicious_unrecognized.append(idx)
            if _looks_like_new_section_heading(text):
                stop_reason = "new_section_before_entries"
                break
            if pre_entry_noise > 2:
                stop_reason = "entry_start_signal_missing"
                break
            continue

        if _looks_like_new_section_heading(text):
            stop_reason = "new_section_after_entries"
            break

        current_group.append(idx)

    _flush_current()

    return ReferenceScanResult(
        entry_groups=tuple(tuple(group) for group in entry_groups),
        entry_group_sources=tuple(entry_group_sources),
        skipped_indices=tuple(skipped),
        suspicious_unrecognized_indices=tuple(suspicious_unrecognized),
        stop_reason=stop_reason,
    )


def _make_missing(block_id: str) -> BlockDetection:
    return BlockDetection(
        block_id=block_id,
        start_paragraph=None,
        end_paragraph=None,
        confidence=0.0,
        evidence=(Evidence(paragraph_index=None, snippet="", reason="anchor_not_found"),),
    )


def _make_span(
    block_id: str,
    *,
    start: int,
    end: int,
    confidence: float,
    reason: str,
    paragraphs: tuple[str, ...],
) -> BlockDetection:
    snippet = paragraphs[start] if 0 <= start < len(paragraphs) else ""
    return BlockDetection(
        block_id=block_id,
        start_paragraph=start,
        end_paragraph=end,
        confidence=confidence,
        evidence=(Evidence(paragraph_index=start, snippet=snippet, reason=reason),),
    )


def _ordered_existing(*indices: int | None) -> list[int]:
    return sorted(idx for idx in indices if idx is not None)


def _scan_heading_indices(paragraphs: tuple[str, ...], start: int, end: int) -> tuple[list[int], list[int], list[int]]:
    h1: list[int] = []
    h2: list[int] = []
    h3: list[int] = []
    for idx in range(start, end + 1):
        line = paragraphs[idx].strip()
        if not line:
            continue
        if HEADING_3_RE.match(line):
            h3.append(idx)
            continue
        if HEADING_2_RE.match(line):
            h2.append(idx)
            continue
        if HEADING_1_RE.match(line):
            h1.append(idx)
    return h1, h2, h3


def locate_blocks(context: DocumentContext) -> BlockMap:
    blocks: dict[str, BlockDetection] = {}
    paragraphs = context.paragraphs
    anchor_hits: dict[str, tuple[int, float, str] | None] = {
        block_id: _find_best_anchor_index(paragraphs, anchors)
        for block_id, anchors in BLOCK_ANCHORS.items()
    }
    anchor_hits["references_title"] = _find_references_heading_index(paragraphs)

    # 1) Direct anchor blocks.
    for block_id in BLOCK_ANCHORS:
        best = anchor_hits[block_id]
        if best is None:
            blocks[block_id] = _make_missing(block_id)
            continue
        idx, confidence, reason = best
        blocks[block_id] = _make_span(
            block_id,
            start=idx,
            end=idx,
            confidence=confidence,
            reason=reason,
            paragraphs=paragraphs,
        )

    abstract_cn_idx = blocks["abstract_cn_title"].start_paragraph
    abstract_en_idx = blocks["abstract_en_title"].start_paragraph
    contents_idx = blocks["contents_title"].start_paragraph
    references_idx = blocks["references_title"].start_paragraph
    ack_idx = blocks["ack_title"].start_paragraph

    # 2) Abstract and keyword body ranges.
    if abstract_cn_idx is not None and abstract_en_idx is not None and abstract_en_idx > abstract_cn_idx:
        cn_body_end = max(abstract_cn_idx, abstract_en_idx - 1)
        blocks["abstract_cn_body"] = _make_span(
            "abstract_cn_body",
            start=abstract_cn_idx + 1,
            end=cn_body_end,
            confidence=0.92,
            reason="range_between_cn_and_en_abstract",
            paragraphs=paragraphs,
        )
    else:
        blocks["abstract_cn_body"] = _make_missing("abstract_cn_body")

    if abstract_en_idx is not None and contents_idx is not None and contents_idx > abstract_en_idx:
        en_body_end = max(abstract_en_idx, contents_idx - 1)
        blocks["abstract_en_body"] = _make_span(
            "abstract_en_body",
            start=abstract_en_idx + 1,
            end=en_body_end,
            confidence=0.92,
            reason="range_between_en_abstract_and_contents",
            paragraphs=paragraphs,
        )
    else:
        blocks["abstract_en_body"] = _make_missing("abstract_en_body")

    # 3) Body range and heading/paragraph candidates.
    body_start = None
    if contents_idx is not None:
        body_start = contents_idx + 1
    elif abstract_en_idx is not None:
        body_start = abstract_en_idx + 1

    body_end = None
    ordered_tail = _ordered_existing(references_idx, ack_idx)
    if ordered_tail:
        body_end = ordered_tail[0] - 1
    elif paragraphs:
        body_end = len(paragraphs) - 1

    if (
        body_start is not None
        and body_end is not None
        and 0 <= body_start <= body_end < len(paragraphs)
    ):
        blocks["body"] = _make_span(
            "body",
            start=body_start,
            end=body_end,
            confidence=0.9,
            reason="body_range_heuristic",
            paragraphs=paragraphs,
        )
        h1, h2, h3 = _scan_heading_indices(paragraphs, body_start, body_end)
        heading_all = sorted([*h1, *h2, *h3])
        if heading_all:
            blocks["body_main_title"] = _make_span(
                "body_main_title",
                start=heading_all[0],
                end=heading_all[0],
                confidence=0.88,
                reason="first_numbered_heading_as_main_title",
                paragraphs=paragraphs,
            )
            if len(heading_all) > 1:
                blocks["body_sub_title"] = _make_span(
                    "body_sub_title",
                    start=heading_all[1],
                    end=heading_all[1],
                    confidence=0.86,
                    reason="second_numbered_heading_as_sub_title",
                    paragraphs=paragraphs,
                )
            else:
                blocks["body_sub_title"] = _make_missing("body_sub_title")
            blocks["body_headings_h1"] = _make_span(
                "body_headings_h1",
                start=h1[0] if h1 else heading_all[0],
                end=h1[-1] if h1 else heading_all[0],
                confidence=0.89 if h1 else 0.7,
                reason="body_h1_heading_scan",
                paragraphs=paragraphs,
            )
            blocks["body_headings_h2"] = _make_span(
                "body_headings_h2",
                start=h2[0] if h2 else heading_all[0],
                end=h2[-1] if h2 else heading_all[0],
                confidence=0.88 if h2 else 0.7,
                reason="body_h2_heading_scan",
                paragraphs=paragraphs,
            )
            blocks["body_headings_h3"] = _make_span(
                "body_headings_h3",
                start=h3[0] if h3 else heading_all[0],
                end=h3[-1] if h3 else heading_all[0],
                confidence=0.86 if h3 else 0.7,
                reason="body_h3_heading_scan",
                paragraphs=paragraphs,
            )
            paragraph_indices = [
                idx
                for idx in range(body_start, body_end + 1)
                if idx not in set(heading_all) and paragraphs[idx].strip()
            ]
            if paragraph_indices:
                blocks["body_paragraphs"] = _make_span(
                    "body_paragraphs",
                    start=paragraph_indices[0],
                    end=paragraph_indices[-1],
                    confidence=0.85,
                    reason="body_non_heading_paragraph_scan",
                    paragraphs=paragraphs,
                )
            else:
                blocks["body_paragraphs"] = _make_missing("body_paragraphs")
        else:
            blocks["body_main_title"] = _make_missing("body_main_title")
            blocks["body_sub_title"] = _make_missing("body_sub_title")
            blocks["body_headings_h1"] = _make_missing("body_headings_h1")
            blocks["body_headings_h2"] = _make_missing("body_headings_h2")
            blocks["body_headings_h3"] = _make_missing("body_headings_h3")
            blocks["body_paragraphs"] = _make_missing("body_paragraphs")
    else:
        for block_id in (
            "body",
            "body_main_title",
            "body_sub_title",
            "body_headings_h1",
            "body_headings_h2",
            "body_headings_h3",
            "body_paragraphs",
        ):
            blocks[block_id] = _make_missing(block_id)

    # 4) References and acknowledgement body ranges.
    if references_idx is not None:
        hard_stop = ack_idx if (ack_idx is not None and ack_idx > references_idx) else None
        reference_scan = scan_reference_entries(paragraphs, heading_index=references_idx, hard_stop_index=hard_stop)
        entry_indices = [idx for group in reference_scan.entry_groups for idx in group]
        if entry_indices:
            numbered_count = sum(1 for source in reference_scan.entry_group_sources if source == "numbered_entry")
            fallback_count = sum(1 for source in reference_scan.entry_group_sources if source == "author_leading_fallback")
            blocks["references_entries"] = _make_span(
                "references_entries",
                start=entry_indices[0],
                end=entry_indices[-1],
                confidence=0.93,
                reason=(
                    "reference_entry_scan:"
                    + f"groups={len(reference_scan.entry_groups)};"
                    + f"numbered={numbered_count};"
                    + f"author_fallback={fallback_count};"
                    + f"paragraphs={len(entry_indices)};"
                    + f"skipped={len(reference_scan.skipped_indices)};"
                    + f"suspicious={len(reference_scan.suspicious_unrecognized_indices)};"
                    + f"stop={reference_scan.stop_reason}"
                ),
                paragraphs=paragraphs,
            )
        else:
            blocks["references_entries"] = _make_missing("references_entries")
    else:
        blocks["references_entries"] = _make_missing("references_entries")

    if ack_idx is not None:
        ack_body_start = ack_idx + 1
        ack_body_end = len(paragraphs) - 1
        if ack_body_start <= ack_body_end and ack_body_start < len(paragraphs):
            blocks["ack_body"] = _make_span(
                "ack_body",
                start=ack_body_start,
                end=ack_body_end,
                confidence=0.9,
                reason="ack_body_tail_range",
                paragraphs=paragraphs,
            )
        else:
            blocks["ack_body"] = _make_missing("ack_body")
    else:
        blocks["ack_body"] = _make_missing("ack_body")

    # 5) Section/header/footer capability blocks.
    if context.valid_docx_package:
        evidence = (Evidence(paragraph_index=None, snippet="word/document.xml", reason="section_capability_available"),)
        blocks["page_margins"] = BlockDetection(
            block_id="page_margins",
            start_paragraph=None,
            end_paragraph=None,
            confidence=0.95,
            evidence=evidence,
        )
        blocks["header"] = BlockDetection(
            block_id="header",
            start_paragraph=None,
            end_paragraph=None,
            confidence=0.95,
            evidence=evidence,
        )
        blocks["footer"] = BlockDetection(
            block_id="footer",
            start_paragraph=None,
            end_paragraph=None,
            confidence=0.95,
            evidence=evidence,
        )
    else:
        blocks["page_margins"] = _make_missing("page_margins")
        blocks["header"] = _make_missing("header")
        blocks["footer"] = _make_missing("footer")

    # Backward-compatible aliases used by TASK-007 review/checkers.
    blocks["abstract_cn"] = blocks["abstract_cn_title"]
    blocks["abstract_en"] = blocks["abstract_en_title"]
    blocks["contents"] = blocks["contents_title"]
    blocks["references"] = blocks["references_title"]
    blocks["references_heading"] = blocks["references_title"]
    blocks["ack"] = blocks["ack_title"]

    return BlockMap(blocks=blocks)
