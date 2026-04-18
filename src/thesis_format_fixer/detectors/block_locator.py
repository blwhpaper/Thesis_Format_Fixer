"""Minimal block locator for TASK-004."""

from __future__ import annotations

from dataclasses import dataclass

from thesis_format_fixer.contracts.report_types import BlockDetection, Evidence
from thesis_format_fixer.io.document_loader import DocumentContext


@dataclass(frozen=True, slots=True)
class BlockMap:
    blocks: dict[str, BlockDetection]


BLOCK_ANCHORS: dict[str, tuple[str, ...]] = {
    "abstract_cn": ("摘 要", "摘要"),
    "keywords_cn": ("关键词",),
    "abstract_en": ("Abstract",),
    "keywords_en": ("Keywords",),
    "contents": ("CONTENTS",),
    "references": ("REFERENCES",),
    "ack": ("致谢",),
}



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



def locate_blocks(context: DocumentContext) -> BlockMap:
    blocks: dict[str, BlockDetection] = {}

    for block_id, anchors in BLOCK_ANCHORS.items():
        best: tuple[int, float, str] | None = None
        for idx, line in enumerate(context.paragraphs):
            match = _match_anchor(line, anchors)
            if not match:
                continue
            confidence, reason = match
            candidate = (idx, confidence, reason)
            if best is None or candidate[1] > best[1]:
                best = candidate

        if best is None:
            blocks[block_id] = BlockDetection(
                block_id=block_id,
                start_paragraph=None,
                end_paragraph=None,
                confidence=0.0,
                evidence=(Evidence(paragraph_index=None, snippet="", reason="anchor_not_found"),),
            )
            continue

        idx, confidence, reason = best
        snippet = context.paragraphs[idx]
        blocks[block_id] = BlockDetection(
            block_id=block_id,
            start_paragraph=idx,
            end_paragraph=idx,
            confidence=confidence,
            evidence=(Evidence(paragraph_index=idx, snippet=snippet, reason=reason),),
        )

    return BlockMap(blocks=blocks)
