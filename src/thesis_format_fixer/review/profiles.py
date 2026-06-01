"""Review profile skeleton for TASK-THESIS-OSS-006.

This module defines a review-policy layer that is independent from format profiles.
It only models structured finding strategies and explicit write-back safety boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

VALID_SEVERITIES = {"info", "warning", "error", "critical"}
VALID_CATEGORIES = {
    "language",
    "argumentation",
    "evidence",
    "citation",
    "terminology",
    "structure",
    "methodology",
    "data_integrity",
    "compliance",
}
VALID_ANCHOR_STRATEGIES = {
    "paragraph",
    "paragraph_run",
    "keyword_in_paragraph",
}


class ReviewProfileValidationError(ValueError):
    """Raised when a review profile breaks contract invariants."""


@dataclass(frozen=True, slots=True)
class ReviewRule:
    rule_id: str
    category: str
    severity: str
    message_template: str
    anchor_strategy: str
    comment_allowed: bool
    auto_rewrite_allowed: bool


@dataclass(frozen=True, slots=True)
class ReviewProfile:
    profile_id: str
    display_name: str
    schema_version: int
    language: str
    scope: str
    rules: tuple[ReviewRule, ...]
    raw: dict[str, Any]


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
            item_content = line[2:].strip()
            if not isinstance(container, list):
                raise ValueError("invalid yaml list structure")
            if ":" in item_content:
                key, _, value = item_content.partition(":")
                value = value.strip()
                item_dict: dict[str, Any] = {key.strip(): _parse_scalar(value)}
                container.append(item_dict)
                stack.append((indent + 1, item_dict))
            else:
                container.append(_parse_scalar(item_content))
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


def load_review_profile(path: Path) -> ReviewProfile:
    data = _load_yaml_subset(path.read_text(encoding="utf-8"))
    rules = data.get("review_rules", [])
    if not isinstance(rules, list):
        raise ReviewProfileValidationError("review_rules must be a list")

    parsed_rules: list[ReviewRule] = []
    for item in rules:
        if not isinstance(item, dict):
            raise ReviewProfileValidationError("review_rules item must be a mapping")
        parsed_rules.append(
            ReviewRule(
                rule_id=str(item.get("rule_id", "")),
                category=str(item.get("category", "")),
                severity=str(item.get("severity", "")),
                message_template=str(item.get("message_template", "")),
                anchor_strategy=str(item.get("anchor_strategy", "")),
                comment_allowed=item.get("comment_allowed"),
                auto_rewrite_allowed=item.get("auto_rewrite_allowed"),
            )
        )

    profile = ReviewProfile(
        profile_id=str(data.get("profile_id", "")),
        display_name=str(data.get("display_name", "")),
        schema_version=int(data.get("schema_version", 0) or 0),
        language=str(data.get("language", "")),
        scope=str(data.get("scope", "")),
        rules=tuple(parsed_rules),
        raw=data,
    )
    validate_review_profile(profile)
    return profile


def validate_review_profile(profile: ReviewProfile) -> tuple[str, ...]:
    errors: list[str] = []

    if not profile.profile_id:
        errors.append("missing:profile_id")
    if not profile.display_name:
        errors.append("missing:display_name")
    if profile.schema_version <= 0:
        errors.append("invalid:schema_version")
    if not profile.rules:
        errors.append("missing:review_rules")

    for idx, rule in enumerate(profile.rules):
        head = f"review_rules[{idx}]"
        if not rule.rule_id:
            errors.append(f"missing:{head}.rule_id")
        if rule.category not in VALID_CATEGORIES:
            errors.append(f"invalid:{head}.category:{rule.category}")
        if rule.severity not in VALID_SEVERITIES:
            errors.append(f"invalid:{head}.severity:{rule.severity}")
        if not rule.message_template:
            errors.append(f"missing:{head}.message_template")
        if rule.anchor_strategy not in VALID_ANCHOR_STRATEGIES:
            errors.append(f"invalid:{head}.anchor_strategy:{rule.anchor_strategy}")
        if not isinstance(rule.comment_allowed, bool):
            errors.append(f"missing_or_invalid:{head}.comment_allowed")
        if rule.comment_allowed is False:
            errors.append(f"invalid:{head}.comment_allowed:false")
        if rule.auto_rewrite_allowed is not False:
            errors.append(f"invalid:{head}.auto_rewrite_allowed:{rule.auto_rewrite_allowed}")

    if errors:
        raise ReviewProfileValidationError("; ".join(errors))
    return tuple()
