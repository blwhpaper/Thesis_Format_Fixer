"""Typed review finding contract and policy-to-adapter mapping for TASK-THESIS-OSS-006A."""

from __future__ import annotations

from dataclasses import dataclass

from thesis_format_fixer.review.adapter import ReviewFinding as AdapterReviewFinding
from thesis_format_fixer.review.profiles import ReviewRule


@dataclass(frozen=True, slots=True)
class StructuredReviewFinding:
    """Policy-constrained structured finding before adapter mapping."""

    rule_id: str
    category: str
    severity: str
    message: str
    anchor_strategy: str
    paragraph_index: int | None = None
    run_index: int | None = None
    anchor_text: str | None = None
    comment_allowed: bool = True
    auto_rewrite_allowed: bool = False
    body_text_mutation_allowed: bool = False


@dataclass(frozen=True, slots=True)
class ReviewFindingMappingResult:
    """Mapping output for adapter consumption or explicit skip/invalid state."""

    status: str
    structured_finding: StructuredReviewFinding
    adapter_finding: AdapterReviewFinding | None
    reason: str


def build_review_finding_from_rule(
    rule: ReviewRule,
    *,
    message: str | None = None,
    paragraph_index: int | None = None,
    run_index: int | None = None,
    anchor_text: str | None = None,
) -> StructuredReviewFinding:
    """Builds a structured finding from review policy plus detected issue payload."""

    return StructuredReviewFinding(
        rule_id=rule.rule_id,
        category=rule.category,
        severity=rule.severity,
        message=(message or rule.message_template).strip(),
        anchor_strategy=rule.anchor_strategy,
        paragraph_index=paragraph_index,
        run_index=run_index,
        anchor_text=anchor_text,
        comment_allowed=rule.comment_allowed,
        auto_rewrite_allowed=rule.auto_rewrite_allowed,
        body_text_mutation_allowed=False,
    )


def validate_structured_finding(finding: StructuredReviewFinding) -> tuple[str, ...]:
    """Validates write-back safety and required metadata invariants."""

    errors: list[str] = []
    if not finding.rule_id:
        errors.append("missing:rule_id")
    if not finding.category:
        errors.append("missing:category")
    if not finding.severity:
        errors.append("missing:severity")
    if not finding.message:
        errors.append("missing:message")
    if not finding.anchor_strategy:
        errors.append("missing:anchor_strategy")

    if finding.auto_rewrite_allowed is not False:
        errors.append(f"invalid:auto_rewrite_allowed:{finding.auto_rewrite_allowed}")
    if finding.comment_allowed is not True:
        errors.append(f"invalid:comment_allowed:{finding.comment_allowed}")
    if finding.body_text_mutation_allowed is not False:
        errors.append(
            f"invalid:body_text_mutation_allowed:{finding.body_text_mutation_allowed}"
        )

    if finding.paragraph_index is not None and finding.paragraph_index < 0:
        errors.append("invalid:paragraph_index")
    if finding.run_index is not None and finding.run_index < 0:
        errors.append("invalid:run_index")

    return tuple(errors)


def to_adapter_finding(finding: StructuredReviewFinding) -> ReviewFindingMappingResult:
    """Maps validated structured finding to Word adapter finding or skip/invalid result."""

    errors = validate_structured_finding(finding)
    if errors:
        return ReviewFindingMappingResult(
            status="invalid",
            structured_finding=finding,
            adapter_finding=None,
            reason="; ".join(errors),
        )

    if finding.paragraph_index is None:
        return ReviewFindingMappingResult(
            status="skipped",
            structured_finding=finding,
            adapter_finding=None,
            reason="missing:anchor.paragraph_index",
        )

    adapter_finding = AdapterReviewFinding(
        rule_id=finding.rule_id,
        message=finding.message,
        paragraph_index=finding.paragraph_index,
        run_index=finding.run_index,
        anchor_text=finding.anchor_text,
    )
    return ReviewFindingMappingResult(
        status="mapped",
        structured_finding=finding,
        adapter_finding=adapter_finding,
        reason="ok",
    )
