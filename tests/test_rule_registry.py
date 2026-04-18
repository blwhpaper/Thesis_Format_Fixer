from thesis_format_fixer.contracts.rule_types import RuleDecision
from thesis_format_fixer.rules.registry import RuleRegistry


def test_rule_registry_counts_match_task003_mapping() -> None:
    registry = RuleRegistry()

    assert len(registry.by_decision(RuleDecision.AUTO_FIX)) == 13
    assert len(registry.by_decision(RuleDecision.AUTO_CHECK)) == 19
    assert len(registry.by_decision(RuleDecision.REPORT_ONLY)) == 24
    assert len(registry.by_decision(RuleDecision.OUT_OF_V1)) == 5
    assert len(registry.all_metadata()) == 61


def test_rule_registry_can_get_binding_and_register_handlers() -> None:
    registry = RuleRegistry()

    detector = object()
    fixer = object()
    reporter = object()
    registry.register_handlers("FR-4.2-01", detector=detector, fixer=fixer, reporter=reporter)

    binding = registry.get_binding("FR-4.2-01")
    assert binding.metadata.rule_id == "FR-4.2-01"
    assert binding.detector is detector
    assert binding.fixer is fixer
    assert binding.reporter is reporter
