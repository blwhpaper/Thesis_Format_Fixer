"""Reference-entry and reference-collection rule checkers for TASK-012."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime

from thesis_format_fixer.contracts.report_types import ReferenceCheckFinding, ReferenceCheckResult
from thesis_format_fixer.detectors.reference_parser import ReferenceEntryParse


def run_reference_checks(
    entries: tuple[ReferenceEntryParse, ...],
    *,
    current_year: int | None = None,
) -> ReferenceCheckResult:
    if current_year is None:
        current_year = datetime.now().year

    entry_findings: list[ReferenceCheckFinding] = []
    collection_findings: list[ReferenceCheckFinding] = []

    english_count = 0
    chinese_count = 0
    unknown_count = 0
    low_confidence_count = 0
    entry_unknown_type_count = 0

    language_buckets: list[str] = []
    for idx, entry in enumerate(entries):
        bucket = _language_bucket(entry)
        language_buckets.append(bucket)
        if bucket == "en":
            english_count += 1
        elif bucket == "zh":
            chinese_count += 1
        else:
            unknown_count += 1

        if entry.entry_type == "unknown":
            entry_unknown_type_count += 1
        if entry.parse_confidence == "low":
            low_confidence_count += 1

        entry_findings.extend(_entry_level_checks(entry, idx))

    collection_findings.extend(
        _collection_level_checks(
            entries,
            english_count=english_count,
            chinese_count=chinese_count,
            unknown_count=unknown_count,
            low_confidence_count=low_confidence_count,
            entry_unknown_type_count=entry_unknown_type_count,
            current_year=current_year,
            language_buckets=tuple(language_buckets),
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


def _entry_level_checks(entry: ReferenceEntryParse, entry_index: int) -> list[ReferenceCheckFinding]:
    findings: list[ReferenceCheckFinding] = []

    def _entry_finding(
        *,
        rule_id: str,
        severity: str,
        message: str,
        evidence: dict[str, object],
        suggested_action: str,
    ) -> None:
        findings.append(
            ReferenceCheckFinding(
                rule_id=rule_id,
                severity=severity,
                scope="entry",
                entry_index=entry_index,
                message=message,
                evidence=evidence,
                suggested_action=suggested_action,
                is_auto_fixable=False,
            )
        )

    if not entry.type_code:
        _entry_finding(
            rule_id="FR-4.11-03",
            severity="warning",
            message="参考文献条目缺失文献类型代码（如 [J]/[M]/[D]）。",
            evidence={"check": "missing_type_code", "raw_text": entry.raw_text},
            suggested_action="补全条目类型代码并按规范标注。",
        )
    if entry.entry_type == "unknown":
        _entry_finding(
            rule_id="FR-4.11-03",
            severity="error",
            message="参考文献条目类型无法识别。",
            evidence={"check": "entry_type_unknown", "type_code": entry.type_code, "raw_text": entry.raw_text},
            suggested_action="按期刊/专著/学位论文/报告等规范重写条目结构。",
        )
    if entry.parse_confidence == "low":
        _entry_finding(
            rule_id="FR-4.11-03",
            severity="warning",
            message="参考文献条目解析置信度较低。",
            evidence={"check": "parse_confidence_low", "parse_notes": list(entry.parse_notes)},
            suggested_action="人工复核条目结构是否满足规范模板。",
        )
    if entry.parse_notes:
        _entry_finding(
            rule_id="FR-4.11-03",
            severity="warning",
            message="参考文献条目存在解析备注，建议人工复核。",
            evidence={"check": "parse_notes_present", "parse_notes": list(entry.parse_notes)},
            suggested_action="根据备注逐项核对条目字段完整性。",
        )

    if entry.type_code == "J":
        _require_non_empty(findings, entry, entry_index, field_name="authors", display_name="作者", rule_id="FR-4.11-03")
        _require_non_empty(findings, entry, entry_index, field_name="title", display_name="题名", rule_id="FR-4.11-03")
        _require_non_empty(
            findings,
            entry,
            entry_index,
            field_name="container_or_source",
            display_name="刊名/来源",
            rule_id="FR-4.11-03",
        )
        _require_non_empty(findings, entry, entry_index, field_name="year", display_name="年份", rule_id="FR-4.11-03")
        _require_non_empty(findings, entry, entry_index, field_name="pages", display_name="页码", rule_id="FR-4.11-03")
        if not entry.issue:
            findings.append(
                ReferenceCheckFinding(
                    rule_id="FR-4.11-03",
                    severity="warning",
                    scope="entry",
                    entry_index=entry_index,
                    message="期刊条目缺少期号（issue）。",
                    evidence={"check": "journal_issue_missing", "raw_text": entry.raw_text},
                    suggested_action="建议补全期号信息（若来源中有该字段）。",
                    is_auto_fixable=False,
                )
            )

    if entry.type_code == "M":
        _require_non_empty(findings, entry, entry_index, field_name="authors", display_name="作者", rule_id="FR-4.11-03")
        _require_non_empty(findings, entry, entry_index, field_name="title", display_name="书名", rule_id="FR-4.11-03")
        if not entry.publication_place and not entry.publisher:
            findings.append(
                ReferenceCheckFinding(
                    rule_id="FR-4.11-03",
                    severity="error",
                    scope="entry",
                    entry_index=entry_index,
                    message="专著条目缺少出版地/出版社信息。",
                    evidence={"check": "book_place_publisher_missing", "raw_text": entry.raw_text},
                    suggested_action="至少补全出版地或出版社中的一项。",
                    is_auto_fixable=False,
                )
            )
        _require_non_empty(findings, entry, entry_index, field_name="year", display_name="年份", rule_id="FR-4.11-03")

    if entry.type_code == "D":
        _require_non_empty(findings, entry, entry_index, field_name="authors", display_name="作者", rule_id="FR-4.11-03")
        _require_non_empty(findings, entry, entry_index, field_name="title", display_name="题名", rule_id="FR-4.11-03")
        _require_non_empty(findings, entry, entry_index, field_name="year", display_name="年份", rule_id="FR-4.11-03")
        if not entry.degree_grantor:
            findings.append(
                ReferenceCheckFinding(
                    rule_id="FR-4.11-03",
                    severity="warning",
                    scope="entry",
                    entry_index=entry_index,
                    message="学位论文条目缺少学位授予单位信息。",
                    evidence={"check": "thesis_degree_grantor_missing", "raw_text": entry.raw_text},
                    suggested_action="补全授予单位（学校/机构）信息。",
                    is_auto_fixable=False,
                )
            )

    if entry.type_code == "R":
        _require_non_empty(findings, entry, entry_index, field_name="authors", display_name="作者/机构作者", rule_id="FR-4.11-03")
        _require_non_empty(findings, entry, entry_index, field_name="title", display_name="题名", rule_id="FR-4.11-03")
        _require_non_empty(findings, entry, entry_index, field_name="year", display_name="年份", rule_id="FR-4.11-03")

    is_electronic = entry.entry_type == "electronic" or entry.medium_code is not None or entry.type_code in {"DB", "EB", "CP"}
    if is_electronic:
        if not entry.medium_code:
            findings.append(
                ReferenceCheckFinding(
                    rule_id="FR-4.11-03",
                    severity="warning",
                    scope="entry",
                    entry_index=entry_index,
                    message="电子文献条目缺少载体标识（如 /OL）。",
                    evidence={"check": "electronic_medium_code_missing", "type_code": entry.type_code},
                    suggested_action="在文献类型代码中补充载体标识。",
                    is_auto_fixable=False,
                )
            )
        if not entry.url_or_locator:
            findings.append(
                ReferenceCheckFinding(
                    rule_id="FR-4.11-03",
                    severity="error",
                    scope="entry",
                    entry_index=entry_index,
                    message="电子文献条目缺少 URL/DOI/定位信息。",
                    evidence={"check": "electronic_url_missing", "raw_text": entry.raw_text},
                    suggested_action="补全可访问的 URL、DOI 或定位标识。",
                    is_auto_fixable=False,
                )
            )
        if not entry.year:
            findings.append(
                ReferenceCheckFinding(
                    rule_id="FR-4.11-03",
                    severity="error",
                    scope="entry",
                    entry_index=entry_index,
                    message="电子文献条目缺少年份。",
                    evidence={"check": "electronic_year_missing", "raw_text": entry.raw_text},
                    suggested_action="补全年份信息。",
                    is_auto_fixable=False,
                )
            )

    return findings


def _require_non_empty(
    findings: list[ReferenceCheckFinding],
    entry: ReferenceEntryParse,
    entry_index: int,
    *,
    field_name: str,
    display_name: str,
    rule_id: str,
) -> None:
    value = getattr(entry, field_name)
    missing = not value if not isinstance(value, tuple) else len(value) == 0
    if not missing:
        return
    findings.append(
        ReferenceCheckFinding(
            rule_id=rule_id,
            severity="error",
            scope="entry",
            entry_index=entry_index,
            message=f"条目缺少{display_name}字段。",
            evidence={"check": f"{field_name}_missing", "type_code": entry.type_code, "raw_text": entry.raw_text},
            suggested_action=f"补全{display_name}字段。",
            is_auto_fixable=False,
        )
    )


def _collection_level_checks(
    entries: tuple[ReferenceEntryParse, ...],
    *,
    english_count: int,
    chinese_count: int,
    unknown_count: int,
    low_confidence_count: int,
    entry_unknown_type_count: int,
    current_year: int,
    language_buckets: tuple[str, ...],
) -> list[ReferenceCheckFinding]:
    findings: list[ReferenceCheckFinding] = []
    total = len(entries)
    if total == 0:
        return findings

    if english_count < 5:
        findings.append(
            ReferenceCheckFinding(
                rule_id="FR-4.11-04",
                severity="warning",
                scope="collection",
                entry_index=None,
                message="英文参考文献数量少于 5 篇。",
                evidence={"english_count": english_count, "required_min": 5},
                suggested_action="补充不少于 5 篇英文文献。",
                is_auto_fixable=False,
            )
        )

    language_order_ok, violation_at = _check_language_order(language_buckets)
    if not language_order_ok:
        findings.append(
            ReferenceCheckFinding(
                rule_id="FR-4.11-04",
                severity="warning",
                scope="collection",
                entry_index=violation_at,
                message="参考文献顺序疑似未满足“英文在前、中文在后”。",
                evidence={"violation_entry_index": violation_at},
                suggested_action="人工复核中英文分组顺序。",
                is_auto_fixable=False,
            )
        )

    recent_threshold = current_year - 2
    recent_count = sum(1 for item in entries if _entry_year(item) is not None and _entry_year(item) >= recent_threshold)
    if recent_count == 0:
        findings.append(
            ReferenceCheckFinding(
                rule_id="FR-4.11-05",
                severity="warning",
                scope="collection",
                entry_index=None,
                message="近三年相关文献命中较少（提示项）。",
                evidence={"recent_window_start_year": recent_threshold, "recent_count": recent_count},
                suggested_action="可考虑补充近三年相关研究文献。",
                is_auto_fixable=False,
            )
        )

    unknown_or_low = entry_unknown_type_count + low_confidence_count
    if unknown_or_low >= max(3, total // 3):
        findings.append(
            ReferenceCheckFinding(
                rule_id="FR-4.11-03",
                severity="warning",
                scope="collection",
                entry_index=None,
                message="unknown/low-confidence 条目占比较高。",
                evidence={
                    "entry_total": total,
                    "unknown_type_count": entry_unknown_type_count,
                    "low_confidence_count": low_confidence_count,
                },
                suggested_action="优先人工复核 unknown 与 low-confidence 条目。",
                is_auto_fixable=False,
            )
        )

    publication_order_weak, order_evidence = _check_publication_order_weak(entries)
    if publication_order_weak:
        findings.append(
            ReferenceCheckFinding(
                rule_id="FR-4.11-06",
                severity="weak",
                scope="collection",
                entry_index=None,
                message="参考文献疑似未按发表顺序排列（弱提示）。",
                evidence=order_evidence,
                suggested_action="仅作提示，建议人工核对排序原则。",
                is_auto_fixable=False,
            )
        )

    if unknown_count > 0 and chinese_count == 0 and english_count == 0:
        findings.append(
            ReferenceCheckFinding(
                rule_id="FR-4.11-04",
                severity="weak",
                scope="collection",
                entry_index=None,
                message="参考文献语言识别结果不稳定，分组判断仅供参考。",
                evidence={"unknown_language_count": unknown_count},
                suggested_action="人工确认中英文文献分组。",
                is_auto_fixable=False,
            )
        )

    return findings


def _check_language_order(language_buckets: tuple[str, ...]) -> tuple[bool, int | None]:
    seen_chinese = False
    for idx, bucket in enumerate(language_buckets):
        if bucket == "zh":
            seen_chinese = True
            continue
        if bucket == "en" and seen_chinese:
            return False, idx
    return True, None


def _check_publication_order_weak(entries: tuple[ReferenceEntryParse, ...]) -> tuple[bool, dict[str, object]]:
    years: list[tuple[int, int]] = []
    for idx, item in enumerate(entries):
        year = _entry_year(item)
        if year is None:
            continue
        years.append((idx, year))

    if len(years) < 4:
        return False, {}

    year_values = [item[1] for item in years]
    is_non_decreasing = all(year_values[idx] >= year_values[idx - 1] for idx in range(1, len(year_values)))
    is_non_increasing = all(year_values[idx] <= year_values[idx - 1] for idx in range(1, len(year_values)))
    if is_non_decreasing or is_non_increasing:
        return False, {}

    return True, {
        "sample_year_sequence": year_values[:8],
        "known_year_entry_count": len(years),
    }


def _entry_year(entry: ReferenceEntryParse) -> int | None:
    if not entry.year:
        return None
    try:
        return int(entry.year)
    except ValueError:
        return None


def _language_bucket(entry: ReferenceEntryParse) -> str:
    if entry.language_hint in {"en", "zh"}:
        return entry.language_hint
    has_cjk = any("\u4e00" <= char <= "\u9fff" for char in entry.raw_text)
    if entry.language_hint == "mixed" and has_cjk:
        return "zh"
    return "unknown"


def finding_to_payload(item: ReferenceCheckFinding) -> dict[str, object]:
    return asdict(item)
