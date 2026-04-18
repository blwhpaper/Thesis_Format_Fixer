"""Minimal document loader for TASK-004 safety skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CapabilityFlags:
    can_read_docx: bool
    can_write_docx: bool
    can_rebuild_toc: bool
    can_reconstruct_sections: bool
    can_renumber_footnotes_per_page: bool
    can_reconstruct_odd_even_layout: bool
    can_rebuild_cover: bool
    can_reorder_bibliography_content: bool


@dataclass(frozen=True, slots=True)
class DocumentContext:
    source_path: Path
    paragraphs: tuple[str, ...]
    capabilities: CapabilityFlags



def _default_capabilities(can_read_docx: bool, can_write_docx: bool) -> CapabilityFlags:
    return CapabilityFlags(
        can_read_docx=can_read_docx,
        can_write_docx=can_write_docx,
        can_rebuild_toc=False,
        can_reconstruct_sections=False,
        can_renumber_footnotes_per_page=False,
        can_reconstruct_odd_even_layout=False,
        can_rebuild_cover=False,
        can_reorder_bibliography_content=False,
    )



def load_document(path: str | Path) -> DocumentContext:
    source_path = Path(path)
    paragraphs: list[str] = []
    can_read_docx = False
    can_write_docx = False

    if source_path.suffix.lower() in {".txt", ".md"}:
        text = source_path.read_text(encoding="utf-8")
        paragraphs = [line.strip() for line in text.splitlines()]
        can_read_docx = False
        can_write_docx = False
    elif source_path.suffix.lower() == ".docx":
        # TASK-004 keeps only skeleton behavior: no actual DOCX parsing is introduced.
        can_read_docx = False
        can_write_docx = False

    return DocumentContext(
        source_path=source_path,
        paragraphs=tuple(paragraphs),
        capabilities=_default_capabilities(can_read_docx=can_read_docx, can_write_docx=can_write_docx),
    )
