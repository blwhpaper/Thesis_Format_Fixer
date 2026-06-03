# Roadmap

## TASK-001 (Current)

- Project skeleton and packaging.
- CLI contract and placeholder exit behavior.
- Rulebook/source files checked into repository.
- Smoke tests and bootstrap scripts.

## TASK-002 (Future, not included now)

- Build first detector set for A-class rules.
- Implement minimal check report output.
- Add fixture-based tests for deterministic checks.

## Later

- Incremental fix actions for safely auto-fixable rules.
- Human-in-the-loop report and override support for B-class rules.
- Coverage expansion and regression baselines.
- Generic Format Profile Engine skeleton (TASK-THESIS-OSS-004): done as minimal runtime composition/check foundation.
- Rulebook/runtime/profile source-of-truth alignment (TASK-THESIS-OSS-004A): default/profile/test path baseline aligned to v1.
- Profile drift report wired into check/report path (TASK-THESIS-OSS-004B): check output now exposes profile/rulebook/registry drift findings.
- Word Review Adapter Audit (TASK-THESIS-OSS-005A): done, established python-docx comment-only adapter boundary.
- Word Review Adapter Minimal Implementation (TASK-THESIS-OSS-005B): baseline comment-only adapter skeleton landed (apply/skip/duplicate/unsupported), no raw OOXML, no track changes.
- Word Review Adapter Real DOCX Integration Test (TASK-THESIS-OSS-005C): landed real python-docx save/reopen comment integration coverage while keeping adapter comment-only.
- Word Review Adapter Feasibility Freeze (TASK-THESIS-OSS-005): done, V1 boundary frozen as comment-only adapter contract and safety invariants; runtime wiring deferred as explicit opt-in.

- Review Profiles minimal strategy layer (TASK-THESIS-OSS-006): profile schema/validation/examples/tests added; runner/cli wiring deferred.
- OSS Release & Codex Application Readiness (TASK-THESIS-OSS-007): done, repository audited for public safety, package readiness, and Codex agent instructions frozen.
- Review E2E Contract Harness (TASK-THESIS-P2-001): done, established E2E contract test for structured findings mapping to WordReviewAdapter.
- CLI review --findings Minimal Write-back (TASK-THESIS-P2-002): done, added minimal opt-in CLI command to write structured findings into docx comments and generate report.
