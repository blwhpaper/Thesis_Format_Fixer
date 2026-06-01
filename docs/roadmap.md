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
