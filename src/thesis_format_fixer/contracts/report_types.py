"""Reporting contracts for TASK-004 safety skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
class ExecutionReport:
    auto_fixed: tuple[RuleExecutionRecord, ...]
    auto_checked: tuple[RuleExecutionRecord, ...]
    report_only: tuple[RuleExecutionRecord, ...]
    excluded_by_scope: tuple[RuleExecutionRecord, ...]
