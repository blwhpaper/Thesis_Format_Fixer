"""Out-of-scope runtime guards for TASK-004."""

from __future__ import annotations

from thesis_format_fixer.contracts.rule_types import RuleDecision
from thesis_format_fixer.rules.registry import RULE_IDS_BY_DECISION
from thesis_format_fixer.rules.whitelist import is_rule_whitelisted_for_write

HARD_BLOCKED_ACTIONS: frozenset[str] = frozenset(
    {
        "toc_rebuild",
        "section_page_numbering_reconstruct",
        "footnote_per_page_renumber",
        "odd_even_layout_reconstruct",
        "cover_rebuild",
        "bibliography_content_reorder_or_correction",
    }
)

OUT_OF_V1_RULE_IDS: frozenset[str] = frozenset(RULE_IDS_BY_DECISION[RuleDecision.OUT_OF_V1])


class OutOfV1Error(RuntimeError):
    """Raised when runtime tries to execute blocked operations."""


class WhitelistViolationError(RuntimeError):
    """Raised when runtime tries to write for non-whitelisted rules."""



def guard_write_back(rule_id: str, *, action: str | None = None) -> None:
    if action in HARD_BLOCKED_ACTIONS:
        raise OutOfV1Error(f"Blocked runtime action: {action}")

    if rule_id in OUT_OF_V1_RULE_IDS:
        raise OutOfV1Error(f"Rule is out of V1 scope: {rule_id}")

    if not is_rule_whitelisted_for_write(rule_id):
        raise WhitelistViolationError(f"Write back is not allowed for rule: {rule_id}")
