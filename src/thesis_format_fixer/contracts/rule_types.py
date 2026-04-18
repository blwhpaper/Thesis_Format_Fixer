"""Rule contracts for TASK-004 safety skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class RuleDecision(str, Enum):
    AUTO_FIX = "Auto Fix"
    AUTO_CHECK = "Auto Check"
    REPORT_ONLY = "Report Only"
    OUT_OF_V1 = "Out of V1"


DetectorFn = Callable[[Any], Any]
FixerFn = Callable[[Any], Any]
ReporterFn = Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class RuleMetadata:
    rule_id: str
    rule_name: str
    v1_decision: RuleDecision
    checked_only: bool
    allow_write_back: bool
    source_of_truth: str


@dataclass(slots=True)
class RuleBinding:
    metadata: RuleMetadata
    detector: DetectorFn | None = None
    fixer: FixerFn | None = None
    reporter: ReporterFn | None = None
