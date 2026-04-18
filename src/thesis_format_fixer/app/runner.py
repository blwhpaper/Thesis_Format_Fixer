"""Application runner for TASK-005 reporting and batch processing."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thesis_format_fixer.contracts.report_types import RuleExecutionRecord
from thesis_format_fixer.contracts.review_types import IntelligentReviewReport, ReviewFinding
from thesis_format_fixer.detectors.block_locator import locate_blocks
from thesis_format_fixer.formatters.task006_specials import execute_task006_docx
from thesis_format_fixer.formatters.task008_a_surface import execute_task008_a_surface_docx
from thesis_format_fixer.io.document_loader import load_document
from thesis_format_fixer.reporters.report_builder import build_report, summarize_a_class_hit_surface
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
    return {
        "rule_id": item.rule_id,
        "block_id": item.block_id,
        "block_type": item.block_type,
        "target": item.target,
        "decision": item.decision.value,
        "confidence": item.confidence,
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
                    + f"source={item['source']} target={item['target']} "
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
        if item["rule_id"] in {"FR-4.10-02", "FR-4.10-03", "FR-4.10-04", "FR-4.11-03", "FR-4.11-04", "FR-4.11-05", "FR-4.11-06"}
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
