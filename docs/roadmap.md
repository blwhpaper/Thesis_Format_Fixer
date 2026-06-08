# Roadmap

## Runtime Governance Pointer

This file is part of the required startup chain:

1. `AGENTS.md` / `CLAUDE.md`
2. `docs/roadmap.md`
3. `docs/governance/TASK_STATE.md`
4. `docs/governance/TASK_INDEX.md`
5. current task card
6. previous closeout
7. `git status --short --branch`

Current runtime task pointer lives in `docs/governance/TASK_STATE.md`.

## Route Status

- `TASK-THESIS-P2-001`: completed
- `TASK-THESIS-P2-002`: completed
- `TASK-THESIS-P2-003`: completed
- `TASK-THESIS-P2-004`: completed
- `current/next = TASK-THESIS-P2-005 Anchor-aware Idempotency`

## Current Task Materials

- current task card:
  `docs/governance/Task_Cards/TASK-THESIS-P2-005_Anchor_Aware_Idempotency.md`
- previous closeout:
  `docs/governance/Task_Closeouts/TASK-THESIS-P2-004_Closeout.md`
- task registry:
  `docs/governance/TASK_INDEX.md`

## Historical Milestones

The items below are retained as historical/provenance milestones and are superseded as runtime task truth by the governance files above.

- Generic Format Profile Engine skeleton (`TASK-THESIS-OSS-004`): done as minimal runtime composition/check foundation.
- Rulebook/runtime/profile source-of-truth alignment (`TASK-THESIS-OSS-004A`): default/profile/test path baseline aligned to v1.
- Profile drift report wired into check/report path (`TASK-THESIS-OSS-004B`): check output now exposes profile/rulebook/registry drift findings.
- Word Review Adapter Audit (`TASK-THESIS-OSS-005A`): done, established python-docx comment-only adapter boundary.
- Word Review Adapter Minimal Implementation (`TASK-THESIS-OSS-005B`): baseline comment-only adapter skeleton landed (apply/skip/duplicate/unsupported), no raw OOXML, no track changes.
- Word Review Adapter Real DOCX Integration Test (`TASK-THESIS-OSS-005C`): landed real python-docx save/reopen comment integration coverage while keeping adapter comment-only.
- Word Review Adapter Feasibility Freeze (`TASK-THESIS-OSS-005`): done, V1 boundary frozen as comment-only adapter contract and safety invariants; runtime wiring deferred as explicit opt-in.
- Review Profiles minimal strategy layer (`TASK-THESIS-OSS-006`): profile schema/validation/examples/tests added; runner/cli wiring deferred.
- OSS Release & Codex Application Readiness (`TASK-THESIS-OSS-007`): done, repository audited for public safety, package readiness, and Codex agent instructions frozen.
- Review E2E Contract Harness (`TASK-THESIS-P2-001`): done, established E2E contract test for structured findings mapping to WordReviewAdapter.
- CLI review `--findings` Minimal Write-back (`TASK-THESIS-P2-002`): done, added minimal opt-in CLI command to write structured findings into docx comments and generate report.
- Real Sample Review Smoke Test (`TASK-THESIS-P2-003`): done, implemented dynamic, sanitized, realistic `.docx` fixture to smoke test the review pipeline without hardcoded private rules.
- Review Report Artifact (`TASK-THESIS-P2-004`): completed; runtime closeout is `docs/governance/Task_Closeouts/TASK-THESIS-P2-004_Closeout.md`.
