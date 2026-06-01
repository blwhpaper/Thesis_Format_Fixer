# Profile Engine Implications (TASK-THESIS-OSS-003)

## Context
This document directly serves the upcoming **TASK-THESIS-OSS-004** by outlining how external intelligence and current architectural state impact the evolution of the Profile Engine.

## Current State Observations
The current profile schema (`generic_university_zh.yaml`) is a lightweight text-anchor validation:
- It declares a `base_rulebook`.
- It sets global boolean flags for A/B/C classes (`a_class_auto_fix: true`, etc.).
- It establishes safety boundaries.

## Implications for TASK-THESIS-OSS-004

### 1. Granular Rule Overrides
The engine must move beyond global boolean flags. TASK-004 must design a mechanism for the profile to override specific formatting tokens (e.g., font size, margins, paragraph spacing) while inheriting the base rulebook's structure.

### 2. Student Override Awareness
Direct formatting is evidence, not automatic permission. Preserve only explicit profile/student override; otherwise safely normalize A-class or report B/C issue.

### 3. A/B/C Execution Mapping
The Profile Engine must bind the profile definitions to the `app/runner.py`. The engine must output a clear decision tree to the detectors and formatters:
- What constitutes an A-class rule for this specific profile?
- How are B-class warnings surfaced to the audit report without triggering a formatter?

### 4. Machine-Readable Rules
As hinted in `docs/architecture.md`, the YAML schema must evolve into a machine-readable format that `thesis_format_fixer.rules` can deserialize into rigid internal models implemented with the smallest sufficient dependency strategy, eliminating ambiguous text-anchor validation.
