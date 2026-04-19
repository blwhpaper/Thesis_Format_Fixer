"""Reference-entry and reference-collection rule checkers for TASK-018."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import re

from thesis_format_fixer.contracts.report_types import ReferenceCheckFinding, ReferenceCheckResult
from thesis_format_fixer.detectors.reference_parser import ReferenceEntryParse


_ALLOWED_TYPE_CODES = {"M", "C", "N", "J", "D", "R", "S", "P", "DB", "CP", "EB"}
_ALLOWED_CARRIERS = {"OL", "MT", "DK", "CD"}
_CARRIER_COMPATIBLE_TYPES = {"J", "DB", "CP", "EB"}
_ELECTRONIC_TYPES = {"DB", "CP", "EB"}

_TYPE_MARKER_RE = re.compile(r"\[(?P<base>[A-Z]{1,3})(?:/(?P<carrier>[A-Z]{1,3}))?\]")
_PAGE_RANGE_RE = re.compile(r"\d+\s*[-–—]\s*\d+")
_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_PLACE_PUBLISHER_RE = re.compile(r"[^,:，：]{1,40}\s*[:：]\s*[^,，]{1,80}")
_ISSUE_RE = re.compile(r"(?:\(|（)\s*[^)）]+\s*(?:\)|）)")
_DOUBLE_PUNCT_RE = re.compile(r"([,，.:：;；])\1+")


def run_reference_checks(entries: tuple[ReferenceEntryParse, ...], *, current_year: int | None = None) -> ReferenceCheckResult:
    _ = current_year

    entry_findings: list[ReferenceCheckFinding] = []
    collection_findings: list[ReferenceCheckFinding] = []

    language_buckets: list[str] = []
    english_count = 0
    chinese_count = 0
    unknown_count = 0

    for entry_index, entry in enumerate(entries):
        bucket = _language_bucket(entry)
        language_buckets.append(bucket)
        if bucket == "en":
            english_count += 1
        elif bucket == "zh":
            chinese_count += 1
        else:
            unknown_count += 1

        entry_findings.extend(_entry_level_checks(entry, entry_index, bucket=bucket))

    collection_findings.extend(
        _collection_level_checks(
            entries,
            language_buckets=tuple(language_buckets),
            english_count=english_count,
        )
    )

    findings = [*entry_findings, *collection_findings]
    rule_counts = Counter(item.rule_id for item in findings)
    error_count = sum(1 for item in findings if item.severity == "error")
    warning_count = sum(1 for item in findings if item.severity == "warning")

    return ReferenceCheckResult(
        findings=tuple(findings),
        entry_findings=tuple(entry_findings),
        collection_findings=tuple(collection_findings),
        english_count=english_count,
        chinese_count=chinese_count,
        unknown_count=unknown_count,
        rule_counts=dict(sorted(rule_counts.items())),
        error_count=error_count,
        warning_count=warning_count,
    )


def _entry_level_checks(entry: ReferenceEntryParse, entry_index: int, *, bucket: str) -> list[ReferenceCheckFinding]:
    findings: list[ReferenceCheckFinding] = []
    raw = entry.normalized_text

    marker = _TYPE_MARKER_RE.search(raw)
    marker_base = marker.group("base") if marker else None
    marker_carrier = marker.group("carrier") if marker else None

    if marker is None:
        findings.append(
            _finding(
                rule_id="FR-4.11-03",
                finding_code="reference_type_marker_missing",
                severity="error",
                entry=entry,
                entry_index=entry_index,
                reason="条目缺少文献类型标识（如 [J]/[M]/[D]/[EB/OL]）。",
                expected_pattern="[序号] 作者. 题名[类型]. ...",
            )
        )
    else:
        if marker_base not in _ALLOWED_TYPE_CODES:
            findings.append(
                _finding(
                    rule_id="FR-4.11-03",
                    finding_code="reference_type_marker_invalid",
                    severity="error",
                    entry=entry,
                    entry_index=entry_index,
                    reason=f"文献类型标识不在允许集合内：[{marker_base}]。",
                    expected_pattern="允许类型：M/C/N/J/D/R/S/P/DB/CP/EB（可带 /OL 等载体）。",
                )
            )

        if marker_carrier is not None:
            if marker_carrier not in _ALLOWED_CARRIERS:
                findings.append(
                    _finding(
                        rule_id="FR-4.11-03",
                        finding_code="reference_type_carrier_invalid",
                        severity="error",
                        entry=entry,
                        entry_index=entry_index,
                        reason=f"载体标识不合法：/{marker_carrier}。",
                        expected_pattern="允许载体：/OL /MT /DK /CD。",
                    )
                )
            elif marker_base not in _CARRIER_COMPATIBLE_TYPES:
                findings.append(
                    _finding(
                        rule_id="FR-4.11-03",
                        finding_code="reference_type_carrier_invalid",
                        severity="error",
                        entry=entry,
                        entry_index=entry_index,
                        reason=f"[{marker_base}] 不应携带 /{marker_carrier} 载体标识。",
                        expected_pattern="载体组合通常用于 J/DB/CP/EB 等类型。",
                    )
                )

    if marker_base == "J":
        if not _is_valid_journal_structure(entry):
            findings.append(
                _finding(
                    rule_id="FR-4.11-03",
                    finding_code="reference_journal_structure_invalid",
                    severity="error",
                    entry=entry,
                    entry_index=entry_index,
                    reason="J 类条目未满足期刊结构字段要求。",
                    expected_pattern="作者. 题目[J]. 期刊名, 年份(期数): 页码.",
                )
            )

    if marker_base in {"M", "R"}:
        if not _is_valid_bookish_structure(entry, require_pages=True):
            findings.append(
                _finding(
                    rule_id="FR-4.11-03",
                    finding_code="reference_book_structure_invalid",
                    severity="error",
                    entry=entry,
                    entry_index=entry_index,
                    reason=f"{marker_base} 类条目字段不完整或顺序异常。",
                    expected_pattern="作者. 书名或题名[类型]. 版次. 出版地: 出版单位, 年份, 页码.",
                )
            )

    if marker_base == "D":
        if not _is_valid_bookish_structure(entry, require_pages=False):
            findings.append(
                _finding(
                    rule_id="FR-4.11-03",
                    finding_code="reference_thesis_structure_invalid",
                    severity="error",
                    entry=entry,
                    entry_index=entry_index,
                    reason="D 类条目字段不完整或顺序异常。",
                    expected_pattern="作者. 题名[D]. 出版地: 授予单位, 年份.",
                )
            )
        if entry.pages is not None or _PAGE_RANGE_RE.search(raw):
            findings.append(
                _finding(
                    rule_id="FR-4.11-07",
                    finding_code="reference_d_thesis_has_page_range",
                    severity="error",
                    entry=entry,
                    entry_index=entry_index,
                    reason="D 类学位论文条目不允许出现页码区间。",
                    expected_pattern="D 类条目应去除页码字段。",
                )
            )

    if _is_electronic_entry(marker_base, entry):
        if not _is_valid_eb_ol_structure(entry, marker_base=marker_base, marker_carrier=marker_carrier):
            findings.append(
                _finding(
                    rule_id="FR-4.11-03",
                    finding_code="reference_eb_ol_structure_invalid",
                    severity="error",
                    entry=entry,
                    entry_index=entry_index,
                    reason="电子文献条目结构不完整（类型/载体/年份/定位信息）。",
                    expected_pattern="作者. 题名[EB/OL]. 来源, 年份. URL/DOI",
                )
            )

    if bucket == "en" and ("《" in raw or "》" in raw):
        findings.append(
            _finding(
                rule_id="FR-4.5-06",
                finding_code="reference_english_contains_cn_book_title_marks",
                severity="warning",
                entry=entry,
                entry_index=entry_index,
                reason="英文条目出现中文书名号《》。",
                expected_pattern="英文条目中不要使用《》，使用英文引号或斜体表达书名。",
            )
        )

    punctuation_reason = _punctuation_violation_reason(entry)
    if punctuation_reason:
        findings.append(
            _finding(
                rule_id="FR-4.11-03",
                finding_code="reference_punctuation_invalid",
                severity="warning",
                entry=entry,
                entry_index=entry_index,
                reason=punctuation_reason,
                expected_pattern="条目建议以句点结尾，避免重复标点。",
            )
        )

    field_order_reason = _field_order_violation_reason(entry, marker_base=marker_base)
    if field_order_reason:
        findings.append(
            _finding(
                rule_id="FR-4.11-03",
                finding_code="reference_field_order_invalid",
                severity="warning",
                entry=entry,
                entry_index=entry_index,
                reason=field_order_reason,
                expected_pattern="类型标识应在题名后，年份应在来源字段后，页码通常在年份后。",
            )
        )

    return findings


def _collection_level_checks(
    entries: tuple[ReferenceEntryParse, ...],
    *,
    language_buckets: tuple[str, ...],
    english_count: int,
) -> list[ReferenceCheckFinding]:
    if not entries:
        return []

    findings: list[ReferenceCheckFinding] = []

    if english_count < 5:
        findings.append(
            _finding_for_collection(
                rule_id="FR-4.11-04",
                finding_code="reference_english_count_insufficient",
                severity="warning",
                reason=f"英文参考文献数量不足：当前 {english_count} 篇，要求不少于 5 篇。",
                expected_pattern="英文文献不少于 5 篇。",
                evidence={"english_count": english_count, "required_min": 5},
            )
        )

    order_ok, violation_index = _check_language_order(language_buckets)
    if not order_ok:
        offending = entries[violation_index] if violation_index is not None else entries[0]
        findings.append(
            _finding_for_collection(
                rule_id="FR-4.11-04",
                finding_code="reference_language_order_invalid",
                severity="warning",
                reason="参考文献未满足“英文在前、中文在后”的分组顺序。",
                expected_pattern="先英文条目，再中文条目。",
                reference_index=_reference_index(offending, violation_index or 0),
                reference_text=offending.raw_text,
                entry_index=violation_index,
                evidence={"violation_entry_index": violation_index},
            )
        )

    return findings


def _is_valid_journal_structure(entry: ReferenceEntryParse) -> bool:
    if not entry.authors or not entry.title:
        return False
    if not entry.container_or_source or not entry.year or not entry.pages:
        return False
    if not entry.issue:
        return False
    return True


def _is_valid_bookish_structure(entry: ReferenceEntryParse, *, require_pages: bool) -> bool:
    if not entry.authors or not entry.title or not entry.year:
        return False
    if not entry.publication_place and not entry.publisher and not entry.degree_grantor:
        return False
    if require_pages and not entry.pages:
        return False
    return True


def _is_electronic_entry(marker_base: str | None, entry: ReferenceEntryParse) -> bool:
    return marker_base in _ELECTRONIC_TYPES or entry.medium_code is not None or entry.entry_type == "electronic"


def _is_valid_eb_ol_structure(
    entry: ReferenceEntryParse,
    *,
    marker_base: str | None,
    marker_carrier: str | None,
) -> bool:
    if marker_base in _ELECTRONIC_TYPES and marker_carrier is None:
        return False
    if marker_carrier is not None and marker_carrier not in _ALLOWED_CARRIERS:
        return False
    if not entry.year:
        return False
    if not entry.url_or_locator:
        return False
    return True


def _punctuation_violation_reason(entry: ReferenceEntryParse) -> str | None:
    raw = entry.normalized_text.strip()
    if not raw:
        return None
    if _DOUBLE_PUNCT_RE.search(raw):
        return "条目中存在重复标点。"
    if not raw.endswith((".", "。")):
        return "条目末尾缺少结束句点。"
    return None


def _field_order_violation_reason(entry: ReferenceEntryParse, *, marker_base: str | None) -> str | None:
    raw = entry.normalized_text
    marker = _TYPE_MARKER_RE.search(raw)
    if marker is None:
        return None

    marker_pos = marker.start()
    year_match = _YEAR_RE.search(raw)
    page_match = _PAGE_RANGE_RE.search(raw)
    place_publisher_match = _PLACE_PUBLISHER_RE.search(raw)

    if year_match is not None and year_match.start() < marker_pos:
        return "年份字段出现在类型标识之前。"

    if page_match is not None and year_match is not None and page_match.start() < year_match.start():
        return "页码字段出现在年份之前。"

    if marker_base == "J":
        issue_match = _ISSUE_RE.search(raw)
        if issue_match is not None and year_match is not None and issue_match.start() < year_match.start():
            return "期号字段出现在年份之前。"

    if marker_base in {"M", "D", "R"}:
        if place_publisher_match is not None and year_match is not None and place_publisher_match.start() > year_match.start():
            return "出版地/出版单位字段出现在年份之后。"

    return None


def _check_language_order(language_buckets: tuple[str, ...]) -> tuple[bool, int | None]:
    seen_zh = False
    for idx, bucket in enumerate(language_buckets):
        if bucket == "zh":
            seen_zh = True
            continue
        if bucket == "en" and seen_zh:
            return False, idx
    return True, None


def _reference_index(entry: ReferenceEntryParse, entry_index: int) -> int:
    return entry.index_number if entry.index_number is not None else entry_index + 1


def _language_bucket(entry: ReferenceEntryParse) -> str:
    if entry.language_hint in {"en", "zh"}:
        return entry.language_hint
    has_cjk = any("\u4e00" <= char <= "\u9fff" for char in entry.raw_text)
    if entry.language_hint == "mixed" and has_cjk:
        return "zh"
    if entry.language_hint == "mixed":
        return "en"
    return "unknown"


def _finding(
    *,
    rule_id: str,
    finding_code: str,
    severity: str,
    entry: ReferenceEntryParse,
    entry_index: int,
    reason: str,
    expected_pattern: str = "",
    evidence: dict[str, object] | None = None,
) -> ReferenceCheckFinding:
    return ReferenceCheckFinding(
        rule_id=rule_id,
        rule_code=rule_id,
        finding_code=finding_code,
        severity=severity,
        block_id="references",
        reference_index=_reference_index(entry, entry_index),
        reference_text=entry.raw_text,
        reason=reason,
        expected_pattern=expected_pattern,
        scope="entry",
        entry_index=entry_index,
        message=reason,
        evidence=evidence or {"finding_code": finding_code},
        suggested_action="仅审查提示，不自动改写参考文献内容。",
        is_auto_fixable=False,
    )


def _finding_for_collection(
    *,
    rule_id: str,
    finding_code: str,
    severity: str,
    reason: str,
    expected_pattern: str = "",
    reference_index: int | None = None,
    reference_text: str = "",
    entry_index: int | None = None,
    evidence: dict[str, object] | None = None,
) -> ReferenceCheckFinding:
    return ReferenceCheckFinding(
        rule_id=rule_id,
        rule_code=rule_id,
        finding_code=finding_code,
        severity=severity,
        block_id="references",
        reference_index=reference_index,
        reference_text=reference_text,
        reason=reason,
        expected_pattern=expected_pattern,
        scope="collection",
        entry_index=entry_index,
        message=reason,
        evidence=evidence or {"finding_code": finding_code},
        suggested_action="仅审查提示，不自动改写参考文献内容。",
        is_auto_fixable=False,
    )


def finding_to_payload(item: ReferenceCheckFinding) -> dict[str, object]:
    return asdict(item)
