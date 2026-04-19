"""Reference findings prioritization for TASK-013."""

from __future__ import annotations

from thesis_format_fixer.contracts.report_types import (
    ReferenceCheckFinding,
    ReferencePrioritySummary,
    ReferenceReviewQueueItem,
    ReferenceReviewQueueResult,
)
from thesis_format_fixer.contracts.review_types import ReferenceReviewAction

_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}
_PRIORITY_SCORE = {"P0": 300, "P1": 200, "P2": 100}


def build_reference_review_queue(
    findings: tuple[ReferenceCheckFinding, ...],
    *,
    top_k: int = 5,
) -> ReferenceReviewQueueResult:
    items: list[ReferenceReviewQueueItem] = []
    for idx, finding in enumerate(findings):
        priority_bucket, review_reason = _classify_priority(finding)
        is_blocking = priority_bucket == "P0"
        review_action = _recommend_action(finding, priority_bucket, is_blocking=is_blocking)
        items.append(
            ReferenceReviewQueueItem(
                finding_index=idx,
                rule_id=finding.rule_id,
                severity=finding.severity,
                scope=finding.scope,
                entry_index=finding.entry_index,
                message=finding.message,
                evidence=dict(finding.evidence),
                suggested_action=finding.suggested_action,
                is_auto_fixable=finding.is_auto_fixable,
                priority_bucket=priority_bucket,
                priority_score=_PRIORITY_SCORE[priority_bucket],
                review_action=review_action,
                review_reason=review_reason,
                is_blocking=is_blocking,
            )
        )

    ordered = tuple(
        sorted(
            items,
            key=lambda item: (
                _PRIORITY_ORDER[item.priority_bucket],
                item.finding_index,
            ),
        )
    )

    p0_count = sum(1 for item in ordered if item.priority_bucket == "P0")
    p1_count = sum(1 for item in ordered if item.priority_bucket == "P1")
    p2_count = sum(1 for item in ordered if item.priority_bucket == "P2")
    summary = ReferencePrioritySummary(
        total_count=len(ordered),
        blocking_count=p0_count,
        p0_count=p0_count,
        p1_count=p1_count,
        p2_count=p2_count,
    )

    top_items = ordered[:max(top_k, 0)]
    return ReferenceReviewQueueResult(summary=summary, queue=ordered, top_priority_findings=top_items)


def _classify_priority(finding: ReferenceCheckFinding) -> tuple[str, str]:
    if _is_blocking_grouping_issue(finding):
        return "P0", "英文文献数量或中英文分组规则疑似不达标，需先处理。"
    if _is_blocking_structure_failure(finding):
        return "P0", "条目结构识别不稳定，需先做结构性复核。"
    if finding.rule_id == "FR-4.11-06":
        return "P1", "参考文献排序疑似异常，建议优先核对。"
    if finding.rule_id == "FR-4.11-05" or finding.severity == "weak":
        return "P2", "提示类问题，可在时间不足时延后处理。"
    if finding.severity == "error":
        return "P1", "关键结构字段缺失或结构异常，需优先修正。"
    return "P1", "结构或规则一致性存在风险，建议优先人工核对。"


def _is_blocking_grouping_issue(finding: ReferenceCheckFinding) -> bool:
    if finding.rule_id != "FR-4.11-04":
        return False
    if finding.scope != "collection":
        return False
    evidence = finding.evidence
    if "required_min" in evidence:
        return True
    if "violation_entry_index" in evidence:
        return True
    return "英文在前、中文在后" in finding.message


def _is_blocking_structure_failure(finding: ReferenceCheckFinding) -> bool:
    evidence = finding.evidence
    check = str(evidence.get("check", ""))
    if check in {"entry_type_unknown", "parse_confidence_low"}:
        return True
    if finding.rule_id == "FR-4.11-03" and finding.scope == "collection":
        return "low_confidence_count" in evidence or "unknown_type_count" in evidence
    return False


def _recommend_action(
    finding: ReferenceCheckFinding,
    priority_bucket: str,
    *,
    is_blocking: bool,
) -> ReferenceReviewAction:
    if is_blocking:
        if finding.scope == "collection" or finding.rule_id == "FR-4.11-04":
            return ReferenceReviewAction.REQUIRES_STRUCTURAL_RECHECK
        return ReferenceReviewAction.FIX_BEFORE_SUBMISSION
    if priority_bucket == "P1":
        if finding.severity == "error":
            return ReferenceReviewAction.FIX_BEFORE_SUBMISSION
        if finding.rule_id == "FR-4.11-06":
            return ReferenceReviewAction.VERIFY_AGAINST_SOURCE
        return ReferenceReviewAction.INSPECT_MANUALLY
    if finding.severity == "weak" or finding.rule_id == "FR-4.11-05":
        return ReferenceReviewAction.DEFER_IF_TIME_LIMITED
    return ReferenceReviewAction.INSPECT_MANUALLY
