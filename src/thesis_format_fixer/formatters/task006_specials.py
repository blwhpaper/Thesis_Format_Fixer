"""TASK-006 focused DOCX footnote/bibliography enhancement utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from thesis_format_fixer.contracts.report_types import Evidence

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}

FONT_SONG = "宋体"
FONT_TNR = "Times New Roman"
SMALL_FIVE_HALF_PT = "18"  # 9pt
SMALL_FOUR_HALF_PT = "24"  # 12pt
SINGLE_SPACING_TWIPS = "240"
LINE_25PT_TWIPS = "500"
REFERENCE_ENTRY_STRONG_RE = re.compile(r"^\s*\[(\d+)\]\s*\S+")
SENTENCE_LIKE_EN_RE = re.compile(r"^[A-Z][a-z]+\s+[a-z]{2,}\b")
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
AUTHOR_LEADING_EN_EXCLUDE_PREFIXES: set[str] = {
    "acknowledgements",
    "acknowledgments",
    "appendix",
    "appendices",
    "introduction",
    "conclusion",
    "discussion",
    "references",
    "note",
    "notes",
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
REFERENCE_CONTINUATION_HINT_RE = re.compile(
    r"^(?:"
    r"\(?\d{4}\)?"
    r"|vol\.?\s*\d+"
    r"|no\.?\s*\d+"
    r"|pp?\.?\s*\d+"
    r"|doi[:\s]"
    r"|https?://"
    r"|[(),.;:，。；：]"
    r")",
    re.IGNORECASE,
)
REFERENCE_CONTINUATION_KEYWORDS: tuple[str, ...] = (
    "journal",
    "press",
    "publisher",
    "proceedings",
    "thesis",
    "dissertation",
    "report",
    "university",
    "vol.",
    "volume",
    "no.",
    "pp.",
    "doi",
    "出版社",
    "学位论文",
    "报告",
    "卷",
    "期",
    "页",
)


@dataclass(frozen=True, slots=True)
class RuleUpdate:
    status: str
    evidence: tuple[Evidence, ...]
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Task006Execution:
    updates: dict[str, RuleUpdate]


@dataclass(frozen=True, slots=True)
class _ReferenceEntry:
    start_index: int
    paragraphs: tuple[ET.Element, ...]
    text: str
    index_value: int | None
    source: str


def execute_task006_docx(path: Path, *, apply_fixes: bool) -> Task006Execution:
    updates: dict[str, RuleUpdate] = {}

    try:
        with ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            raw_parts = {name: archive.read(name) for name in archive.namelist()}
    except (BadZipFile, OSError):
        return Task006Execution(
            updates={
                "FR-4.10-02": _unsupported("footnotes_part_unreadable"),
                "FR-4.10-03": _unsupported("footnotes_part_unreadable"),
                "FR-4.10-04": _unsupported("footnotes_part_unreadable"),
                "FR-4.11-02": _unsupported("references_block_unreadable"),
                "FR-4.11-03": _unsupported("references_block_unreadable"),
                "FR-4.11-07": _unsupported("references_block_unreadable"),
                "FR-4.11-04": _unsupported("references_block_unreadable"),
                "FR-4.11-05": _unsupported("references_block_unreadable"),
                "FR-4.11-06": _unsupported("references_block_unreadable"),
            }
        )

    modified = False

    if "word/footnotes.xml" in names:
        try:
            footnotes_root = ET.fromstring(raw_parts["word/footnotes.xml"])
            footnote_updates, footnotes_changed = _fix_and_check_footnotes(footnotes_root, apply_fixes=apply_fixes)
            updates.update(footnote_updates)
            if footnotes_changed and apply_fixes:
                raw_parts["word/footnotes.xml"] = ET.tostring(footnotes_root, encoding="utf-8", xml_declaration=True)
                modified = True
        except ET.ParseError:
            updates["FR-4.10-02"] = _unsupported("footnotes_xml_parse_error")
            updates["FR-4.10-03"] = _unsupported("footnotes_xml_parse_error")
            updates["FR-4.10-04"] = _unsupported("footnotes_xml_parse_error")
    else:
        updates["FR-4.10-02"] = RuleUpdate(status="not_applicable", evidence=(), details={"reason": "no_footnotes"})
        updates["FR-4.10-03"] = RuleUpdate(status="not_applicable", evidence=(), details={"reason": "no_footnotes"})
        updates["FR-4.10-04"] = RuleUpdate(status="not_applicable", evidence=(), details={"reason": "no_footnotes"})

    if "word/document.xml" in names:
        try:
            document_root = ET.fromstring(raw_parts["word/document.xml"])
            bibliography_updates, references_changed = _fix_and_check_references(
                document_root,
                apply_fixes=apply_fixes,
                current_year=datetime.now().year,
            )
            updates.update(bibliography_updates)
            if references_changed and apply_fixes:
                raw_parts["word/document.xml"] = ET.tostring(document_root, encoding="utf-8", xml_declaration=True)
                modified = True
        except ET.ParseError:
            for rule_id in ("FR-4.11-02", "FR-4.11-03", "FR-4.11-04", "FR-4.11-05", "FR-4.11-06", "FR-4.11-07"):
                updates[rule_id] = _unsupported("document_xml_parse_error")
    else:
        for rule_id in ("FR-4.11-02", "FR-4.11-03", "FR-4.11-04", "FR-4.11-05", "FR-4.11-06", "FR-4.11-07"):
            updates[rule_id] = _unsupported("document_xml_missing")

    if "word/endnotes.xml" in names:
        updates["FR-4.10-01"] = RuleUpdate(
            status="detected_not_modified",
            evidence=(Evidence(paragraph_index=None, snippet="word/endnotes.xml", reason="endnotes_present"),),
            details={"issue": "endnotes_detected"},
        )
    else:
        updates["FR-4.10-01"] = RuleUpdate(status="checked_ok", evidence=(), details={"issue": "no_endnotes"})

    if modified and apply_fixes:
        with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
            for name, content in raw_parts.items():
                archive.writestr(name, content)

    return Task006Execution(updates=updates)


def _unsupported(reason: str) -> RuleUpdate:
    return RuleUpdate(status="detected_not_modified", evidence=(), details={"reason": reason})


def _fix_and_check_footnotes(root: ET.Element, *, apply_fixes: bool) -> tuple[dict[str, RuleUpdate], bool]:
    changed = False
    cn_count = 0
    en_count = 0
    skipped_unstable = 0

    for footnote in root.findall(".//w:footnote", NS):
        if footnote.get(f"{{{W_NS}}}type") is not None:
            continue
        paragraphs = footnote.findall(".//w:p", NS)
        if not paragraphs:
            skipped_unstable += 1
            continue

        text = "".join(_paragraph_text(paragraph) for paragraph in paragraphs).strip()
        if not text:
            skipped_unstable += 1
            continue

        is_cn = _contains_cjk(text)
        if is_cn:
            cn_count += 1
        else:
            en_count += 1

        target_font = FONT_SONG if is_cn else FONT_TNR

        for paragraph in paragraphs:
            if apply_fixes and _set_paragraph_spacing(paragraph, line=SINGLE_SPACING_TWIPS, line_rule="auto"):
                changed = True
            runs = paragraph.findall("w:r", NS)
            if not runs:
                skipped_unstable += 1
                continue
            for run in runs:
                if apply_fixes and _set_run_font_and_size(run, font_name=target_font, half_points=SMALL_FIVE_HALF_PT):
                    changed = True

    footnote_evidence = (
        Evidence(
            paragraph_index=None,
            snippet=f"cn={cn_count}, en={en_count}, unstable={skipped_unstable}",
            reason="footnote_scan_summary",
        ),
    )

    updates: dict[str, RuleUpdate] = {}

    cn_status = "fixed" if (apply_fixes and cn_count > 0 and changed) else "checked_ok"
    en_status = "fixed" if (apply_fixes and en_count > 0 and changed) else "checked_ok"
    spacing_status = "fixed" if (apply_fixes and (cn_count + en_count) > 0 and changed) else "checked_ok"

    if skipped_unstable > 0:
        details = {"issue": "unstable_footnote_object", "unstable_count": skipped_unstable}
        updates["FR-4.10-02"] = RuleUpdate(status="detected_not_modified", evidence=footnote_evidence, details=details)
        updates["FR-4.10-03"] = RuleUpdate(status="detected_not_modified", evidence=footnote_evidence, details=details)
        updates["FR-4.10-04"] = RuleUpdate(status="detected_not_modified", evidence=footnote_evidence, details=details)
    else:
        updates["FR-4.10-02"] = RuleUpdate(status=cn_status, evidence=footnote_evidence, details={"footnote_cn_count": cn_count})
        updates["FR-4.10-03"] = RuleUpdate(status=en_status, evidence=footnote_evidence, details={"footnote_en_count": en_count})
        updates["FR-4.10-04"] = RuleUpdate(
            status=spacing_status,
            evidence=footnote_evidence,
            details={"footnote_total": cn_count + en_count},
        )

    return updates, changed


def _fix_and_check_references(
    root: ET.Element,
    *,
    apply_fixes: bool,
    current_year: int,
) -> tuple[dict[str, RuleUpdate], bool]:
    changed = False
    body_paragraphs = root.findall(".//w:body/w:p", NS)
    heading_index = _find_references_heading_index(body_paragraphs)

    if heading_index is None:
        updates = {
            "FR-4.11-02": RuleUpdate(status="detected_not_modified", evidence=(), details={"issue": "references_heading_not_found"}),
            "FR-4.11-03": RuleUpdate(status="detected_not_modified", evidence=(), details={"issue": "references_heading_not_found"}),
            "FR-4.11-07": RuleUpdate(status="detected_not_modified", evidence=(), details={"issue": "references_heading_not_found"}),
            "FR-4.11-04": RuleUpdate(status="detected_not_modified", evidence=(), details={"issue": "references_heading_not_found"}),
            "FR-4.11-05": RuleUpdate(status="detected_not_modified", evidence=(), details={"issue": "references_heading_not_found"}),
            "FR-4.11-06": RuleUpdate(status="detected_not_modified", evidence=(), details={"issue": "references_heading_not_found"}),
        }
        return updates, changed

    entries, skipped_indices = _collect_reference_entries(body_paragraphs, heading_index)
    evidence = (
        Evidence(paragraph_index=heading_index, snippet="REFERENCES", reason="references_heading_found"),
    )

    if not entries:
        updates = {
            "FR-4.11-02": RuleUpdate(status="not_applicable", evidence=evidence, details={"entries": 0}),
            "FR-4.11-03": RuleUpdate(status="detected_not_modified", evidence=evidence, details={"issue": "reference_entries_not_found"}),
            "FR-4.11-07": RuleUpdate(status="not_applicable", evidence=evidence, details={"entries": 0}),
            "FR-4.11-04": RuleUpdate(status="not_applicable", evidence=evidence, details={"entries": 0}),
            "FR-4.11-05": RuleUpdate(status="not_applicable", evidence=evidence, details={"entries": 0}),
            "FR-4.11-06": RuleUpdate(status="not_applicable", evidence=evidence, details={"entries": 0}),
        }
        return updates, changed

    changed_entries = 0
    d_type_page_violation_count = 0
    d_type_page_fixed_count = 0
    d_type_page_skipped_count = 0
    for entry in entries:
        entry_changed = False
        has_d_pages, normalized_entry_text = _strip_d_type_pages(entry.text)
        if has_d_pages:
            d_type_page_violation_count += 1
            if apply_fixes and len(entry.paragraphs) == 1 and normalized_entry_text and normalized_entry_text != entry.text:
                if _replace_paragraph_text(entry.paragraphs[0], normalized_entry_text):
                    entry_changed = True
                    d_type_page_fixed_count += 1
            else:
                d_type_page_skipped_count += 1
        for paragraph in entry.paragraphs:
            if apply_fixes and _set_paragraph_spacing(paragraph, line=LINE_25PT_TWIPS, line_rule="exact"):
                entry_changed = True
            for run in paragraph.findall("w:r", NS):
                if apply_fixes and _set_run_font_and_size(run, font_name=FONT_TNR, half_points=SMALL_FOUR_HALF_PT):
                    entry_changed = True
        if entry_changed:
            changed = True
            changed_entries += 1

    entry_texts = [entry.text for entry in entries]
    language_sequence = [_lang_bucket(text) for text in entry_texts]
    english_count = sum(1 for bucket in language_sequence if bucket == "en")
    years = [_extract_year(text) for text in entry_texts]
    valid_years = [year for year in years if year is not None]
    recent_threshold = current_year - 2
    recent_count = sum(1 for year in valid_years if year >= recent_threshold)

    sequence_ok = _index_sequence_ok(entries)
    language_order_ok = _english_first_then_chinese(language_sequence)
    recency_ok = bool(valid_years) and recent_count * 2 >= len(valid_years)
    rough_format_ok, invalid_examples = _rough_reference_format_check(entry_texts)
    numbered_entry_count = sum(1 for entry in entries if entry.source == "numbered_entry")
    author_leading_entry_count = sum(1 for entry in entries if entry.source == "author_leading_fallback")

    updates = {
        "FR-4.11-02": RuleUpdate(
            status="fixed" if (apply_fixes and changed) else "checked_ok",
            evidence=evidence,
            details={
                "entry_count": len(entries),
                "reference_entry_total": len(entries),
                "numbered_reference_entry_count": numbered_entry_count,
                "author_leading_reference_entry_count": author_leading_entry_count,
                "entry_paragraph_count": sum(len(entry.paragraphs) for entry in entries),
                "fixed_entry_count": changed_entries if apply_fixes else 0,
                "skipped_paragraph_count": len(skipped_indices),
                "skipped_paragraph_indices": skipped_indices,
            },
        ),
        "FR-4.11-03": RuleUpdate(
            status="checked_ok" if rough_format_ok and sequence_ok else "detected_not_modified",
            evidence=evidence,
            details={
                "issue": None if rough_format_ok and sequence_ok else "structure_or_sequence_issue",
                "sequence_ok": sequence_ok,
                "rough_format_ok": rough_format_ok,
                "invalid_examples": invalid_examples,
            },
        ),
        "FR-4.11-07": RuleUpdate(
            status=(
                "fixed"
                if apply_fixes and d_type_page_violation_count > 0 and d_type_page_skipped_count == 0
                else ("checked_ok" if d_type_page_violation_count == 0 else "detected_not_modified")
            ),
            evidence=evidence,
            details={
                "issue": None
                if d_type_page_violation_count == 0 or (apply_fixes and d_type_page_skipped_count == 0)
                else "d_type_pages_present",
                "d_type_page_violation_count": d_type_page_violation_count,
                "d_type_page_fixed_count": d_type_page_fixed_count,
                "d_type_page_skipped_count": d_type_page_skipped_count,
            },
        ),
        "FR-4.11-04": RuleUpdate(
            status="checked_ok" if (language_order_ok and english_count >= 5) else "detected_not_modified",
            evidence=evidence,
            details={
                "issue": None if (language_order_ok and english_count >= 5) else "language_grouping_or_english_count",
                "english_count": english_count,
                "language_order_ok": language_order_ok,
            },
        ),
        "FR-4.11-05": RuleUpdate(
            status="checked_ok" if recency_ok else "detected_not_modified",
            evidence=evidence,
            details={
                "issue": None if recency_ok else "recent_years_not_majority",
                "recent_threshold": recent_threshold,
                "recent_count": recent_count,
                "valid_year_count": len(valid_years),
            },
        ),
        "FR-4.11-06": RuleUpdate(
            status="checked_ok" if sequence_ok else "detected_not_modified",
            evidence=evidence,
            details={"issue": None if sequence_ok else "publish_order_or_index_issue"},
        ),
    }
    return updates, changed


def _find_references_heading_index(paragraphs: list[ET.Element]) -> int | None:
    for idx, paragraph in enumerate(paragraphs):
        if _paragraph_text(paragraph).strip().upper() == "REFERENCES":
            return idx
    return None


def _collect_reference_entries(
    paragraphs: list[ET.Element],
    heading_index: int,
) -> tuple[list[_ReferenceEntry], list[int]]:
    entries: list[_ReferenceEntry] = []
    skipped: list[int] = []
    current_index = 0
    current_source = "numbered_entry"
    current_paragraphs: list[ET.Element] = []
    current_texts: list[str] = []
    pre_entry_noise = 0
    blank_noise = 0

    def flush() -> None:
        nonlocal current_index, current_source, current_paragraphs, current_texts
        if not current_paragraphs:
            return
        entries.append(
            _ReferenceEntry(
                start_index=current_index,
                paragraphs=tuple(current_paragraphs),
                text=" ".join(current_texts).strip(),
                index_value=current_index if current_source == "numbered_entry" else None,
                source=current_source,
            )
        )
        current_paragraphs = []
        current_texts = []
        current_source = "numbered_entry"

    for idx in range(heading_index + 1, len(paragraphs)):
        text = _paragraph_text(paragraphs[idx]).strip()
        if not text:
            if current_paragraphs:
                blank_noise += 1
                if blank_noise > 1:
                    break
            continue

        blank_noise = 0
        if _is_reference_stop_heading(text):
            break

        matched = REFERENCE_ENTRY_STRONG_RE.match(text)
        if matched:
            flush()
            current_index = int(matched.group(1))
            current_source = "numbered_entry"
            current_paragraphs = [paragraphs[idx]]
            current_texts = [text]
            continue

        if _looks_like_author_leading_entry_start(text):
            flush()
            current_index = len(entries) + 1
            current_source = "author_leading_fallback"
            current_paragraphs = [paragraphs[idx]]
            current_texts = [text]
            continue

        if not entries and not current_paragraphs:
            skipped.append(idx)
            pre_entry_noise += 1
            if _looks_like_new_section_heading(text) or pre_entry_noise > 2:
                break
            continue

        if _looks_like_new_section_heading(text):
            break

        if current_paragraphs and _looks_like_reference_continuation_line(text):
            current_paragraphs.append(paragraphs[idx])
            current_texts.append(text)
            continue

        if current_paragraphs:
            flush()
            skipped.append(idx)
            pre_entry_noise = 1
            continue

        current_paragraphs.append(paragraphs[idx])
        current_texts.append(text)

    flush()
    return entries, skipped


def _index_sequence_ok(entries: list[_ReferenceEntry]) -> bool:
    expected = 1
    for entry in entries:
        if entry.source != "numbered_entry":
            return False
        if entry.index_value != expected:
            return False
        expected += 1
    return True


def _is_reference_stop_heading(text: str) -> bool:
    lowered = text.strip().casefold()
    return lowered in {
        "致谢",
        "acknowledgements",
        "acknowledgments",
        "appendix",
        "appendices",
        "附录",
        "contents",
        "目录",
        "abstract",
        "摘 要",
        "摘要",
        "references",
        "参考文献",
    }


def _looks_like_new_section_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _is_reference_stop_heading(stripped):
        return True
    if re.match(r"^\d+(?:\.\d+){0,2}\s+\S+", stripped):
        return True
    if re.match(r"^[A-Z][A-Z\s]{2,30}$", stripped):
        return len([item for item in stripped.split() if item]) <= 4
    return False


def _looks_like_author_leading_entry_start(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if REFERENCE_ENTRY_STRONG_RE.match(stripped):
        return False
    if _looks_like_new_section_heading(stripped):
        return False
    if SENTENCE_LIKE_EN_RE.match(stripped):
        return False
    first_word_match = re.match(r"^([A-Za-z]+)", stripped)
    if first_word_match is not None and first_word_match.group(1).casefold() in AUTHOR_LEADING_EN_EXCLUDE_PREFIXES:
        return False
    if AUTHOR_ENTRY_EN_RE.match(stripped):
        return True
    if AUTHOR_ENTRY_ZH_RE.match(stripped):
        return True
    return False


def _looks_like_reference_continuation_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _looks_like_new_section_heading(stripped):
        return False
    if REFERENCE_CONTINUATION_HINT_RE.match(stripped):
        return True
    lowered = stripped.casefold()
    if any(keyword in lowered for keyword in REFERENCE_CONTINUATION_KEYWORDS):
        return True
    if stripped[:1].islower():
        return True
    return False


def _english_first_then_chinese(language_sequence: list[str]) -> bool:
    seen_chinese = False
    for bucket in language_sequence:
        if bucket == "zh":
            seen_chinese = True
            continue
        if bucket == "en" and seen_chinese:
            return False
    return True


def _rough_reference_format_check(texts: list[str]) -> tuple[bool, list[str]]:
    invalid: list[str] = []
    for text in texts:
        lowered = text.lower()
        has_year = _extract_year(text) is not None
        looks_journal = bool(re.search(r"\b\d{4}\b", text) and re.search(r"[\.,:]", text))
        looks_book = "press" in lowered or "出版社" in text
        looks_thesis = "thesis" in lowered or "dissertation" in lowered or "学位论文" in text
        looks_report = "report" in lowered or "报告" in text
        if not has_year or not (looks_journal or looks_book or looks_thesis or looks_report):
            invalid.append(text[:120])
    return len(invalid) == 0, invalid


def _extract_year(text: str) -> int | None:
    years = [int(item) for item in re.findall(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", text)]
    if not years:
        return None
    return max(years)


def _lang_bucket(text: str) -> str:
    return "zh" if _contains_cjk(text) else "en"


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _paragraph_text(paragraph: ET.Element) -> str:
    return "".join((node.text or "") for node in paragraph.findall(".//w:t", NS))


def _set_run_font_and_size(run: ET.Element, *, font_name: str, half_points: str) -> bool:
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

    return changed


def _set_paragraph_spacing(paragraph: ET.Element, *, line: str, line_rule: str) -> bool:
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
    return changed


def _set_attr(node: ET.Element, name: str, value: str) -> bool:
    if node.get(name) == value:
        return False
    node.set(name, value)
    return True


def _replace_paragraph_text(paragraph: ET.Element, new_text: str) -> bool:
    if _paragraph_text(paragraph) == new_text:
        return False
    for run in list(paragraph.findall("w:r", NS)):
        paragraph.remove(run)
    run = ET.SubElement(paragraph, f"{{{W_NS}}}r")
    text_node = ET.SubElement(run, f"{{{W_NS}}}t")
    if new_text[:1].isspace() or new_text[-1:].isspace():
        text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_node.text = new_text
    return True


def _strip_d_type_pages(text: str) -> tuple[bool, str]:
    if "[D" not in text.upper():
        return False, text
    updated = text
    for pattern in (
        r"([,，:：]\s*)\d+\s*[-–—]\s*\d+\s*(?=[\.\。]|$)",
        r"\bpp?\.?\s*\d+\s*[-–—]\s*\d+\s*(?=[\.\。]|$)",
    ):
        updated = re.sub(pattern, "", updated, flags=re.IGNORECASE)
    updated = re.sub(r"\s{2,}", " ", updated).strip()
    updated = re.sub(r"[，,]\s*(?=[\.\。]|$)", "", updated)
    return updated != text, updated
