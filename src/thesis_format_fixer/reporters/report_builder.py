"""Builds structured execution report for TASK-004 skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from thesis_format_fixer.contracts.report_types import (
    ExecutionReport,
    RuleExecutionRecord,
    UserSummaryArtifact,
    UserSummaryCategorySummary,
    UserResultSummary,
    UserSummaryItem,
    UserSummaryTopAction,
)
from thesis_format_fixer.contracts.review_types import IntelligentReviewReport
from thesis_format_fixer.contracts.rule_types import RuleDecision

TECHNICAL_SUMMARY_KEYS = (
    "auto_fix_rule_count",
    "detected_not_auto_modified_count",
    "manual_review_required_count",
    "reference_finding_count",
    "reference_blocking_count",
    "block_low_confidence_count",
)


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
    title = rule_name
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
            issue_title=rule_name,
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


def _item_is_reference(item: UserSummaryItem) -> bool:
    return item.rule_id.startswith("FR-4.11") or "参考文献" in item.issue_title


def _item_is_footnote(item: UserSummaryItem) -> bool:
    return item.rule_id.startswith("FR-4.10") or "脚注" in item.issue_title


def build_user_result_summary(
    payload: dict[str, Any],
    *,
    artifact_paths: dict[str, str],
    processing_type: str = "check",
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
    all_user_items = (*auto_fixed_items, *detected_but_not_fixed_items, *manual_review_items)
    reference_items = tuple(item for item in all_user_items if _item_is_reference(item))
    footnote_items = tuple(item for item in all_user_items if _item_is_footnote(item))
    other_tip_items = tuple(
        item for item in all_user_items if not _item_is_reference(item) and not _item_is_footnote(item)
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

    processing_label = "修复" if processing_type == "fix" else "检查"
    auto_fixed_count = int(summary.get("auto_fix_rule_count", 0))
    detected_not_auto_modified_count = int(summary.get("detected_not_auto_modified_count", 0))
    manual_review_required_count = int(summary.get("manual_review_required_count", 0))
    reference_reminder_count = int(summary.get("reference_finding_count", 0))
    footnote_reminder_count = len(footnote_items)
    other_reminder_count = len(other_tip_items)
    technical_summary = {key: int(summary.get(key, 0)) for key in TECHNICAL_SUMMARY_KEYS}

    overall_status = f"已完成{processing_label}，当前未发现需要你额外处理的问题"
    if manual_review_required_count > 0:
        overall_status = f"已完成{processing_label}，但仍有需要人工复核的问题"
    elif detected_not_auto_modified_count > 0:
        overall_status = f"已完成{processing_label}，但仍有检测到未自动修改的问题"
    elif processing_type == "fix" and auto_fixed_count > 0:
        overall_status = f"已完成修复，本次已实际修改文档中的 {auto_fixed_count} 项问题"

    key_issues: list[str] = []
    if detected_not_auto_modified_count > 0:
        key_issues.append(f"检测到 {detected_not_auto_modified_count} 项问题，系统未自动修改。")
    if manual_review_required_count > 0:
        key_issues.append(f"有 {manual_review_required_count} 项内容需要你人工复核。")
    if reference_reminder_count > 0:
        key_issues.append(f"参考文献相关提醒 {reference_reminder_count} 项。")
    for item in detected_but_not_fixed_items[:3]:
        key_issues.append(f"重点关注：{item.issue_title}。")
    for item in manual_review_items[:2]:
        key_issues.append(f"建议人工检查：{item.issue_title}。")
    if not key_issues:
        key_issues.append("本次未发现明显格式风险。")

    next_steps: list[str] = []
    if detected_not_auto_modified_count > 0:
        next_steps.append("先处理“检测到但未自动修改”的问题。")
    if manual_review_required_count > 0:
        next_steps.append("再完成“需要人工复核”的项目，避免遗漏。")
    if reference_reminder_count > 0:
        next_steps.append("重点核对参考文献条目格式和顺序。")
    next_steps.append("处理完成后，打开详细报告逐项复查。")

    category_summaries = (
        UserSummaryCategorySummary(
            category_key="auto_fixed",
            category_title="已自动修复 / 已自动处理",
            count=auto_fixed_count,
            description="系统已完成安全范围内的自动处理。",
        ),
        UserSummaryCategorySummary(
            category_key="detected_not_auto_modified",
            category_title="检测到异常但未自动修改",
            count=detected_not_auto_modified_count,
            description="系统已发现异常，但为避免误改，未直接修改文档。",
        ),
        UserSummaryCategorySummary(
            category_key="manual_review_required",
            category_title="需要人工复核",
            count=manual_review_required_count,
            description="这些问题超出当前安全自动处理边界，建议人工确认。",
        ),
        UserSummaryCategorySummary(
            category_key="reference",
            category_title="参考文献相关提醒",
            count=reference_reminder_count,
            description="建议重点检查参考文献条目格式、顺序和类型标识。",
        ),
        UserSummaryCategorySummary(
            category_key="footnote",
            category_title="脚注相关提醒",
            count=footnote_reminder_count,
            description="建议复核脚注类型、编号和样式是否符合要求。",
        ),
    )
    artifact_label_map = {
        "input_file": "输入文件",
        "fixed_docx": "修复后论文文件",
        "technical_report_json": "技术报告 JSON",
        "technical_report_md": "技术报告 Markdown",
        "report_json": "技术报告 JSON",
        "report_md": "技术报告 Markdown",
        "user_summary_md": "用户版摘要文件",
    }
    artifacts = tuple(
        UserSummaryArtifact(
            artifact_key=key,
            label=artifact_label_map.get(key, key),
            path=value,
        )
        for key, value in artifact_paths.items()
        if isinstance(value, str) and value.strip() and value != "(not generated)"
    )

    return UserResultSummary(
        processing_type=processing_type,
        processing_label=processing_label,
        overall_status=overall_status,
        auto_fixed_count=auto_fixed_count,
        detected_not_auto_modified_count=detected_not_auto_modified_count,
        manual_review_required_count=manual_review_required_count,
        reference_reminder_count=reference_reminder_count,
        footnote_reminder_count=footnote_reminder_count,
        other_reminder_count=other_reminder_count,
        key_issues=tuple(key_issues),
        next_steps=tuple(next_steps),
        auto_fixed_items=auto_fixed_items,
        detected_but_not_fixed_items=detected_but_not_fixed_items,
        manual_review_items=manual_review_items,
        reference_items=reference_items,
        footnote_items=footnote_items,
        other_tip_items=other_tip_items,
        category_summaries=category_summaries,
        top_actions=tuple(top_actions),
        artifacts=artifacts,
        technical_summary=technical_summary,
        artifact_paths=artifact_paths,
    )


def render_user_summary_markdown(summary: UserResultSummary, *, payload: dict[str, Any]) -> str:
    lines = [
        "# 用户版结果摘要",
        "",
        "## 概览结果",
        "",
        f"- 本次操作类型：{summary.processing_type}",
        f"- 操作说明：{summary.processing_label}",
        f"- 总体状态：{summary.overall_status}",
        f"- 已自动修复 / 已自动处理：{summary.auto_fixed_count}",
        f"- 检测到异常但未自动修改：{summary.detected_not_auto_modified_count}",
        f"- 需要人工复核：{summary.manual_review_required_count}",
        f"- 参考文献相关提醒：{summary.reference_reminder_count}",
        f"- 脚注相关提醒：{summary.footnote_reminder_count}",
        f"- 其他提示：{summary.other_reminder_count}",
        "",
        "## 分类结果",
        "",
    ]
    for category in summary.category_summaries:
        lines.append(f"- {category.category_title}：{category.count} 项。{category.description}")

    lines.extend(["", "## 结果概览补充", ""])

    for issue in summary.key_issues:
        lines.append(f"- {issue}")

    lines.extend(
        [
            "",
            "## 已自动修改（明细）",
            "",
        ]
    )

    if summary.auto_fixed_items:
        for item in summary.auto_fixed_items:
            lines.append(f"- {item.issue_title}：已处理。建议：{item.next_step or '抽查相关段落。'}")
    else:
        lines.append("- 本次未发生可自动修改的问题。")

    lines.extend(["", "## 发现但未自动修改", ""])
    if summary.detected_but_not_fixed_items:
        for item in summary.detected_but_not_fixed_items:
            lines.append(f"- {item.issue_title}：未自动修改。原因：{item.why_not_auto_fixed} 建议：{item.next_step}")
    else:
        lines.append("- 本次未发现“已定位但未自动修改”的问题。")

    lines.extend(["", "## 建议优先人工检查", ""])
    if summary.manual_review_items:
        for item in summary.manual_review_items:
            lines.append(f"- {item.issue_title}：{item.issue_description} 原因：{item.why_not_auto_fixed} 建议：{item.next_step}")
    else:
        lines.append("- 当前没有必须优先人工处理的项。")

    lines.extend(["", "## 参考文献相关", ""])
    if summary.reference_items:
        for item in summary.reference_items[:10]:
            lines.append(f"- {item.issue_title}：{item.issue_description} 建议：{item.next_step}")
    else:
        lines.append("- 本次未发现参考文献相关提醒。")

    lines.extend(["", "## 脚注相关", ""])
    if summary.footnote_items:
        for item in summary.footnote_items[:10]:
            lines.append(f"- {item.issue_title}：{item.issue_description} 建议：{item.next_step}")
    else:
        lines.append("- 本次未发现脚注相关提醒。")

    lines.extend(["", "## 其他提示", ""])
    if summary.other_tip_items:
        for item in summary.other_tip_items[:10]:
            lines.append(f"- {item.issue_title}：{item.issue_description} 建议：{item.next_step}")
    else:
        lines.append("- 当前没有其他提示。")

    lines.extend(["", "## 相关输出文件路径", ""])
    if summary.artifacts:
        for artifact in summary.artifacts:
            lines.append(f"- {artifact.label}：{artifact.path}")
    else:
        lines.append("- 当前没有可展示的输出文件路径。")

    lines.extend(["", "## 建议下一步", ""])
    for step in summary.next_steps:
        lines.append(f"- {step}")

    if summary.top_actions:
        lines.extend(["", "## 优先建议", ""])
        for action in summary.top_actions:
            lines.append(f"- [{action.priority}] {action.title}：{action.reason}")

    lines.extend(["", "## 技术字段（次级）", ""])
    for key, value in summary.technical_summary.items():
        lines.append(f"- {key}: {value}")

    return "\n".join(lines) + "\n"
