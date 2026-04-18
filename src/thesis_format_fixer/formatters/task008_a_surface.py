"""TASK-008 A-class hit-surface fixer (style-only, no content rewrite)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from thesis_format_fixer.contracts.report_types import Evidence
from thesis_format_fixer.detectors.block_locator import BlockMap

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"w": W_NS, "rel": REL_NS}

FONT_SONG = "宋体"
FONT_HEITI = "黑体"
FONT_TNR = "Times New Roman"
SMALL_TWO_HALF_PT = "36"
SMALL_THREE_HALF_PT = "32"
FOUR_HALF_PT = "28"
SMALL_FOUR_HALF_PT = "24"
FIVE_HALF_PT = "21"
LINE_25PT_TWIPS = "500"
LINE_SINGLE_TWIPS = "240"
TITLE_BEFORE_TWIPS = "360"
TITLE_AFTER_TWIPS = "240"


@dataclass(frozen=True, slots=True)
class RuleUpdate:
    status: str
    evidence: tuple[Evidence, ...]
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Task008Execution:
    updates: dict[str, RuleUpdate]


@dataclass(frozen=True, slots=True)
class _ParagraphRef:
    context_index: int
    element: ET.Element
    text: str


def execute_task008_a_surface_docx(
    path: Path,
    *,
    block_map: BlockMap,
    apply_fixes: bool,
    confidence_threshold: float,
) -> Task008Execution:
    try:
        with ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            raw_parts = {name: archive.read(name) for name in archive.namelist()}
    except (BadZipFile, OSError):
        return Task008Execution(updates={})

    if "word/document.xml" not in names:
        return Task008Execution(updates={})

    try:
        document_root = ET.fromstring(raw_parts["word/document.xml"])
    except ET.ParseError:
        return Task008Execution(updates={})

    body_paragraphs = document_root.findall(".//w:body/w:p", NS)
    paragraph_refs = _build_paragraph_refs(body_paragraphs)
    by_context_index = {item.context_index: item for item in paragraph_refs}

    modified = False
    updates: dict[str, RuleUpdate] = {}

    # Text/paragraph style rules.
    paragraph_style_rules: dict[str, tuple[tuple[str, ...], dict[str, str | bool]]] = {
        "FR-4.2-01": (("abstract_cn_title",), _style(font=FONT_HEITI, size=SMALL_TWO_HALF_PT, bold=True, center=True, line=LINE_25PT_TWIPS, before=TITLE_BEFORE_TWIPS, after=TITLE_AFTER_TWIPS)),
        "FR-4.2-02": (("abstract_cn_title",), _style(font=FONT_HEITI, size=SMALL_TWO_HALF_PT, bold=True, center=True, line=LINE_25PT_TWIPS, before=TITLE_BEFORE_TWIPS, after=TITLE_AFTER_TWIPS)),
        "FR-4.2-03": (("abstract_cn_body",), _style(font=FONT_SONG, size=SMALL_FOUR_HALF_PT, bold=False, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.3-01": (("keywords_cn",), _style(font=FONT_SONG, size=SMALL_FOUR_HALF_PT, bold=True, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.4-01": (("abstract_en_title",), _style(font=FONT_TNR, size=SMALL_TWO_HALF_PT, bold=True, center=True, line=LINE_25PT_TWIPS, before=TITLE_BEFORE_TWIPS, after=TITLE_AFTER_TWIPS)),
        "FR-4.4-02": (("abstract_en_title",), _style(font=FONT_TNR, size=SMALL_TWO_HALF_PT, bold=True, center=True, line=LINE_25PT_TWIPS, before=TITLE_BEFORE_TWIPS, after=TITLE_AFTER_TWIPS)),
        "FR-4.4-03": (("abstract_en_body",), _style(font=FONT_TNR, size=SMALL_FOUR_HALF_PT, bold=False, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.5-01": (("keywords_en",), _style(font=FONT_TNR, size=SMALL_FOUR_HALF_PT, bold=True, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.5-02": (("keywords_en",), _style(font=FONT_TNR, size=SMALL_FOUR_HALF_PT, bold=True, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.6-01": (("contents_title",), _style(font=FONT_TNR, size=SMALL_TWO_HALF_PT, bold=True, center=True, line=LINE_25PT_TWIPS, before=TITLE_BEFORE_TWIPS, after=TITLE_AFTER_TWIPS)),
        "FR-4.6-02": (("contents_title",), _style(font=FONT_TNR, size=SMALL_FOUR_HALF_PT, bold=False, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.7-01": (("body_main_title",), _style(font=FONT_TNR, size=SMALL_TWO_HALF_PT, bold=True, center=True, line=LINE_25PT_TWIPS, before=TITLE_BEFORE_TWIPS, after=TITLE_AFTER_TWIPS)),
        "FR-4.7-02": (("body_sub_title",), _style(font=FONT_TNR, size=SMALL_THREE_HALF_PT, bold=True, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.8-03": (("body_headings_h1",), _style(font=FONT_TNR, size=FOUR_HALF_PT, bold=True, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.8-04": (("body_headings_h2", "body_headings_h3"), _style(font=FONT_TNR, size=SMALL_FOUR_HALF_PT, bold=True, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.8-05": (("body_headings_h1", "body_headings_h2", "body_headings_h3"), _style(font=FONT_TNR, size=SMALL_FOUR_HALF_PT, bold=True, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.9-01": (("body_paragraphs",), _style(font=FONT_TNR, size=SMALL_FOUR_HALF_PT, bold=False, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.11-01": (("references_title",), _style(font=FONT_TNR, size=SMALL_TWO_HALF_PT, bold=True, center=True, line=LINE_25PT_TWIPS, before=TITLE_BEFORE_TWIPS, after=TITLE_AFTER_TWIPS)),
        "FR-4.11-02": (("references_entries",), _style(font=FONT_TNR, size=SMALL_FOUR_HALF_PT, bold=False, center=False, line=LINE_25PT_TWIPS)),
        "FR-4.12-01": (("ack_title",), _style(font=FONT_HEITI, size=SMALL_TWO_HALF_PT, bold=True, center=True, line=LINE_25PT_TWIPS, before=TITLE_BEFORE_TWIPS, after=TITLE_AFTER_TWIPS)),
        "FR-4.12-02": (("ack_body",), _style(font=FONT_SONG, size=SMALL_FOUR_HALF_PT, bold=False, center=False, line=LINE_25PT_TWIPS)),
    }

    for rule_id, (block_ids, style) in paragraph_style_rules.items():
        target_refs, evidence, status, degraded = _resolve_targets(
            block_map,
            block_ids=block_ids,
            by_context_index=by_context_index,
            confidence_threshold=confidence_threshold,
        )
        changed = False
        if apply_fixes and status == "applicable":
            for item in target_refs:
                changed |= _apply_paragraph_style(item.element, style)

        updates[rule_id] = _to_rule_update(
            rule_id,
            status=status,
            degraded=degraded,
            changed=changed,
            apply_fixes=apply_fixes,
            evidence=evidence,
            details={"target_blocks": list(block_ids), "target_count": len(target_refs)},
        )
        modified |= changed

    # Section margin rule.
    margin_block = block_map.blocks.get("page_margins")
    margin_degraded = margin_block is not None and margin_block.confidence < confidence_threshold
    margin_status = "not_applicable" if margin_block is None else ("degraded" if margin_degraded else "applicable")
    margin_changed = False
    if apply_fixes and margin_status == "applicable":
        for sect_pr in document_root.findall(".//w:body/w:sectPr", NS):
            margin_changed |= _set_page_margins(sect_pr)
    updates["FR-4.13-02"] = _to_rule_update(
        "FR-4.13-02",
        status=margin_status,
        degraded=margin_degraded,
        changed=margin_changed,
        apply_fixes=apply_fixes,
        evidence=_block_evidence(margin_block, "page_margins"),
        details={"target": "section.page_margins"},
    )
    modified |= margin_changed

    # Header / footer style rules.
    header_changed, header_count = _style_header_footer_parts(
        raw_parts,
        names,
        kind="header",
        apply_fixes=apply_fixes,
        font=FONT_TNR,
        size=FIVE_HALF_PT,
        line=LINE_25PT_TWIPS,
    )
    footer_changed, footer_count = _style_header_footer_parts(
        raw_parts,
        names,
        kind="footer",
        apply_fixes=apply_fixes,
        font=FONT_TNR,
        size=FIVE_HALF_PT,
        line=LINE_25PT_TWIPS,
    )
    modified |= header_changed or footer_changed

    header_block = block_map.blocks.get("header")
    footer_block = block_map.blocks.get("footer")

    updates["FR-4.14-01"] = _to_rule_update(
        "FR-4.14-01",
        status=("not_applicable" if header_count == 0 else ("degraded" if (header_block and header_block.confidence < confidence_threshold) else "applicable")),
        degraded=bool(header_block and header_block.confidence < confidence_threshold),
        changed=header_changed,
        apply_fixes=apply_fixes,
        evidence=_block_evidence(header_block, "header"),
        details={"header_parts": header_count},
    )
    updates["FR-4.14-02"] = _to_rule_update(
        "FR-4.14-02",
        status=("not_applicable" if footer_count == 0 else ("degraded" if (footer_block and footer_block.confidence < confidence_threshold) else "applicable")),
        degraded=bool(footer_block and footer_block.confidence < confidence_threshold),
        changed=footer_changed,
        apply_fixes=apply_fixes,
        evidence=_block_evidence(footer_block, "footer"),
        details={"footer_parts": footer_count},
    )

    if apply_fixes and modified:
        raw_parts["word/document.xml"] = ET.tostring(document_root, encoding="utf-8", xml_declaration=True)
        with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
            for name, content in raw_parts.items():
                archive.writestr(name, content)

    return Task008Execution(updates=updates)


def _style(
    *,
    font: str,
    size: str,
    bold: bool,
    center: bool,
    line: str,
    before: str | None = None,
    after: str | None = None,
) -> dict[str, str | bool]:
    return {
        "font": font,
        "size": size,
        "bold": bold,
        "center": center,
        "line": line,
        "before": before or "",
        "after": after or "",
    }


def _build_paragraph_refs(body_paragraphs: list[ET.Element]) -> list[_ParagraphRef]:
    refs: list[_ParagraphRef] = []
    context_index = 0
    for paragraph in body_paragraphs:
        text = _paragraph_text(paragraph).strip()
        if not text:
            continue
        refs.append(_ParagraphRef(context_index=context_index, element=paragraph, text=text))
        context_index += 1
    return refs


def _resolve_targets(
    block_map: BlockMap,
    *,
    block_ids: tuple[str, ...],
    by_context_index: dict[int, _ParagraphRef],
    confidence_threshold: float,
) -> tuple[list[_ParagraphRef], tuple[Evidence, ...], str, bool]:
    refs: dict[int, _ParagraphRef] = {}
    evidence: list[Evidence] = []
    degraded = False
    has_any_target = False

    for block_id in block_ids:
        block = block_map.blocks.get(block_id)
        if block is None or block.start_paragraph is None or block.end_paragraph is None:
            continue
        has_any_target = True
        evidence.extend(block.evidence)
        if block.confidence < confidence_threshold:
            degraded = True
            continue
        for idx in range(block.start_paragraph, block.end_paragraph + 1):
            ref = by_context_index.get(idx)
            if ref is not None:
                refs[ref.context_index] = ref

    if not has_any_target:
        return [], tuple(evidence), "not_applicable", degraded
    if degraded:
        return [], tuple(evidence), "degraded", degraded
    if not refs:
        return [], tuple(evidence), "not_applicable", degraded
    return list(refs.values()), tuple(evidence), "applicable", degraded


def _to_rule_update(
    rule_id: str,
    *,
    status: str,
    degraded: bool,
    changed: bool,
    apply_fixes: bool,
    evidence: tuple[Evidence, ...],
    details: dict[str, Any],
) -> RuleUpdate:
    if status == "not_applicable":
        return RuleUpdate(status="not_applicable", evidence=evidence, details={**details, "reason": "target_not_found"})
    if status == "degraded":
        return RuleUpdate(status="detected_not_modified", evidence=evidence, details={**details, "reason": "low_confidence_block"})
    if apply_fixes:
        return RuleUpdate(status="fixed" if changed else "checked_ok", evidence=evidence, details=details)
    return RuleUpdate(status="detected_not_modified", evidence=evidence, details={**details, "reason": "check_mode_no_write"})


def _block_evidence(block: Any, name: str) -> tuple[Evidence, ...]:
    if block is None:
        return (Evidence(paragraph_index=None, snippet=name, reason="block_not_found"),)
    return block.evidence


def _paragraph_text(paragraph: ET.Element) -> str:
    return "".join((item.text or "") for item in paragraph.findall(".//w:t", NS))


def _apply_paragraph_style(paragraph: ET.Element, style: dict[str, str | bool]) -> bool:
    changed = False
    changed |= _set_paragraph_spacing(
        paragraph,
        line=str(style["line"]),
        line_rule="exact" if str(style["line"]) == LINE_25PT_TWIPS else "auto",
        before=str(style["before"]),
        after=str(style["after"]),
    )
    changed |= _set_paragraph_alignment(paragraph, centered=bool(style["center"]))

    runs = paragraph.findall("w:r", NS)
    for run in runs:
        changed |= _set_run_font_size_bold(
            run,
            font_name=str(style["font"]),
            half_points=str(style["size"]),
            bold=bool(style["bold"]),
        )
    return changed


def _style_header_footer_parts(
    raw_parts: dict[str, bytes],
    names: set[str],
    *,
    kind: str,
    apply_fixes: bool,
    font: str,
    size: str,
    line: str,
) -> tuple[bool, int]:
    part_names = sorted(name for name in names if name.startswith(f"word/{kind}") and name.endswith(".xml"))
    if not part_names:
        return False, 0

    changed = False
    for part_name in part_names:
        try:
            root = ET.fromstring(raw_parts[part_name])
        except ET.ParseError:
            continue

        part_changed = False
        paragraphs = root.findall(".//w:p", NS)
        for paragraph in paragraphs:
            if apply_fixes:
                part_changed |= _set_paragraph_alignment(paragraph, centered=True)
                part_changed |= _set_paragraph_spacing(paragraph, line=line, line_rule="exact", before="", after="")
                for run in paragraph.findall("w:r", NS):
                    part_changed |= _set_run_font_size_bold(run, font_name=font, half_points=size, bold=False)

        if apply_fixes and part_changed:
            raw_parts[part_name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            changed = True

    return changed, len(part_names)


def _set_page_margins(sect_pr: ET.Element) -> bool:
    changed = False
    pg_mar = sect_pr.find("w:pgMar", NS)
    if pg_mar is None:
        pg_mar = ET.SubElement(sect_pr, f"{{{W_NS}}}pgMar")
        changed = True

    changed |= _set_attr(pg_mar, f"{{{W_NS}}}top", "1417")
    changed |= _set_attr(pg_mar, f"{{{W_NS}}}bottom", "1417")
    changed |= _set_attr(pg_mar, f"{{{W_NS}}}left", "1417")
    changed |= _set_attr(pg_mar, f"{{{W_NS}}}right", "1134")
    changed |= _set_attr(pg_mar, f"{{{W_NS}}}header", "1134")
    changed |= _set_attr(pg_mar, f"{{{W_NS}}}footer", "992")
    return changed


def _set_run_font_size_bold(run: ET.Element, *, font_name: str, half_points: str, bold: bool) -> bool:
    changed = False
    rpr = run.find("w:rPr", NS)
    if rpr is None:
        rpr = ET.SubElement(run, f"{{{W_NS}}}rPr")
        changed = True

    rfonts = rpr.find("w:rFonts", NS)
    if rfonts is None:
        rfonts = ET.SubElement(rpr, f"{{{W_NS}}}rFonts")
        changed = True

    changed |= _set_attr(rfonts, f"{{{W_NS}}}ascii", font_name)
    changed |= _set_attr(rfonts, f"{{{W_NS}}}hAnsi", font_name)
    changed |= _set_attr(rfonts, f"{{{W_NS}}}eastAsia", font_name)
    changed |= _set_attr(rfonts, f"{{{W_NS}}}cs", font_name)

    sz = rpr.find("w:sz", NS)
    if sz is None:
        sz = ET.SubElement(rpr, f"{{{W_NS}}}sz")
        changed = True
    changed |= _set_attr(sz, f"{{{W_NS}}}val", half_points)

    szcs = rpr.find("w:szCs", NS)
    if szcs is None:
        szcs = ET.SubElement(rpr, f"{{{W_NS}}}szCs")
        changed = True
    changed |= _set_attr(szcs, f"{{{W_NS}}}val", half_points)

    b = rpr.find("w:b", NS)
    if bold:
        if b is None:
            b = ET.SubElement(rpr, f"{{{W_NS}}}b")
            changed = True
        changed |= _set_attr(b, f"{{{W_NS}}}val", "1")
    else:
        if b is not None:
            changed |= _set_attr(b, f"{{{W_NS}}}val", "0")
    return changed


def _set_paragraph_spacing(
    paragraph: ET.Element,
    *,
    line: str,
    line_rule: str,
    before: str,
    after: str,
) -> bool:
    changed = False
    ppr = paragraph.find("w:pPr", NS)
    if ppr is None:
        ppr = ET.SubElement(paragraph, f"{{{W_NS}}}pPr")
        changed = True

    spacing = ppr.find("w:spacing", NS)
    if spacing is None:
        spacing = ET.SubElement(ppr, f"{{{W_NS}}}spacing")
        changed = True

    changed |= _set_attr(spacing, f"{{{W_NS}}}line", line)
    changed |= _set_attr(spacing, f"{{{W_NS}}}lineRule", line_rule)
    if before:
        changed |= _set_attr(spacing, f"{{{W_NS}}}before", before)
    if after:
        changed |= _set_attr(spacing, f"{{{W_NS}}}after", after)
    return changed


def _set_paragraph_alignment(paragraph: ET.Element, *, centered: bool) -> bool:
    changed = False
    ppr = paragraph.find("w:pPr", NS)
    if ppr is None:
        ppr = ET.SubElement(paragraph, f"{{{W_NS}}}pPr")
        changed = True

    jc = ppr.find("w:jc", NS)
    if jc is None:
        jc = ET.SubElement(ppr, f"{{{W_NS}}}jc")
        changed = True
    changed |= _set_attr(jc, f"{{{W_NS}}}val", "center" if centered else "left")
    return changed


def _set_attr(node: ET.Element, name: str, value: str) -> bool:
    if node.get(name) == value:
        return False
    node.set(name, value)
    return True
