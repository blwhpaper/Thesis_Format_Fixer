from thesis_format_fixer.contracts.rule_types import RuleDecision
from thesis_format_fixer.rules.out_of_scope import WhitelistViolationError, guard_write_back
from thesis_format_fixer.rules.registry import RULE_IDS_BY_DECISION
from thesis_format_fixer.rules.whitelist import AUTO_FIX_RUNTIME_WHITELIST


def test_runtime_whitelist_equals_auto_fix_decision_set() -> None:
    assert AUTO_FIX_RUNTIME_WHITELIST == frozenset(RULE_IDS_BY_DECISION[RuleDecision.AUTO_FIX])


def test_write_back_rejected_for_non_whitelist_rule() -> None:
    non_whitelist_rule = "FR-4.6-05"  # Report Only
    try:
        guard_write_back(non_whitelist_rule)
    except WhitelistViolationError:
        return
    raise AssertionError("Expected whitelist violation for non-whitelisted write")
