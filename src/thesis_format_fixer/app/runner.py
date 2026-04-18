"""Application runner for TASK-004 safety skeleton."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from thesis_format_fixer.contracts.report_types import RuleExecutionRecord
from thesis_format_fixer.detectors.block_locator import locate_blocks
from thesis_format_fixer.io.document_loader import load_document
from thesis_format_fixer.reporters.report_builder import build_report
from thesis_format_fixer.rules.registry import RuleRegistry



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



def run_check(input_file: Path) -> int:
    if not input_file.exists():
        print(f"输入文件不存在: {input_file}")
        return 2

    context = load_document(input_file)
    block_map = locate_blocks(context)
    registry = RuleRegistry()
    report = build_report(_build_skeleton_records(registry))

    payload = {
        "file": str(input_file),
        "capabilities": asdict(context.capabilities),
        "blocks": {
            key: {
                "confidence": value.confidence,
                "evidence": [asdict(e) for e in value.evidence],
            }
            for key, value in block_map.blocks.items()
        },
        "summary": {
            "auto_fixed": len(report.auto_fixed),
            "auto_checked": len(report.auto_checked),
            "report_only": len(report.report_only),
            "excluded_by_scope": len(report.excluded_by_scope),
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0



def run_fix(input_file: Path, output_file: Path) -> int:
    if not input_file.exists():
        print(f"输入文件不存在: {input_file}")
        return 2
    if output_file.is_dir():
        print(f"--out 不能是目录: {output_file}")
        return 2

    # TASK-004: keep fix path as safety-only skeleton, no write-back logic yet.
    return run_check(input_file)
