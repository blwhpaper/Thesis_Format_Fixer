"""Application runner for TASK-005 reporting and batch processing."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thesis_format_fixer.contracts.report_types import (
    ReferencePrioritySummary,
    ReferenceReviewQueueItem,
    RuleExecutionRecord,
)
from thesis_format_fixer.contracts.review_types import IntelligentReviewReport, ReviewFinding
from thesis_format_fixer.detectors.block_locator import locate_blocks, scan_reference_entries
from thesis_format_fixer.detectors.reference_parser import parse_reference_entry
from thesis_format_fixer.formatters.task006_specials import execute_task006_docx
from thesis_format_fixer.formatters.task008_a_surface import execute_task008_a_surface_docx
from thesis_format_fixer.io.document_loader import load_document
from thesis_format_fixer.reporters.report_builder import build_report, summarize_a_class_hit_surface
from thesis_format_fixer.review.reference_checkers import finding_to_payload, run_reference_checks
from thesis_format_fixer.review.finding_prioritizer import build_reference_review_queue
from thesis_format_fixer.review.model_adapter import LocalModelAdapter
from thesis_format_fixer.review.reviewer import REVIEW_TARGETS, ReviewConfig, Reviewer
from thesis_format_fixer.rules.registry import RuleRegistry


BLOCK_CONFIDENCE_REVIEW_THRESHOLD = 0.85


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_to_payload(record: RuleExecutionRecord, *, registry: RuleRegistry) -> dict[str, Any]:
    metadata = registry.get_metadata(record.rule_id)
    return {
        "rule_id": record.rule_id,
        "rule_name": metadata.rule_name,
        "decision": record.decision.value,
        "status": record.status,
        "checked_only": record.checked_only,
        "excluded_by_scope": record.excluded_by_scope,
        "evidence": [asdict(item) for item in record.evidence],
        "details": dict(record.details),
    }


def _derive_report_paths(output_docx: Path) -> tuple[Path, Path]:
    report_json = output_docx.with_suffix(".report.json")
    report_md = output_docx.with_suffix(".report.md")
    return report_json, report_md


def _normalize_review_targets(raw: str | tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if raw is None:
        return REVIEW_TARGETS
    if isinstance(raw, str):
        parts = [item.strip() for item in raw.split(",")]
    else:
        parts = [str(item).strip() for item in raw]
    targets = tuple(item for item in parts if item in REVIEW_TARGETS)
    if not targets:
        return REVIEW_TARGETS
    # Keep deterministic order.
    return tuple(item for item in REVIEW_TARGETS if item in targets)


def _review_finding_to_payload(item: ReviewFinding) -> dict[str, Any]:
    first_evidence = item.evidence[0] if item.evidence else None
    return {
        "rule_id": item.rule_id,
        "severity": item.severity,
        "block_id": item.block_id,
        "block_type": item.block_type,
        "target": item.target,
        "decision": item.decision.value,
        "confidence": item.confidence,
        "reason": first_evidence.reason if first_evidence is not None else "",
        "snippet": first_evidence.snippet if first_evidence is not None else "",
        "paragraph_index": first_evidence.paragraph_index if first_evidence is not None else None,
        "evidence": [asdict(evidence) for evidence in item.evidence],
        "suggestion": item.suggestion,
        "auto_fix_allowed": item.auto_fix_allowed,
        "source": item.source,
    }


def _intelligent_review_payload(report: IntelligentReviewReport) -> dict[str, Any]:
    return {
        "status": report.status.value,
        "mode": report.mode,
        "targets": list(report.targets),
        "degraded_reasons": list(report.degraded_reasons),
        "findings": [_review_finding_to_payload(item) for item in report.findings],
        "metadata": dict(report.metadata),
    }


def _reference_priority_summary_payload(item: ReferencePrioritySummary) -> dict[str, int]:
    return {
        "total_count": item.total_count,
        "blocking_count": item.blocking_count,
        "p0_count": item.p0_count,
        "p1_count": item.p1_count,
        "p2_count": item.p2_count,
    }


def _reference_review_queue_item_payload(item: ReferenceReviewQueueItem) -> dict[str, Any]:
    return {
        "finding_index": item.finding_index,
        "rule_id": item.rule_id,
        "rule_code": item.rule_code,
        "finding_code": item.finding_code,
        "severity": item.severity,
        "block_id": item.block_id,
        "reference_index": item.reference_index,
        "reference_text": item.reference_text,
        "reason": item.reason,
        "expected_pattern": item.expected_pattern,
        "scope": item.scope,
        "entry_index": item.entry_index,
        "message": item.message,
        "evidence": dict(item.evidence),
        "suggested_action": item.suggested_action,
        "is_auto_fixable": item.is_auto_fixable,
        "priority_bucket": item.priority_bucket,
        "priority_score": item.priority_score,
        "review_action": item.review_action.value,
        "review_reason": item.review_reason,
        "is_blocking": item.is_blocking,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    sections = payload["sections"]
    summary = payload["summary"]
    lines = [
        "# Thesis Format Fixer Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- input_file: {payload['input_file']}",
        f"- output_docx: {payload.get('output_docx') or '(none)'}",
        "",
        "## Summary",
        "",
        f"- auto_fix_rule_count: {summary['auto_fix_rule_count']}",
        f"- detected_not_auto_modified_count: {summary['detected_not_auto_modified_count']}",
        f"- manual_review_required_count: {summary['manual_review_required_count']}",
        f"- block_low_confidence_count: {summary['block_low_confidence_count']}",
        "",
        "## 已自动修复",
        "",
    ]

    auto_fixed = sections["auto_fixed"]
    if auto_fixed:
        for item in auto_fixed:
            lines.append(f"- {item['rule_id']} {item['rule_name']} [{item['status']}]")
    else:
        lines.append("- (none)")

    lines.extend(["", "## 已自动修复的脚注样式项", ""])
    footnotes_fixed = sections["auto_fixed_footnotes"]
    if footnotes_fixed:
        for item in footnotes_fixed:
            lines.append(f"- {item['rule_id']} {item['rule_name']} [{item['status']}]")
    else:
        lines.append("- (none)")

    lines.extend(["", "## 已自动修复的参考文献基础样式项", ""])
    bibliography_fixed = sections["auto_fixed_bibliography"]
    if bibliography_fixed:
        for item in bibliography_fixed:
            lines.append(f"- {item['rule_id']} {item['rule_name']} [{item['status']}]")
    else:
        lines.append("- (none)")

    lines.extend(["", "## 检测到异常但未自动修改", ""])
    not_modified = sections["detected_not_auto_modified"]
    if not_modified:
        for item in not_modified:
            lines.append(f"- {item['rule_id']} {item['rule_name']} [{item['decision']}]")
    else:
        lines.append("- (none)")

    lines.extend(["", "## 检测到但未自动修改的专项问题", ""])
    special_not_modified = sections["detected_special_issues_not_modified"]
    if special_not_modified:
        for item in special_not_modified:
            lines.append(f"- {item['rule_id']} {item['rule_name']}: {item['details']}")
    else:
        lines.append("- (none)")

    lines.extend(["", "## A 类命中面", ""])
    a_surface = sections.get("a_class_hit_surface", {})
    for label, key in (
        ("已命中", "hit"),
        ("未命中", "unhit"),
        ("降级", "degraded"),
    ):
        lines.append(f"- {label}: {len(a_surface.get(key, []))}")

    lines.extend(["", "## 参考文献识别诊断", ""])
    references_diag = sections.get("references_diagnostics", {})
    lines.append(f"- references_heading_detected: {references_diag.get('references_heading_detected', False)}")
    lines.append(f"- references_heading_index: {references_diag.get('references_heading_index')}")
    lines.append(f"- reference_entries_detected: {references_diag.get('reference_entries_detected', 0)}")
    lines.append(f"- reference_entry_total: {references_diag.get('reference_entry_total', 0)}")
    lines.append(
        f"- numbered_reference_entry_count: {references_diag.get('numbered_reference_entry_count', 0)}"
    )
    lines.append(
        f"- author_leading_reference_entry_count: {references_diag.get('author_leading_reference_entry_count', 0)}"
    )
    lines.append(
        f"- suspicious_reference_candidate_count: {references_diag.get('suspicious_reference_candidate_count', 0)}"
    )
    lines.append(f"- reference_entries_fixed: {references_diag.get('reference_entries_fixed', 0)}")
    lines.append(f"- skipped_or_suspicious_count: {len(references_diag.get('skipped_or_suspicious', []))}")
    lines.append(f"- reference_parsed_count: {references_diag.get('reference_parsed_count', 0)}")
    lines.append(
        "- "
        + f"reference_parse_high_confidence_count: {references_diag.get('reference_parse_high_confidence_count', 0)}"
    )
    lines.append(
        "- "
        + f"reference_parse_low_confidence_count: {references_diag.get('reference_parse_low_confidence_count', 0)}"
    )
    lines.append(f"- reference_check_finding_count: {references_diag.get('reference_check_finding_count', 0)}")
    lines.append(f"- reference_check_error_count: {references_diag.get('reference_check_error_count', 0)}")
    lines.append(f"- reference_check_warning_count: {references_diag.get('reference_check_warning_count', 0)}")
    lines.append(f"- reference_english_count: {references_diag.get('reference_english_count', 0)}")
    lines.append(f"- reference_chinese_count: {references_diag.get('reference_chinese_count', 0)}")
    lines.append(f"- reference_unknown_count: {references_diag.get('reference_unknown_count', 0)}")
    lines.append(
        "- "
        + f"reference_collection_findings: {len(references_diag.get('reference_collection_findings', []))}"
    )
    lines.append(
        "- "
        + f"reference_entry_findings_sample: {len(references_diag.get('reference_entry_findings_sample', []))}"
    )

    lines.extend(["", "## 参考文献人工复核队列", ""])
    reference_review = sections.get("reference_review", {})
    priority_summary = reference_review.get("reference_priority_summary", {})
    lines.append(f"- reference_finding_count: {reference_review.get('reference_finding_count', 0)}")
    lines.append(f"- reference_blocking_count: {reference_review.get('reference_blocking_count', 0)}")
    lines.append(
        "- "
        + "priority_distribution: "
        + f"P0={priority_summary.get('p0_count', 0)} "
        + f"P1={priority_summary.get('p1_count', 0)} "
        + f"P2={priority_summary.get('p2_count', 0)}"
    )
    queue = reference_review.get("reference_review_queue", [])
    if queue:
        for item in queue:
            lines.append(
                "- "
                + f"[{item['priority_bucket']}] {item['rule_id']} "
                + f"blocking={item['is_blocking']} action={item['review_action']} "
                + f"reason={item['review_reason']}"
            )
    else:
        lines.append("- reference_review_queue: (none)")

    lines.extend(["", "## 需人工复核", ""])
    manual_items = sections["manual_review_required"]
    if manual_items:
        for item in manual_items:
            if item["item_type"] == "rule":
                lines.append(f"- 规则 {item['rule_id']} {item['rule_name']}: 超出 V1 自动修改范围")
                continue
            if item["item_type"] == "block":
                lines.append(
                    f"- 区块 {item['block_id']}: 置信度 {item['confidence']:.2f} 低于阈值 {BLOCK_CONFIDENCE_REVIEW_THRESHOLD:.2f}"
                )
                continue
            lines.append(f"- {item}")
    else:
        lines.append("- (none)")

    intelligent_review = sections.get("intelligent_review")
    if intelligent_review is not None:
        lines.extend(["", "## 智能审查结果", ""])
        lines.append(f"- status: {intelligent_review['status']}")
        lines.append(f"- mode: {intelligent_review['mode']}")
        if intelligent_review["degraded_reasons"]:
            lines.append(f"- degraded_reasons: {', '.join(intelligent_review['degraded_reasons'])}")
        findings = intelligent_review["findings"]
        if findings:
            for item in findings:
                lines.append(
                    "- "
                    + f"{item['rule_id']} [{item['decision']}] "
                    + f"severity={item['severity']} source={item['source']} target={item['target']} "
                    + f"confidence={item['confidence']:.2f}"
                )
        else:
            lines.append("- findings: (none)")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_single_payload(
    input_file: Path,
    *,
    output_docx: Path | None = None,
    review_mode: str = "off",
    review_targets: str | tuple[str, ...] | list[str] | None = None,
    review_local_model: str | None = None,
    model_adapter: LocalModelAdapter | None = None,
) -> dict[str, Any]:
    working_file = output_docx if output_docx is not None else input_file
    context = load_document(working_file)
    block_map = locate_blocks(context)
    registry = RuleRegistry()
    records = _build_skeleton_records(registry)

    if working_file.suffix.lower() == ".docx" and working_file.exists():
        task008 = execute_task008_a_surface_docx(
            working_file,
            block_map=block_map,
            apply_fixes=output_docx is not None,
            confidence_threshold=BLOCK_CONFIDENCE_REVIEW_THRESHOLD,
        )
        _merge_rule_updates(records, task008.updates)
        task006 = execute_task006_docx(working_file, apply_fixes=output_docx is not None)
        _merge_rule_updates(records, task006.updates)

    review_report = None
    if review_mode.lower().strip() != "off":
        review_config = ReviewConfig(
            mode=review_mode,
            targets=_normalize_review_targets(review_targets),
            local_model=review_local_model,
        )
        review_report = Reviewer(review_config, adapter=model_adapter).run(context, block_map)

    report = build_report(records, intelligent_review=review_report)
    a_surface = summarize_a_class_hit_surface(records)
    references_diagnostics = _build_references_diagnostics(
        context=context,
        block_map=block_map,
        records=records,
    )
    reference_priority_summary = references_diagnostics["reference_priority_summary"]
    reference_review_queue = references_diagnostics["reference_review_queue"]
    top_priority_findings = references_diagnostics["top_priority_findings"]

    auto_fixed = [
        _record_to_payload(item, registry=registry) for item in report.auto_fixed if item.status == "fixed"
    ]
    auto_fixed_footnotes = [
        item for item in auto_fixed if item["rule_id"] in {"FR-4.10-02", "FR-4.10-03", "FR-4.10-04"}
    ]
    auto_fixed_bibliography = [item for item in auto_fixed if item["rule_id"] == "FR-4.11-02"]
    detected_not_auto_modified = [
        _record_to_payload(item, registry=registry)
        for item in (*report.auto_fixed, *report.auto_checked, *report.report_only)
        if item.status == "detected_not_modified"
    ]
    detected_special_issues_not_modified = [
        item
        for item in detected_not_auto_modified
        if item["rule_id"]
        in {
            "FR-4.9-02",
            "FR-4.10-02",
            "FR-4.10-03",
            "FR-4.10-04",
            "FR-4.11-03",
            "FR-4.11-04",
            "FR-4.11-05",
            "FR-4.11-06",
            "FR-4.11-07",
        }
    ]
    manual_review_required: list[dict[str, Any]] = [
        {
            "item_type": "rule",
            "rule_id": item.rule_id,
            "rule_name": registry.get_metadata(item.rule_id).rule_name,
            "reason": "out_of_v1_scope",
        }
        for item in report.excluded_by_scope
    ]

    for block in block_map.blocks.values():
        if block.confidence >= BLOCK_CONFIDENCE_REVIEW_THRESHOLD:
            continue
        manual_review_required.append(
            {
                "item_type": "block",
                "block_id": block.block_id,
                "confidence": block.confidence,
                "evidence": [asdict(item) for item in block.evidence],
                "reason": "low_confidence_block_location",
            }
        )

    sections: dict[str, Any] = {
        "auto_fixed": auto_fixed,
        "auto_fixed_footnotes": auto_fixed_footnotes,
        "auto_fixed_bibliography": auto_fixed_bibliography,
        "detected_not_auto_modified": detected_not_auto_modified,
        "detected_special_issues_not_modified": detected_special_issues_not_modified,
        "a_class_hit_surface": {
            "hit": [_record_to_payload(item, registry=registry) for item in a_surface.hit],
            "unhit": [_record_to_payload(item, registry=registry) for item in a_surface.unhit],
            "degraded": [_record_to_payload(item, registry=registry) for item in a_surface.degraded],
        },
        "references_diagnostics": references_diagnostics,
        "reference_review": {
            "reference_finding_count": references_diagnostics["reference_finding_count"],
            "reference_blocking_count": references_diagnostics["reference_blocking_count"],
            "reference_priority_summary": reference_priority_summary,
            "reference_review_queue": reference_review_queue,
            "top_priority_findings": top_priority_findings,
        },
        "manual_review_required": manual_review_required,
    }

    if report.intelligent_review is not None:
        sections["intelligent_review"] = _intelligent_review_payload(report.intelligent_review)

    return {
        "schema_version": "task-006-report-v1",
        "generated_at": _utc_now_iso(),
        "input_file": str(input_file),
        "output_docx": str(output_docx) if output_docx is not None else None,
        "summary": {
            "auto_fix_rule_count": len(auto_fixed),
            "auto_fix_footnote_count": len(auto_fixed_footnotes),
            "auto_fix_bibliography_count": len(auto_fixed_bibliography),
            "detected_not_auto_modified_count": len(detected_not_auto_modified),
            "detected_special_issues_not_modified_count": len(detected_special_issues_not_modified),
            "manual_review_required_count": len(manual_review_required),
            "a_class_hit_count": len(a_surface.hit),
            "a_class_unhit_count": len(a_surface.unhit),
            "a_class_degraded_count": len(a_surface.degraded),
            "references_heading_detected": 1 if references_diagnostics["references_heading_detected"] else 0,
            "reference_entry_detected_count": references_diagnostics["reference_entries_detected"],
            "reference_entry_total": references_diagnostics["reference_entry_total"],
            "numbered_reference_entry_count": references_diagnostics["numbered_reference_entry_count"],
            "author_leading_reference_entry_count": references_diagnostics[
                "author_leading_reference_entry_count"
            ],
            "reference_entry_fixed_count": references_diagnostics["reference_entries_fixed"],
            "reference_parsed_count": references_diagnostics["reference_parsed_count"],
            "reference_parse_high_confidence_count": references_diagnostics[
                "reference_parse_high_confidence_count"
            ],
            "reference_parse_low_confidence_count": references_diagnostics[
                "reference_parse_low_confidence_count"
            ],
            "reference_check_finding_count": references_diagnostics["reference_check_finding_count"],
            "reference_finding_count": references_diagnostics["reference_finding_count"],
            "reference_check_error_count": references_diagnostics["reference_check_error_count"],
            "reference_check_warning_count": references_diagnostics["reference_check_warning_count"],
            "reference_blocking_count": references_diagnostics["reference_blocking_count"],
            "reference_priority_summary": reference_priority_summary,
            "reference_english_count": references_diagnostics["reference_english_count"],
            "reference_chinese_count": references_diagnostics["reference_chinese_count"],
            "reference_unknown_count": references_diagnostics["reference_unknown_count"],
            "suspicious_reference_candidate_count": references_diagnostics[
                "suspicious_reference_candidate_count"
            ],
            "reference_suspicious_count": len(references_diagnostics["skipped_or_suspicious"]),
            "block_low_confidence_count": sum(
                1
                for block in block_map.blocks.values()
                if block.confidence < BLOCK_CONFIDENCE_REVIEW_THRESHOLD
            ),
            "intelligent_review_finding_count": len(report.intelligent_review.findings)
            if report.intelligent_review is not None
            else 0,
            "intelligent_review_degraded_count": len(report.intelligent_review.degraded_reasons)
            if report.intelligent_review is not None
            else 0,
        },
        "sections": sections,
        "capabilities": asdict(context.capabilities),
        "blocks": {
            key: {
                "confidence": value.confidence,
                "evidence": [asdict(e) for e in value.evidence],
            }
            for key, value in block_map.blocks.items()
        },
    }


def _build_references_diagnostics(
    *,
    context: Any,
    block_map: Any,
    records: list[RuleExecutionRecord],
) -> dict[str, Any]:
    heading_block = block_map.blocks.get("references_heading") or block_map.blocks.get("references_title")
    heading_index = None if heading_block is None else heading_block.start_paragraph
    heading_detected = heading_index is not None

    entries_detected = 0
    numbered_entry_count = 0
    author_leading_entry_count = 0
    parsed_count = 0
    parsed_high_confidence_count = 0
    parsed_low_confidence_count = 0
    reference_type_counts: dict[str, int] = {}
    unresolved_reference_entries: list[dict[str, Any]] = []
    parsed_entries: list[Any] = []
    entry_texts: list[str] = []
    scan_stop_reason = "references_heading_not_found"
    skipped_or_suspicious: list[dict[str, Any]] = []
    if heading_detected:
        hard_stop = None
        ack_block = block_map.blocks.get("ack_title")
        if ack_block is not None and ack_block.start_paragraph is not None and ack_block.start_paragraph > heading_index:
            hard_stop = ack_block.start_paragraph
        scan = scan_reference_entries(context.paragraphs, heading_index=heading_index, hard_stop_index=hard_stop)
        entries_detected = len(scan.entry_groups)
        numbered_entry_count = sum(1 for source in scan.entry_group_sources if source == "numbered_entry")
        author_leading_entry_count = sum(
            1 for source in scan.entry_group_sources if source == "author_leading_fallback"
        )
        for group in scan.entry_groups:
            lines = [context.paragraphs[idx].strip() for idx in group if 0 <= idx < len(context.paragraphs)]
            text = " ".join(item for item in lines if item).strip()
            if text:
                entry_texts.append(text)
        scan_stop_reason = scan.stop_reason
        for idx in scan.skipped_indices:
            skipped_or_suspicious.append(
                {
                    "paragraph_index": idx,
                    "snippet": context.paragraphs[idx] if 0 <= idx < len(context.paragraphs) else "",
                    "reason": "suspicious_unrecognized",
                }
            )
        for idx in scan.suspicious_unrecognized_indices:
            if idx in scan.skipped_indices:
                continue
            skipped_or_suspicious.append(
                {
                    "paragraph_index": idx,
                    "snippet": context.paragraphs[idx] if 0 <= idx < len(context.paragraphs) else "",
                    "reason": "suspicious_unrecognized",
                }
            )
        if entries_detected == 0:
            skipped_or_suspicious.append(
                {
                    "paragraph_index": heading_index,
                    "snippet": context.paragraphs[heading_index] if 0 <= heading_index < len(context.paragraphs) else "",
                    "reason": "reference_entry_start_not_found",
                }
            )
    for text in entry_texts:
        parsed = parse_reference_entry(text)
        parsed_entries.append(parsed)
        if parsed.entry_type != "unknown" or parsed.title is not None or parsed.authors:
            parsed_count += 1
        reference_type_counts[parsed.entry_type] = reference_type_counts.get(parsed.entry_type, 0) + 1
        if parsed.parse_confidence == "high":
            parsed_high_confidence_count += 1
        if parsed.parse_confidence == "low":
            parsed_low_confidence_count += 1
            unresolved_reference_entries.append(
                {
                    "index_number": parsed.index_number,
                    "entry_type": parsed.entry_type,
                    "raw_text": parsed.raw_text,
                    "parse_notes": list(parsed.parse_notes),
                }
            )

    unresolved_reference_entries = unresolved_reference_entries[:5]
    parsed_entries_tuple = tuple(parsed_entries)
    reference_check_result = run_reference_checks(parsed_entries_tuple)
    reference_review_queue = build_reference_review_queue(reference_check_result.findings)

    ref_fix_record = next((item for item in records if item.rule_id == "FR-4.11-02"), None)
    entries_fixed = 0
    if ref_fix_record is not None:
        details = ref_fix_record.details
        entries_fixed = int(details.get("fixed_entry_group_count", 0))
        if not skipped_or_suspicious:
            for idx in details.get("skipped_paragraph_indices", [])[:5]:
                index = int(idx)
                skipped_or_suspicious.append(
                    {
                        "paragraph_index": index,
                        "snippet": context.paragraphs[index] if 0 <= index < len(context.paragraphs) else "",
                        "reason": "formatter_skipped_paragraph",
                    }
                )

    return {
        "references_heading_detected": heading_detected,
        "references_heading_index": heading_index,
        "reference_entries_detected": entries_detected,
        "reference_entry_total": entries_detected,
        "numbered_reference_entry_count": numbered_entry_count,
        "author_leading_reference_entry_count": author_leading_entry_count,
        "reference_entries_fixed": entries_fixed,
        "reference_entry_count": entries_detected,
        "reference_parsed_count": parsed_count,
        "reference_parse_high_confidence_count": parsed_high_confidence_count,
        "reference_parse_low_confidence_count": parsed_low_confidence_count,
        "reference_type_counts": reference_type_counts,
        "unresolved_reference_entries": unresolved_reference_entries,
        "reference_check_finding_count": len(reference_check_result.findings),
        "reference_finding_count": len(reference_check_result.findings),
        "reference_check_error_count": reference_check_result.error_count,
        "reference_check_warning_count": reference_check_result.warning_count,
        "reference_blocking_count": reference_review_queue.summary.blocking_count,
        "reference_priority_summary": _reference_priority_summary_payload(reference_review_queue.summary),
        "reference_review_queue": [
            _reference_review_queue_item_payload(item) for item in reference_review_queue.queue
        ],
        "top_priority_findings": [
            _reference_review_queue_item_payload(item) for item in reference_review_queue.top_priority_findings
        ],
        "reference_check_rule_counts": dict(reference_check_result.rule_counts),
        "reference_collection_findings": [
            finding_to_payload(item) for item in reference_check_result.collection_findings
        ],
        "reference_entry_findings_sample": [
            finding_to_payload(item) for item in reference_check_result.entry_findings[:10]
        ],
        "reference_english_count": reference_check_result.english_count,
        "reference_chinese_count": reference_check_result.chinese_count,
        "reference_unknown_count": reference_check_result.unknown_count,
        "scan_stop_reason": scan_stop_reason,
        "suspicious_reference_candidate_count": len(skipped_or_suspicious),
        "skipped_or_suspicious": skipped_or_suspicious,
    }


def _run_single(
    input_file: Path,
    *,
    output_docx: Path | None,
    report_json_out: Path | None,
    report_md_out: Path | None,
    review_mode: str = "off",
    review_targets: str | tuple[str, ...] | list[str] | None = None,
    review_local_model: str | None = None,
    model_adapter: LocalModelAdapter | None = None,
) -> tuple[int, dict[str, Any], Path | None, Path | None]:
    if output_docx is not None:
        output_docx.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_file, output_docx)

    payload = _build_single_payload(
        input_file,
        output_docx=output_docx,
        review_mode=review_mode,
        review_targets=review_targets,
        review_local_model=review_local_model,
        model_adapter=model_adapter,
    )

    final_json_out: Path | None = report_json_out
    final_md_out: Path | None = report_md_out
    if output_docx is not None:
        default_json, default_md = _derive_report_paths(output_docx)
        if final_json_out is None:
            final_json_out = default_json
        if final_md_out is None:
            final_md_out = default_md

    if final_json_out is not None:
        _write_json(final_json_out, payload)
    if final_md_out is not None:
        _write_markdown(final_md_out, payload)

    return 0, payload, final_json_out, final_md_out


def _find_docx_files(input_dir: Path, *, recursive: bool) -> tuple[Path, ...]:
    if recursive:
        return tuple(sorted(path for path in input_dir.rglob("*.docx") if path.is_file()))
    return tuple(sorted(path for path in input_dir.glob("*.docx") if path.is_file()))


def _build_skeleton_records(registry: RuleRegistry) -> list[RuleExecutionRecord]:
    records: list[RuleExecutionRecord] = []
    for metadata in registry.all_metadata():
        records.append(
            RuleExecutionRecord(
                rule_id=metadata.rule_id,
                decision=metadata.v1_decision,
                status="skeleton_only",
                checked_only=metadata.checked_only,
                excluded_by_scope=not metadata.allow_write_back and metadata.v1_decision.value == "Out of V1",
                evidence=(),
                details={"source_of_truth": metadata.source_of_truth},
            )
        )
    return records


def _merge_rule_updates(records: list[RuleExecutionRecord], updates: dict[str, Any]) -> None:
    indexed = {record.rule_id: idx for idx, record in enumerate(records)}
    for rule_id, update in updates.items():
        idx = indexed.get(rule_id)
        if idx is None:
            continue
        current = records[idx]
        next_status = update.status
        if current.status == "fixed" and update.status != "fixed":
            next_status = current.status
        records[idx] = RuleExecutionRecord(
            rule_id=current.rule_id,
            decision=current.decision,
            status=next_status,
            checked_only=current.checked_only,
            excluded_by_scope=current.excluded_by_scope,
            evidence=update.evidence,
            details={**current.details, **update.details},
        )



def run_check(
    input_file: Path,
    *,
    report_json_out: Path | None = None,
    report_md_out: Path | None = None,
    review_mode: str = "off",
    review_targets: str | tuple[str, ...] | list[str] | None = None,
    review_local_model: str | None = None,
    model_adapter: LocalModelAdapter | None = None,
) -> int:
    if not input_file.exists():
        print(f"输入文件不存在: {input_file}")
        return 2

    code, payload, _, _ = _run_single(
        input_file,
        output_docx=None,
        report_json_out=report_json_out,
        report_md_out=report_md_out,
        review_mode=review_mode,
        review_targets=review_targets,
        review_local_model=review_local_model,
        model_adapter=model_adapter,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code



def run_fix(
    input_file: Path,
    output_file: Path,
    *,
    report_json_out: Path | None = None,
    report_md_out: Path | None = None,
    review_mode: str = "off",
    review_targets: str | tuple[str, ...] | list[str] | None = None,
    review_local_model: str | None = None,
    model_adapter: LocalModelAdapter | None = None,
) -> int:
    if not input_file.exists():
        print(f"输入文件不存在: {input_file}")
        return 2
    if output_file.is_dir():
        print(f"--out 不能是目录: {output_file}")
        return 2

    # V1 safety boundary: no content/style write-back, only passthrough copy + report.
    code, payload, report_json, report_md = _run_single(
        input_file,
        output_docx=output_file,
        report_json_out=report_json_out,
        report_md_out=report_md_out,
        review_mode=review_mode,
        review_targets=review_targets,
        review_local_model=review_local_model,
        model_adapter=model_adapter,
    )
    print(
        json.dumps(
            {
                "input_file": str(input_file),
                "output_docx": str(output_file),
                "report_json": str(report_json) if report_json else None,
                "report_md": str(report_md) if report_md else None,
                "summary": payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return code


def run_batch_fix(
    input_dir: Path,
    output_dir: Path,
    *,
    recursive: bool = True,
    review_mode: str = "off",
    review_targets: str | tuple[str, ...] | list[str] | None = None,
    review_local_model: str | None = None,
) -> int:
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"输入目录不存在或不可用: {input_dir}")
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    files = _find_docx_files(input_dir, recursive=recursive)

    started_at = _utc_now_iso()
    items: list[dict[str, Any]] = []
    succeeded = 0
    failed = 0

    for input_file in files:
        rel_path = input_file.relative_to(input_dir)
        target_dir = output_dir / rel_path.parent
        output_docx = target_dir / f"{input_file.stem}.fixed.docx"
        report_json = target_dir / f"{input_file.stem}.report.json"
        report_md = target_dir / f"{input_file.stem}.report.md"

        try:
            code, payload, _, _ = _run_single(
                input_file,
                output_docx=output_docx,
                report_json_out=report_json,
                report_md_out=report_md,
                review_mode=review_mode,
                review_targets=review_targets,
                review_local_model=review_local_model,
            )
        except Exception as exc:  # pragma: no cover - defensive path
            code = 1
            payload = {"error": str(exc), "summary": {}}

        if code == 0:
            succeeded += 1
        else:
            failed += 1

        items.append(
            {
                "input_file": str(input_file),
                "output_docx": str(output_docx),
                "report_json": str(report_json),
                "report_md": str(report_md),
                "exit_code": code,
                "summary": payload.get("summary", {}),
            }
        )

    summary_payload = {
        "schema_version": "task-005-batch-summary-v1",
        "generated_at": _utc_now_iso(),
        "started_at": started_at,
        "finished_at": _utc_now_iso(),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "recursive": recursive,
        "total_files": len(files),
        "succeeded": succeeded,
        "failed": failed,
        "items": items,
    }

    summary_json = output_dir / "batch_summary.json"
    summary_md = output_dir / "batch_summary.md"
    _write_json(summary_json, summary_payload)

    md_lines = [
        "# Thesis Format Fixer Batch Summary",
        "",
        f"- generated_at: {summary_payload['generated_at']}",
        f"- input_dir: {summary_payload['input_dir']}",
        f"- output_dir: {summary_payload['output_dir']}",
        f"- recursive: {summary_payload['recursive']}",
        f"- total_files: {summary_payload['total_files']}",
        f"- succeeded: {summary_payload['succeeded']}",
        f"- failed: {summary_payload['failed']}",
        "",
        "## Per File",
        "",
    ]
    if not items:
        md_lines.append("- (no .docx files found)")
    else:
        for item in items:
            md_lines.append(
                "- "
                + f"exit_code={item['exit_code']} "
                + f"input={item['input_file']} "
                + f"output={item['output_docx']} "
                + f"report={item['report_json']}"
            )
    summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps(summary_payload, ensure_ascii=False, indent=2))
    return 0 if failed == 0 else 1
