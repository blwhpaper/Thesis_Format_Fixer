"""Builds structured execution report for TASK-004 skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from thesis_format_fixer.contracts.report_types import (
    ExecutionReport,
    RuleExecutionRecord,
    UserResultSummary,
    UserSummaryItem,
    UserSummaryTopAction,
)
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


def _reason_category_text(reason: str, decision: str = "") -> tuple[str, str]:
    if reason == "out_of_v1_scope":
        return "超出范围", "当前版本出于安全边界不自动修改该类问题。"
    if reason == "low_confidence_block_location":
        return "定位置信度不足", "系统对区块定位置信度不足，避免误改。"
    if decision == RuleDecision.AUTO_CHECK.value:
        return "仅自动检查", "该规则当前仅做检查，不执行自动修改。"
    if decision == RuleDecision.REPORT_ONLY.value:
        return "仅报告提示", "该规则当前只做报告提示，需人工确认后处理。"
    return "需人工判断", "当前结果未满足安全自动修改条件。"


def _build_user_item_from_rule(item: dict[str, Any], *, handled: str) -> UserSummaryItem:
    rule_id = str(item.get("rule_id", ""))
    rule_name = str(item.get("rule_name", "")).strip() or "未命名规则"
    decision = str(item.get("decision", ""))
    category, why = _reason_category_text(str(item.get("reason", "")), decision=decision)
    title = f"{rule_name}（{rule_id}）" if rule_id else rule_name
    return UserSummaryItem(
        issue_title=title,
        issue_description=f"检测到与“{rule_name}”相关的问题。",
        handling_status=handled,
        why_not_auto_fixed=why if handled != "已自动修改" else "",
        next_step="按技术报告定位段落进行人工确认。" if handled != "已自动修改" else "抽查修改后的段落样式是否符合规范。",
        rule_id=rule_id,
        reason_category=category,
    )


def _build_user_item_from_manual(item: dict[str, Any]) -> UserSummaryItem:
    item_type = str(item.get("item_type", ""))
    if item_type == "rule":
        rule_id = str(item.get("rule_id", ""))
        rule_name = str(item.get("rule_name", "")).strip() or "未命名规则"
        category, why = _reason_category_text(str(item.get("reason", "")))
        return UserSummaryItem(
            issue_title=f"{rule_name}（{rule_id}）" if rule_id else rule_name,
            issue_description="该问题需要人工复核后再决定是否调整。",
            handling_status="需人工处理",
            why_not_auto_fixed=why,
            next_step="优先核对该规则涉及的文档区域。",
            rule_id=rule_id,
            reason_category=category,
        )

    block_id = str(item.get("block_id", "unknown"))
    confidence = item.get("confidence")
    category, why = _reason_category_text(str(item.get("reason", "")))
    return UserSummaryItem(
        issue_title=f"区块定位复核（{block_id}）",
        issue_description=f"文档区块定位置信度偏低（{confidence}）。",
        handling_status="需人工处理",
        why_not_auto_fixed=why,
        next_step="先确认该区块起止位置是否正确，再决定是否手动修改。",
        rule_id="",
        reason_category=category,
    )


def build_user_result_summary(
    payload: dict[str, Any],
    *,
    artifact_paths: dict[str, str],
) -> UserResultSummary:
    sections = payload.get("sections", {})
    summary = payload.get("summary", {})

    auto_fixed_items = tuple(
        _build_user_item_from_rule(item, handled="已自动修改") for item in sections.get("auto_fixed", [])
    )
    detected_but_not_fixed_items = tuple(
        _build_user_item_from_rule(item, handled="发现但未自动修改")
        for item in sections.get("detected_not_auto_modified", [])
    )
    manual_review_items = tuple(
        _build_user_item_from_manual(item) for item in sections.get("manual_review_required", [])
    )

    top_actions: list[UserSummaryTopAction] = []
    if detected_but_not_fixed_items:
        top_actions.append(
            UserSummaryTopAction(
                title="优先处理“发现但未自动修改”问题",
                reason="这些问题已被定位，但需要你确认后手动处理。",
                priority="high",
            )
        )
    if manual_review_items:
        top_actions.append(
            UserSummaryTopAction(
                title="优先完成人工复核项",
                reason="存在超出自动处理范围或定位置信度不足的问题。",
                priority="high",
            )
        )
    if not top_actions:
        top_actions.append(
            UserSummaryTopAction(
                title="已完成本轮基础处理",
                reason="建议抽查技术报告中的关键段落以确认最终格式。",
                priority="medium",
            )
        )

    overall_status = "已完成并全部自动处理"
    if summary.get("manual_review_required_count", 0):
        overall_status = "已完成处理，但仍有人工复核项"
    elif summary.get("detected_not_auto_modified_count", 0):
        overall_status = "已完成处理，但仍有未自动修改问题"

    return UserResultSummary(
        overall_status=overall_status,
        auto_fixed_items=auto_fixed_items,
        detected_but_not_fixed_items=detected_but_not_fixed_items,
        manual_review_items=manual_review_items,
        top_actions=tuple(top_actions),
        artifact_paths=artifact_paths,
    )


def render_user_summary_markdown(summary: UserResultSummary, *, payload: dict[str, Any]) -> str:
    counts = payload.get("summary", {})
    lines = [
        "# 用户版结果摘要",
        "",
        "## 处理结果概览",
        "",
        f"- 总体状态：{summary.overall_status}",
        f"- 自动修改项：{counts.get('auto_fix_rule_count', 0)}",
        f"- 发现但未自动修改：{counts.get('detected_not_auto_modified_count', 0)}",
        f"- 建议人工复核：{counts.get('manual_review_required_count', 0)}",
        "",
        "## 已自动修改",
        "",
    ]

    if summary.auto_fixed_items:
        for item in summary.auto_fixed_items:
            lines.append(
                f"- {item.issue_title}：已处理。建议：{item.next_step or '抽查相关段落。'}"
            )
    else:
        lines.append("- 本次未发生可自动修改的问题。")

    lines.extend(["", "## 发现但未自动修改", ""])
    if summary.detected_but_not_fixed_items:
        for item in summary.detected_but_not_fixed_items:
            lines.append(
                f"- {item.issue_title}：未自动修改。原因：{item.why_not_auto_fixed} 建议：{item.next_step}"
            )
    else:
        lines.append("- 本次未发现“已定位但未自动修改”的问题。")

    lines.extend(["", "## 建议优先人工检查", ""])
    if summary.manual_review_items:
        for item in summary.manual_review_items:
            lines.append(
                f"- {item.issue_title}：{item.issue_description} 原因：{item.why_not_auto_fixed} 建议：{item.next_step}"
            )
    else:
        lines.append("- 当前没有必须优先人工处理的项。")

    lines.extend(["", "## 结果文件位置说明", ""])
    for key, path in summary.artifact_paths.items():
        lines.append(f"- {key}: {path}")

    if summary.top_actions:
        lines.extend(["", "### 下一步建议", ""])
        for action in summary.top_actions:
            lines.append(f"- [{action.priority}] {action.title}：{action.reason}")

    return "\n".join(lines) + "\n"
