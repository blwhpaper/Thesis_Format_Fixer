"""Profile engine for runtime composition and validation."""

from thesis_format_fixer.profiles.engine import (
    detect_profile_rule_key_gaps,
    EffectiveProfile,
    FormatProfile,
    compose_profiles,
    detect_rulebook_registry_drift,
    load_profile,
    validate_profile_keys,
)

__all__ = [
    "EffectiveProfile",
    "FormatProfile",
    "compose_profiles",
    "detect_rulebook_registry_drift",
    "detect_profile_rule_key_gaps",
    "load_profile",
    "validate_profile_keys",
]
