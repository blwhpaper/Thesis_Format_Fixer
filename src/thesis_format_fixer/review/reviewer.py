"""Review orchestrator for TASK-007."""

from __future__ import annotations

from dataclasses import dataclass

from thesis_format_fixer.contracts.review_types import (
    IntelligentReviewReport,
    ReviewDecision,
    ReviewEvidence,
    ReviewFinding,
    ReviewStatus,
)
from thesis_format_fixer.detectors.block_locator import BlockMap
from thesis_format_fixer.io.document_loader import DocumentContext
from thesis_format_fixer.review.checkers import heading_structure_review, pagination_review, reference_structure_review
from thesis_format_fixer.review.model_adapter import (
    DisabledModelAdapter,
    LocalModelAdapter,
    ModelAdapterError,
    PlaceholderLocalModelAdapter,
)

REVIEW_TARGETS = ("headings", "references", "pagination")


@dataclass(frozen=True, slots=True)
class ReviewConfig:
    mode: str = "off"
    targets: tuple[str, ...] = REVIEW_TARGETS
    local_model: str | None = None


_TARGET_TO_TASK = {
    "headings": "heading_structure_review",
    "references": "reference_structure_review",
    "pagination": "pagination_review",
}


class Reviewer:
    """Runs rule-engine checks and optional local-model assisted review."""

    def __init__(self, config: ReviewConfig, *, adapter: LocalModelAdapter | None = None) -> None:
        self._config = config
        self._adapter = adapter

    def run(self, context: DocumentContext, block_map: BlockMap) -> IntelligentReviewReport | None:
        mode = self._config.mode.lower().strip()
        if mode == "off":
            return None

        targets = tuple(item for item in self._config.targets if item in REVIEW_TARGETS)
        if not targets:
            targets = REVIEW_TARGETS

        findings: list[ReviewFinding] = []
        degraded_reasons: list[str] = []

        for target in targets:
            findings.extend(_run_rule_engine_target(target, context, block_map))

        status = ReviewStatus.COMPLETED
        if mode == "llm":
            model_findings, model_degraded = self._run_model_assisted(targets, context, block_map)
            findings.extend(model_findings)
            degraded_reasons.extend(model_degraded)
            if model_degraded:
                status = ReviewStatus.DEGRADED

        return IntelligentReviewReport(
            status=status,
            mode=mode,
            targets=targets,
            findings=tuple(findings),
            degraded_reasons=tuple(degraded_reasons),
            metadata={"local_model": self._config.local_model or ""},
        )

    def _run_model_assisted(
        self,
        targets: tuple[str, ...],
        context: DocumentContext,
        block_map: BlockMap,
    ) -> tuple[list[ReviewFinding], list[str]]:
        degraded_reasons: list[str] = []
        adapter = self._adapter
        if adapter is None:
            if not self._config.local_model:
                adapter = DisabledModelAdapter()
                degraded_reasons.append("local_model_not_configured")
            else:
                adapter = PlaceholderLocalModelAdapter(self._config.local_model)

        findings: list[ReviewFinding] = []
        for target in targets:
            task = _TARGET_TO_TASK[target]
            payload = _build_model_payload(task=task, target=target, context=context, block_map=block_map)
            try:
                rows = adapter.generate(task=task, payload=payload)
            except ModelAdapterError as exc:
                degraded_reasons.append(str(exc))
                continue

            parsed, reason = _parse_model_rows(rows)
            if reason:
                degraded_reasons.append(reason)
                continue
            findings.extend(parsed)

        return findings, degraded_reasons


def _run_rule_engine_target(target: str, context: DocumentContext, block_map: BlockMap) -> tuple[ReviewFinding, ...]:
    if target == "headings":
        return heading_structure_review(context, block_map)
    if target == "references":
        return reference_structure_review(context, block_map)
    if target == "pagination":
        return pagination_review(context, block_map)
    return ()


def _build_model_payload(
    *,
    task: str,
    target: str,
    context: DocumentContext,
    block_map: BlockMap,
) -> dict[str, object]:
    return {
        "task": task,
        "rule_ids": _task_rule_ids(task),
        "target": target,
        "context": {
            "paragraphs": list(context.paragraphs[:300]),
            "blocks": {
                key: {
                    "start_paragraph": value.start_paragraph,
                    "end_paragraph": value.end_paragraph,
                    "confidence": value.confidence,
                }
                for key, value in block_map.blocks.items()
            },
        },
        "constraints": {
            "auto_fix_allowed": False,
            "decision_enum": ["pass", "warn", "fail", "unable_to_judge"],
        },
    }


def _task_rule_ids(task: str) -> list[str]:
    if task == "heading_structure_review":
        return ["FR-4.8-01"]
    if task == "reference_structure_review":
        return ["FR-4.11-03", "FR-4.11-04"]
    if task == "pagination_review":
        return ["FR-4.15-01", "FR-4.15-03"]
    return []


def _parse_model_rows(rows: list[dict[str, object]]) -> tuple[list[ReviewFinding], str | None]:
    parsed: list[ReviewFinding] = []
    for row in rows:
        try:
            decision_text = str(row["decision"])
            source = str(row["source"])
            auto_fix_allowed = bool(row["auto_fix_allowed"])
            confidence = float(row["confidence"])
        except (KeyError, TypeError, ValueError):
            return [], "model_output_invalid_required_fields"

        if decision_text not in {item.value for item in ReviewDecision}:
            return [], "model_output_invalid_decision"
        if source != "local_model":
            return [], "model_output_invalid_source"
        if auto_fix_allowed:
            return [], "model_output_invalid_auto_fix_allowed"
        if confidence < 0.0 or confidence > 1.0:
            return [], "model_output_invalid_confidence"

        evidence_rows = row.get("evidence", [])
        if not isinstance(evidence_rows, list):
            return [], "model_output_invalid_evidence"

        evidence: list[ReviewEvidence] = []
        for item in evidence_rows:
            if not isinstance(item, dict) or "reason" not in item:
                return [], "model_output_invalid_evidence_item"
            evidence.append(
                ReviewEvidence(
                    reason=str(item["reason"]),
                    snippet=str(item.get("snippet", "")),
                    paragraph_index=_parse_optional_int(item.get("paragraph_index")),
                )
            )

        try:
            finding = ReviewFinding(
                rule_id=str(row["rule_id"]),
                block_id=str(row["block_id"]),
                block_type=str(row["block_type"]),
                target=str(row["target"]),
                decision=ReviewDecision(decision_text),
                confidence=confidence,
                evidence=tuple(evidence),
                suggestion=str(row.get("suggestion", "")),
                auto_fix_allowed=auto_fix_allowed,
                source=source,
            )
        except KeyError:
            return [], "model_output_invalid_required_fields"
        parsed.append(finding)

    return parsed, None


def _parse_optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
