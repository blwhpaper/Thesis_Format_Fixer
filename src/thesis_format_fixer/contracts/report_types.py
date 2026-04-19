"""Reporting contracts for TASK-004 safety skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from thesis_format_fixer.contracts.review_types import IntelligentReviewReport, ReferenceReviewAction
from thesis_format_fixer.contracts.rule_types import RuleDecision


@dataclass(frozen=True, slots=True)
class Evidence:
    paragraph_index: int | None
    snippet: str
    reason: str


@dataclass(frozen=True, slots=True)
class BlockDetection:
    block_id: str
    start_paragraph: int | None
    end_paragraph: int | None
    confidence: float
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True, slots=True)
class RuleExecutionRecord:
    rule_id: str
    decision: RuleDecision
    status: str
    checked_only: bool
    excluded_by_scope: bool
    evidence: tuple[Evidence, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReferenceCheckFinding:
    rule_id: str
    rule_code: str = ""
    finding_code: str = ""
    severity: str = "warning"
    block_id: str = "references"
    reference_index: int | None = None
    reference_text: str = ""
    reason: str = ""
    expected_pattern: str = ""
    scope: str = "entry"
    entry_index: int | None = None
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    suggested_action: str = ""
    is_auto_fixable: bool = False


@dataclass(frozen=True, slots=True)
class ReferenceCheckResult:
    findings: tuple[ReferenceCheckFinding, ...]
    entry_findings: tuple[ReferenceCheckFinding, ...]
    collection_findings: tuple[ReferenceCheckFinding, ...]
    english_count: int
    chinese_count: int
    unknown_count: int
    rule_counts: dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    warning_count: int = 0


@dataclass(frozen=True, slots=True)
class ReferencePrioritySummary:
    total_count: int
    blocking_count: int
    p0_count: int
    p1_count: int
    p2_count: int


@dataclass(frozen=True, slots=True)
class ReferenceReviewQueueItem:
    finding_index: int
    rule_id: str
    rule_code: str = ""
    finding_code: str = ""
    severity: str = "warning"
    block_id: str = "references"
    reference_index: int | None = None
    reference_text: str = ""
    reason: str = ""
    expected_pattern: str = ""
    scope: str = "entry"
    entry_index: int | None = None
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    suggested_action: str = ""
    is_auto_fixable: bool = False
    priority_bucket: str = "P2"
    priority_score: int = 100
    review_action: ReferenceReviewAction = ReferenceReviewAction.INSPECT_MANUALLY
    review_reason: str = ""
    is_blocking: bool = False


@dataclass(frozen=True, slots=True)
class ReferenceReviewQueueResult:
    summary: ReferencePrioritySummary
    queue: tuple[ReferenceReviewQueueItem, ...]
    top_priority_findings: tuple[ReferenceReviewQueueItem, ...] = ()


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    auto_fixed: tuple[RuleExecutionRecord, ...]
    auto_checked: tuple[RuleExecutionRecord, ...]
    report_only: tuple[RuleExecutionRecord, ...]
    excluded_by_scope: tuple[RuleExecutionRecord, ...]
    intelligent_review: IntelligentReviewReport | None = None
