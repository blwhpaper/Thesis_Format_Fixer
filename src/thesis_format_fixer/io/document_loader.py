"""Minimal document loader for TASK-004 safety skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


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
    footnotes: tuple[str, ...] = ()
    has_endnotes: bool = False
    valid_docx_package: bool = False



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
    footnotes: list[str] = []
    has_endnotes = False
    valid_docx_package = False
    can_read_docx = False
    can_write_docx = False

    if source_path.suffix.lower() in {".txt", ".md"}:
        text = source_path.read_text(encoding="utf-8")
        paragraphs = [line.strip() for line in text.splitlines()]
        can_read_docx = False
        can_write_docx = False
    elif source_path.suffix.lower() == ".docx" and source_path.exists():
        try:
            with ZipFile(source_path, "r") as archive:
                names = set(archive.namelist())
                if "word/document.xml" in names:
                    paragraphs = _extract_paragraph_texts(archive.read("word/document.xml"))
                    can_read_docx = True
                    can_write_docx = True
                    valid_docx_package = True
                if "word/footnotes.xml" in names:
                    footnotes = _extract_footnote_texts(archive.read("word/footnotes.xml"))
                has_endnotes = "word/endnotes.xml" in names
        except (BadZipFile, ET.ParseError, KeyError, OSError):
            can_read_docx = False
            can_write_docx = False

    return DocumentContext(
        source_path=source_path,
        paragraphs=tuple(paragraphs),
        footnotes=tuple(footnotes),
        has_endnotes=has_endnotes,
        valid_docx_package=valid_docx_package,
        capabilities=_default_capabilities(can_read_docx=can_read_docx, can_write_docx=can_write_docx),
    )


def _extract_paragraph_texts(document_xml: bytes) -> list[str]:
    root = ET.fromstring(document_xml)
    texts: list[str] = []
    for paragraph in root.findall(".//w:body/w:p", NS):
        text = _paragraph_text(paragraph).strip()
        if text:
            texts.append(text)
    return texts


def _extract_footnote_texts(footnotes_xml: bytes) -> list[str]:
    root = ET.fromstring(footnotes_xml)
    texts: list[str] = []
    for footnote in root.findall(".//w:footnote", NS):
        footnote_type = footnote.get(f"{{{W_NS}}}type")
        if footnote_type is not None:
            continue
        text = "".join(_paragraph_text(p) for p in footnote.findall(".//w:p", NS)).strip()
        if text:
            texts.append(text)
    return texts


def _paragraph_text(paragraph: ET.Element) -> str:
    chunks: list[str] = []
    for text_node in paragraph.findall(".//w:t", NS):
        chunks.append(text_node.text or "")
    return "".join(chunks)
