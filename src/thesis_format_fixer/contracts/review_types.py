"""Structured review contracts for TASK-007."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ReviewDecision(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    UNABLE_TO_JUDGE = "unable_to_judge"


class ReviewStatus(str, Enum):
    DISABLED = "disabled"
    COMPLETED = "completed"
    DEGRADED = "degraded"


@dataclass(frozen=True, slots=True)
class ReviewEvidence:
    reason: str
    snippet: str = ""
    paragraph_index: int | None = None


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    rule_id: str
    block_id: str
    block_type: str
    target: str
    decision: ReviewDecision
    confidence: float
    evidence: tuple[ReviewEvidence, ...] = ()
    suggestion: str = ""
    auto_fix_allowed: bool = False
    source: str = "rule_engine"


@dataclass(frozen=True, slots=True)
class IntelligentReviewReport:
    status: ReviewStatus
    mode: str
    targets: tuple[str, ...]
    findings: tuple[ReviewFinding, ...] = ()
    degraded_reasons: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
