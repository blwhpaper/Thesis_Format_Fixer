"""Builds structured execution report for TASK-004 skeleton."""

from __future__ import annotations

from dataclasses import dataclass

from thesis_format_fixer.contracts.report_types import ExecutionReport, RuleExecutionRecord
from thesis_format_fixer.contracts.review_types import IntelligentReviewReport
from thesis_format_fixer.contracts.rule_types import RuleDecision


@dataclass(frozen=True, slots=True)
class AClassHitSurface:
    hit: tuple[RuleExecutionRecord, ...]
    unhit: tuple[RuleExecutionRecord, ...]
    degraded: tuple[RuleExecutionRecord, ...]


def summarize_a_class_hit_surface(records: list[RuleExecutionRecord]) -> AClassHitSurface:
    hit: list[RuleExecutionRecord] = []
    unhit: list[RuleExecutionRecord] = []
    degraded: list[RuleExecutionRecord] = []
    for item in records:
        if item.decision is not RuleDecision.AUTO_FIX:
            continue
        if item.status in {"fixed", "checked_ok"}:
            hit.append(item)
            continue
        if item.status in {"detected_not_modified"}:
            degraded.append(item)
            continue
        unhit.append(item)
    return AClassHitSurface(hit=tuple(hit), unhit=tuple(unhit), degraded=tuple(degraded))


def build_report(
    records: list[RuleExecutionRecord],
    *,
    intelligent_review: IntelligentReviewReport | None = None,
) -> ExecutionReport:
    auto_fixed: list[RuleExecutionRecord] = []
    auto_checked: list[RuleExecutionRecord] = []
    report_only: list[RuleExecutionRecord] = []
    excluded_by_scope: list[RuleExecutionRecord] = []

    for record in records:
        if record.excluded_by_scope:
            excluded_by_scope.append(record)
            continue
        if record.decision is RuleDecision.AUTO_FIX:
            auto_fixed.append(record)
            continue
        if record.decision is RuleDecision.AUTO_CHECK:
            auto_checked.append(record)
            continue
        if record.decision is RuleDecision.REPORT_ONLY:
            report_only.append(record)
            continue
        excluded_by_scope.append(record)

    return ExecutionReport(
        auto_fixed=tuple(auto_fixed),
        auto_checked=tuple(auto_checked),
        report_only=tuple(report_only),
        excluded_by_scope=tuple(excluded_by_scope),
        intelligent_review=intelligent_review,
    )
