"""Runtime write-back whitelist for TASK-004."""

from __future__ import annotations

from thesis_format_fixer.contracts.rule_types import RuleDecision
from thesis_format_fixer.rules.registry import RULE_IDS_BY_DECISION

AUTO_FIX_RUNTIME_WHITELIST: frozenset[str] = frozenset(RULE_IDS_BY_DECISION[RuleDecision.AUTO_FIX])


def is_rule_whitelisted_for_write(rule_id: str) -> bool:
    return rule_id in AUTO_FIX_RUNTIME_WHITELIST
