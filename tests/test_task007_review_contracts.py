from thesis_format_fixer.contracts.review_types import (
    IntelligentReviewReport,
    ReviewDecision,
    ReviewEvidence,
    ReviewFinding,
    ReviewStatus,
)


def test_review_contract_defaults_and_required_fields() -> None:
    finding = ReviewFinding(
        rule_id="FR-4.8-01",
        block_id="body",
        block_type="body.headings",
        target="heading_structure",
        decision=ReviewDecision.WARN,
        confidence=0.7,
        evidence=(ReviewEvidence(reason="sample", snippet="1.2 Title", paragraph_index=10),),
        suggestion="人工复核",
    )

    assert finding.rule_id == "FR-4.8-01"
    assert finding.decision is ReviewDecision.WARN
    assert finding.auto_fix_allowed is False
    assert finding.source == "rule_engine"


def test_intelligent_review_report_structure() -> None:
    report = IntelligentReviewReport(
        status=ReviewStatus.COMPLETED,
        mode="basic",
        targets=("headings",),
        findings=(),
        degraded_reasons=(),
    )

    assert report.status is ReviewStatus.COMPLETED
    assert report.mode == "basic"
    assert report.targets == ("headings",)
