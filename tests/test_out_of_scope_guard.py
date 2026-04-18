import pytest

from thesis_format_fixer.rules.out_of_scope import HARD_BLOCKED_ACTIONS, OutOfV1Error, guard_write_back


@pytest.mark.parametrize("action", sorted(HARD_BLOCKED_ACTIONS))
def test_hard_blocked_actions_always_raise(action: str) -> None:
    with pytest.raises(OutOfV1Error):
        guard_write_back("FR-4.2-01", action=action)


def test_out_of_scope_rule_write_is_blocked() -> None:
    with pytest.raises(OutOfV1Error):
        guard_write_back("FR-4.10-05")
