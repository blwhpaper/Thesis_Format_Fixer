"""Block locator with TASK-008 A-class hit-surface coverage."""

from __future__ import annotations

from dataclasses import dataclass
import re

from thesis_format_fixer.contracts.report_types import BlockDetection, Evidence
from thesis_format_fixer.io.document_loader import DocumentContext


@dataclass(frozen=True, slots=True)
class BlockMap:
    blocks: dict[str, BlockDetection]


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
REFERENCE_ENTRY_RE = re.compile(r"^\s*(\[\d+\]|\d+\.)\s*\S+")


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
        refs_start = references_idx + 1
        refs_end = (ack_idx - 1) if (ack_idx is not None and ack_idx > references_idx) else (len(paragraphs) - 1)
        if refs_start <= refs_end and refs_start < len(paragraphs):
            entry_indices = [idx for idx in range(refs_start, refs_end + 1) if REFERENCE_ENTRY_RE.match(paragraphs[idx].strip())]
            if entry_indices:
                blocks["references_entries"] = _make_span(
                    "references_entries",
                    start=entry_indices[0],
                    end=entry_indices[-1],
                    confidence=0.9,
                    reason="reference_entry_pattern_scan",
                    paragraphs=paragraphs,
                )
            else:
                blocks["references_entries"] = _make_missing("references_entries")
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
    blocks["ack"] = blocks["ack_title"]

    return BlockMap(blocks=blocks)
