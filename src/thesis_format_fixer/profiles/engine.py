"""Minimal generic profile engine for runtime composition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from thesis_format_fixer.contracts.rule_types import RuleDecision
from thesis_format_fixer.io.rulebook import ROOT_DIR, RULEBOOK_PATH
from thesis_format_fixer.rules.registry import RuleRegistry, SOURCE_OF_TRUTH


def _parse_scalar(value: str) -> Any:
    if value == "{}":
        return {}
    if value == "[]":
        return []
    if value == "true":
        return True
    if value == "false":
        return False
    if value.isdigit():
        return int(value)
    return value


def _load_yaml_subset(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        container = stack[-1][1]
        if line.startswith("- "):
            if not isinstance(container, list):
                raise ValueError("invalid yaml list structure")
            container.append(_parse_scalar(line[2:].strip()))
            i += 1
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"invalid yaml line: {raw}")
        key = key.strip()
        value = value.strip()
        if value == "|":
            block_lines: list[str] = []
            i += 1
            while i < len(lines):
                nxt = lines[i]
                nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                if nxt.strip() and nxt_indent <= indent:
                    break
                block_lines.append(nxt[indent + 2 :] if len(nxt) >= indent + 2 else "")
                i += 1
            if not isinstance(container, dict):
                raise ValueError("invalid yaml mapping structure")
            container[key] = "\n".join(block_lines).strip()
            continue
        if value == "":
            next_nonempty = ""
            j = i + 1
            while j < len(lines):
                candidate = lines[j].strip()
                if candidate and not candidate.startswith("#"):
                    next_nonempty = candidate
                    break
                j += 1
            next_container: Any = [] if next_nonempty.startswith("- ") else {}
            if not isinstance(container, dict):
                raise ValueError("invalid yaml mapping structure")
            container[key] = next_container
            stack.append((indent, next_container))
            i += 1
            continue
        if not isinstance(container, dict):
            raise ValueError("invalid yaml mapping structure")
        container[key] = _parse_scalar(value)
        i += 1
    return root


def _to_rule_decision(value: str) -> RuleDecision:
    normalized = value.strip().upper().replace(" ", "_")
    if normalized == "AUTO_FIX":
        return RuleDecision.AUTO_FIX
    if normalized == "AUTO_CHECK":
        return RuleDecision.AUTO_CHECK
    if normalized == "REPORT_ONLY":
        return RuleDecision.REPORT_ONLY
    if normalized in {"OUT_OF_V1", "OUT_OF_V_1"}:
        return RuleDecision.OUT_OF_V1
    raise ValueError(f"unknown decision: {value}")


@dataclass(frozen=True, slots=True)
class FormatProfile:
    profile_id: str
    display_name: str
    base_rulebook: str
    rule_decisions: dict[str, RuleDecision]
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class EffectiveProfile:
    profile_id: str
    base_rulebook: str
    effective_rule_decisions: dict[str, RuleDecision]
    unknown_rule_keys: tuple[str, ...]
    invalid_decisions: dict[str, str]
    conflicts: tuple[str, ...]
    boundary_violations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "base_rulebook": self.base_rulebook,
            "effective_rule_decisions": {
                key: decision.name for key, decision in sorted(self.effective_rule_decisions.items())
            },
            "unknown_rule_keys": list(self.unknown_rule_keys),
            "invalid_decisions": dict(sorted(self.invalid_decisions.items())),
            "conflicts": list(self.conflicts),
            "boundary_violations": list(self.boundary_violations),
        }


def load_profile(path: Path) -> FormatProfile:
    data = _load_yaml_subset(path.read_text(encoding="utf-8"))
    ruleset = data.get("ruleset", {})
    runtime = data.get("runtime", {})
    overrides = runtime.get("rule_decisions", {}) if isinstance(runtime, dict) else {}
    parsed_overrides: dict[str, RuleDecision] = {}
    for rule_id, decision in overrides.items():
        parsed_overrides[str(rule_id)] = _to_rule_decision(str(decision))
    return FormatProfile(
        profile_id=str(data.get("profile_id", "")),
        display_name=str(data.get("display_name", "")),
        base_rulebook=str(ruleset.get("base_rulebook", "")),
        rule_decisions=parsed_overrides,
        raw=data,
    )


def validate_profile_keys(profile: FormatProfile, registry: RuleRegistry | None = None) -> tuple[str, ...]:
    active_registry = registry or RuleRegistry()
    known = set(active_registry.rule_ids())
    unknown = sorted(rule_id for rule_id in profile.rule_decisions if rule_id not in known)
    return tuple(unknown)


def compose_profiles(
    base: FormatProfile,
    institution: FormatProfile | None = None,
    overrides: dict[str, str] | None = None,
    registry: RuleRegistry | None = None,
) -> EffectiveProfile:
    active_registry = registry or RuleRegistry()
    known_rule_ids = set(active_registry.rule_ids())
    effective: dict[str, RuleDecision] = {}
    conflicts: set[str] = set()
    unknown: set[str] = set()
    invalid_decisions: dict[str, str] = {}
    boundary_violations: set[str] = set()

    def apply_layer(layer_decisions: dict[str, RuleDecision], layer_name: str) -> None:
        for rule_id, decision in layer_decisions.items():
            if rule_id not in known_rule_ids:
                unknown.add(rule_id)
                continue
            registry_decision = active_registry.get_metadata(rule_id).v1_decision
            if registry_decision is not RuleDecision.AUTO_FIX and decision is RuleDecision.AUTO_FIX:
                boundary_violations.add(rule_id)
                continue
            previous = effective.get(rule_id)
            if previous is not None and previous is not decision:
                conflicts.add(f"{rule_id}:{previous.name}->{decision.name}@{layer_name}")
            effective[rule_id] = decision

    apply_layer(base.rule_decisions, "base")
    if institution is not None:
        apply_layer(institution.rule_decisions, "institution")
    if overrides:
        parsed: dict[str, RuleDecision] = {}
        for rule_id, decision_text in overrides.items():
            try:
                parsed[rule_id] = _to_rule_decision(decision_text)
            except ValueError:
                invalid_decisions[rule_id] = decision_text
        apply_layer(parsed, "overrides")

    return EffectiveProfile(
        profile_id=institution.profile_id if institution is not None else base.profile_id,
        base_rulebook=institution.base_rulebook if institution is not None else base.base_rulebook,
        effective_rule_decisions=effective,
        unknown_rule_keys=tuple(sorted(unknown)),
        invalid_decisions=invalid_decisions,
        conflicts=tuple(sorted(conflicts)),
        boundary_violations=tuple(sorted(boundary_violations)),
    )


def detect_rulebook_registry_drift(profile: FormatProfile) -> tuple[str, ...]:
    issues: list[str] = []
    expected_rulebook = str(RULEBOOK_PATH.relative_to(ROOT_DIR))
    if profile.base_rulebook and profile.base_rulebook != expected_rulebook:
        issues.append(f"base_rulebook_mismatch:{profile.base_rulebook}!={expected_rulebook}")
    if not (ROOT_DIR / SOURCE_OF_TRUTH).exists():
        issues.append(f"registry_source_missing:{SOURCE_OF_TRUTH}")
    if profile.base_rulebook and not (ROOT_DIR / profile.base_rulebook).exists():
        issues.append(f"profile_rulebook_missing:{profile.base_rulebook}")
    return tuple(issues)
