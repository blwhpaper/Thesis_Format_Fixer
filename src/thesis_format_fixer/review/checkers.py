"""Rule-engine review checkers for TASK-007."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

from thesis_format_fixer.contracts.review_types import ReviewDecision, ReviewEvidence, ReviewFinding
from thesis_format_fixer.detectors.block_locator import BlockMap
from thesis_format_fixer.io.document_loader import DocumentContext

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


_HEADING_PATTERN = re.compile(r"^\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?\s+")
_REFERENCE_ENTRY_PATTERN = re.compile(r"^\[(\d+)\]\s+")


def heading_structure_review(context: DocumentContext, block_map: BlockMap) -> tuple[ReviewFinding, ...]:
    paragraphs = context.paragraphs
    if not paragraphs:
        return (
            ReviewFinding(
                rule_id="FR-4.8-01",
                block_id="body",
                block_type="body.headings",
                target="heading_structure",
                decision=ReviewDecision.UNABLE_TO_JUDGE,
                confidence=0.05,
                evidence=(ReviewEvidence(reason="paragraphs_empty"),),
                suggestion="正文段落为空，需人工复核标题层级。",
            ),
        )

    body_start = 0
    contents = block_map.blocks.get("contents")
    if contents and contents.start_paragraph is not None:
        body_start = max(body_start, contents.start_paragraph + 1)

    references = block_map.blocks.get("references")
    body_end = len(paragraphs)
    if references and references.start_paragraph is not None:
        body_end = min(body_end, references.start_paragraph)

    candidates: list[tuple[int, str, tuple[int, ...]]] = []
    ambiguous: list[tuple[int, str]] = []
    for idx in range(body_start, body_end):
        text = paragraphs[idx].strip()
        if not text:
            continue
        matched = _HEADING_PATTERN.match(text)
        if matched:
            levels = tuple(int(item) for item in matched.groups() if item is not None)
            if 1 <= len(levels) <= 3:
                candidates.append((idx, text, levels))
                continue
        if re.match(r"^\s*\d+(?:\.\d+){0,3}\s*$", text):
            ambiguous.append((idx, text))

    if not candidates:
        return (
            ReviewFinding(
                rule_id="FR-4.8-01",
                block_id="body",
                block_type="body.headings",
                target="heading_structure",
                decision=ReviewDecision.UNABLE_TO_JUDGE,
                confidence=0.25,
                evidence=(ReviewEvidence(reason="heading_candidates_not_found"),),
                suggestion="未识别到稳定标题序号，建议人工核对。",
            ),
        )

    sequence_issue = _detect_heading_sequence_issue(candidates)
    if sequence_issue is not None:
        idx, text, reason = sequence_issue
        return (
            ReviewFinding(
                rule_id="FR-4.8-01",
                block_id="body",
                block_type="body.headings",
                target="heading_structure",
                decision=ReviewDecision.FAIL,
                confidence=0.88,
                evidence=(ReviewEvidence(reason=reason, snippet=text, paragraph_index=idx),),
                suggestion="标题层级疑似混乱，请人工确认序号是否按 1/1.1/1.1.1 递进。",
            ),
        )

    findings: list[ReviewFinding] = []
    if ambiguous:
        idx, text = ambiguous[0]
        findings.append(
            ReviewFinding(
                rule_id="FR-4.8-01",
                block_id="body",
                block_type="body.headings",
                target="heading_structure",
                decision=ReviewDecision.WARN,
                confidence=0.52,
                evidence=(ReviewEvidence(reason="ambiguous_heading_token", snippet=text, paragraph_index=idx),),
                suggestion="存在无法稳定判断的标题行，建议人工复核。",
            )
        )

    findings.append(
        ReviewFinding(
            rule_id="FR-4.8-01",
            block_id="body",
            block_type="body.headings",
            target="heading_structure",
            decision=ReviewDecision.PASS,
            confidence=0.84,
            evidence=(ReviewEvidence(reason="heading_sequence_looks_valid", snippet=f"count={len(candidates)}"),),
            suggestion="标题层级整体看起来正常。",
        )
    )
    return tuple(findings)


def reference_structure_review(context: DocumentContext, block_map: BlockMap) -> tuple[ReviewFinding, ...]:
    paragraphs = context.paragraphs
    ref_block = block_map.blocks.get("references")
    if ref_block is None or ref_block.start_paragraph is None:
        return (
            ReviewFinding(
                rule_id="FR-4.11-03",
                block_id="references",
                block_type="bibliography.entries",
                target="reference_structure",
                decision=ReviewDecision.UNABLE_TO_JUDGE,
                confidence=0.2,
                evidence=(ReviewEvidence(reason="references_block_not_found"),),
                suggestion="未定位到 REFERENCES 区块，需人工复核。",
            ),
        )

    entries: list[tuple[int, str, int | None]] = []
    for idx in range(ref_block.start_paragraph + 1, len(paragraphs)):
        text = paragraphs[idx].strip()
        if not text:
            if entries:
                break
            continue
        matched = _REFERENCE_ENTRY_PATTERN.match(text)
        if not matched:
            if entries:
                break
            continue
        entries.append((idx, text, int(matched.group(1))))

    if not entries:
        return (
            ReviewFinding(
                rule_id="FR-4.11-03",
                block_id="references",
                block_type="bibliography.entries",
                target="reference_structure",
                decision=ReviewDecision.FAIL,
                confidence=0.86,
                evidence=(ReviewEvidence(reason="reference_numbering_missing"),),
                suggestion="参考文献疑似缺少 [1][2] 编号结构。",
            ),
        )

    findings: list[ReviewFinding] = []

    sequence_ok = all(item[2] == idx + 1 for idx, item in enumerate(entries) if item[2] is not None)
    rough_ok, invalid_example = _reference_rough_format(entries)
    language_order_ok, english_count = _reference_language_order(entries)

    if not sequence_ok or not rough_ok:
        detail = "reference_sequence_issue" if not sequence_ok else "reference_rough_format_issue"
        snippet = invalid_example or entries[0][1]
        findings.append(
            ReviewFinding(
                rule_id="FR-4.11-03",
                block_id="references",
                block_type="bibliography.entries",
                target="reference_structure",
                decision=ReviewDecision.WARN,
                confidence=0.74,
                evidence=(ReviewEvidence(reason=detail, snippet=snippet),),
                suggestion="部分条目结构疑似不符合期刊/专著/学位论文基础格式，请人工复核。",
            )
        )
    else:
        findings.append(
            ReviewFinding(
                rule_id="FR-4.11-03",
                block_id="references",
                block_type="bibliography.entries",
                target="reference_structure",
                decision=ReviewDecision.PASS,
                confidence=0.81,
                evidence=(ReviewEvidence(reason="reference_sequence_and_rough_format_ok", snippet=f"entries={len(entries)}"),),
                suggestion="参考文献基础结构未见明显异常。",
            )
        )

    if not language_order_ok or english_count < 5:
        findings.append(
            ReviewFinding(
                rule_id="FR-4.11-04",
                block_id="references",
                block_type="bibliography.entries",
                target="reference_language_grouping",
                decision=ReviewDecision.WARN,
                confidence=0.63,
                evidence=(
                    ReviewEvidence(
                        reason="english_grouping_or_count_suspect",
                        snippet=f"english_count={english_count}, language_order_ok={language_order_ok}",
                    ),
                ),
                suggestion="英文文献数量或中英文分组顺序存在疑点，建议人工复核。",
            )
        )
    else:
        findings.append(
            ReviewFinding(
                rule_id="FR-4.11-04",
                block_id="references",
                block_type="bibliography.entries",
                target="reference_language_grouping",
                decision=ReviewDecision.PASS,
                confidence=0.75,
                evidence=(ReviewEvidence(reason="language_grouping_looks_ok", snippet=f"english_count={english_count}"),),
                suggestion="中英文文献分组与英文数量未见明显异常。",
            )
        )

    return tuple(findings)


def pagination_review(context: DocumentContext, block_map: BlockMap) -> tuple[ReviewFinding, ...]:
    path = context.source_path
    if path.suffix.lower() != ".docx" or not path.exists():
        return (
            ReviewFinding(
                rule_id="FR-4.15-01",
                block_id="pagination",
                block_type="page.numbering",
                target="pagination",
                decision=ReviewDecision.UNABLE_TO_JUDGE,
                confidence=0.1,
                evidence=(ReviewEvidence(reason="docx_not_available"),),
                suggestion="缺少可读 docx 证据，无法判断页码起始。",
            ),
        )

    try:
        with ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            document_xml = archive.read("word/document.xml") if "word/document.xml" in names else b""
            footer_names = sorted(name for name in names if name.startswith("word/footer") and name.endswith(".xml"))
            footers = [archive.read(name) for name in footer_names]
    except (BadZipFile, OSError, KeyError):
        return (
            ReviewFinding(
                rule_id="FR-4.15-01",
                block_id="pagination",
                block_type="page.numbering",
                target="pagination",
                decision=ReviewDecision.UNABLE_TO_JUDGE,
                confidence=0.12,
                evidence=(ReviewEvidence(reason="docx_read_error"),),
                suggestion="页码相关部件读取失败，建议人工复核。",
            ),
        )

    if not document_xml or not footers:
        return (
            ReviewFinding(
                rule_id="FR-4.15-01",
                block_id="pagination",
                block_type="page.numbering",
                target="pagination",
                decision=ReviewDecision.UNABLE_TO_JUDGE,
                confidence=0.28,
                evidence=(ReviewEvidence(reason="footer_or_document_part_missing"),),
                suggestion="缺少页脚或正文 XML，无法稳定判断页码规则。",
            ),
        )

    footer_text = " ".join(_extract_text_from_xml(raw) for raw in footers)
    has_dash_style = bool(re.search(r"-\s*\d+\s*-", footer_text))
    has_numeric_page = bool(re.search(r"\d+", footer_text))

    findings: list[ReviewFinding] = []

    if not has_numeric_page:
        findings.append(
            ReviewFinding(
                rule_id="FR-4.15-01",
                block_id="pagination",
                block_type="page.numbering",
                target="page_number_start",
                decision=ReviewDecision.UNABLE_TO_JUDGE,
                confidence=0.31,
                evidence=(ReviewEvidence(reason="page_number_not_detected_in_footer"),),
                suggestion="未检测到页码文本，无法判断是否从正文开始。",
            )
        )
    else:
        findings.append(
            ReviewFinding(
                rule_id="FR-4.15-01",
                block_id="pagination",
                block_type="page.numbering",
                target="page_number_start",
                decision=ReviewDecision.WARN,
                confidence=0.55,
                evidence=(ReviewEvidence(reason="page_number_detected_but_body_link_uncertain"),),
                suggestion="检测到页码信号，但正文起始分节证据不足，需人工确认。",
            )
        )

    findings.append(
        ReviewFinding(
            rule_id="FR-4.15-03",
            block_id="pagination",
            block_type="page.numbering",
            target="page_number_format",
            decision=ReviewDecision.PASS if has_dash_style else ReviewDecision.WARN,
            confidence=0.77 if has_dash_style else 0.66,
            evidence=(
                ReviewEvidence(
                    reason="page_number_dash_style_detected" if has_dash_style else "page_number_dash_style_not_detected",
                    snippet=footer_text[:120],
                ),
            ),
            suggestion="页码样式建议为 -1-，请人工确认页脚显示格式。" if not has_dash_style else "页码样式疑似符合 -1-。",
        )
    )

    return tuple(findings)


def _detect_heading_sequence_issue(
    candidates: list[tuple[int, str, tuple[int, ...]]],
) -> tuple[int, str, str] | None:
    previous: tuple[int, ...] | None = None
    for idx, text, levels in candidates:
        if previous is None:
            previous = levels
            continue

        if len(levels) > len(previous) + 1:
            return idx, text, "heading_depth_jump"

        if len(levels) == len(previous):
            if levels[:-1] != previous[:-1] or levels[-1] <= previous[-1]:
                return idx, text, "heading_same_level_sequence_invalid"

        if len(levels) < len(previous):
            if len(levels) == 1:
                if levels[0] <= previous[0]:
                    return idx, text, "heading_h1_sequence_invalid"
            else:
                if levels[:-1] != previous[: len(levels) - 1] and levels[-1] != 1:
                    return idx, text, "heading_parent_mismatch"

        if len(levels) == len(previous) + 1:
            if levels[-1] != 1:
                return idx, text, "heading_child_not_start_from_one"

        previous = levels
    return None


def _reference_rough_format(entries: list[tuple[int, str, int | None]]) -> tuple[bool, str]:
    for _, text, _ in entries:
        has_year = bool(re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", text))
        lowered = text.lower()
        looks_kind = any(
            token in lowered
            for token in ("journal", "press", "thesis", "dissertation", "report", "出版社", "学位论文", "报告")
        )
        if not has_year or not looks_kind:
            return False, text
    return True, ""


def _reference_language_order(entries: list[tuple[int, str, int | None]]) -> tuple[bool, int]:
    sequence: list[str] = []
    for _, text, _ in entries:
        sequence.append("zh" if _contains_cjk(text) else "en")

    english_count = sum(1 for item in sequence if item == "en")
    seen_zh = False
    for item in sequence:
        if item == "zh":
            seen_zh = True
            continue
        if item == "en" and seen_zh:
            return False, english_count
    return True, english_count


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _extract_text_from_xml(raw: bytes) -> str:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return ""
    chunks: list[str] = []
    for node in root.findall(".//w:t", NS):
        chunks.append(node.text or "")
    return "".join(chunks).strip()
