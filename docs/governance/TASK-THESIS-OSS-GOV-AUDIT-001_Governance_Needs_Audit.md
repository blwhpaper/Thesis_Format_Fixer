# TASK-THESIS-OSS-GOV-AUDIT-001 Governance Needs Audit

## 0. Audit Scope and Constraints

- Task: total-control governance needs audit and migratable governance pattern evaluation.
- Constraint: no root `CLAUDE.md` implementation in this task; no core code refactor; no formatter boundary expansion.
- Repository check result: **CLAUDE.md absent** (repository root).
- Audit baseline date: 2026-06-02.

## 1. Current Governance State

### 1.1 Existing governance entry points

- Product boundary and safety commitments are present in `README.md`:
  - Word-first (`.docx`) workflow.
  - `check` / `fix` / `batch-fix` split.
  - `fix` writes to new file and does not overwrite input.
  - preserve manual/fallback/error boundary.
- Rule sources and mapping chain are present:
  - `rules/FORMAT_RULEBOOK_v1.md` / `v2.md` / `v3.md`
  - `docs/RULE_TO_ENGINE_MAPPING_TASK-003.md`
  - `src/thesis_format_fixer/rules/registry.py`
- Profile-driven entry exists:
  - `rules/profiles/generic_university_zh.yaml`
  - `rules/profiles/sample_institution_zh.yaml`
- Runtime guardrails exist in code:
  - write whitelist: `src/thesis_format_fixer/rules/whitelist.py`
  - out-of-scope hard block: `src/thesis_format_fixer/rules/out_of_scope.py`
- Test governance exists via `pyproject.toml` and `tests/`.

### 1.2 Current governance inconsistencies / drift

- Legacy docs (`docs/roadmap.md`, `docs/architecture.md`, `docs/decisions.md`) still describe early TASK-001 stage and are no longer full runtime truth.
- Source-of-truth references are partially inconsistent:
  - `registry.py` declares `docs/RULE_TO_ENGINE_MAPPING_TASK-003.md` as source of truth.
  - profile files point to `rules/FORMAT_RULEBOOK_v3.md` as base rulebook.
  - `io/rulebook.py` default loader still points at `rules/FORMAT_RULEBOOK_v1.md`.
  - mapping doc section 1 still says v2 baseline, while later section includes v3 patch notes.
- No single governance control-plane file currently states:
  - governance precedence,
  - document freshness expectations,
  - task-state handoff contract.

## 2. Runtime Source of Truth and Invariants

### 2.1 Runtime source-of-truth (actual)

For execution behavior today, the most authoritative chain is:

1. `src/thesis_format_fixer/rules/registry.py` decision sets.
2. runtime guards in `rules/whitelist.py` + `rules/out_of_scope.py`.
3. runner/report behavior in `src/thesis_format_fixer/app/runner.py`.
4. profile policy intent in `rules/profiles/*.yaml`.
5. mapping/rulebook docs as human-facing provenance.

### 2.2 Must-keep invariants

- Word-first scope; do not evolve into LaTeX/citation-manager bridge.
- Profile-driven behavior, including institution-level adaptation and temporary overrides.
- Rulebook/mapping as policy provenance; runtime registry/guards as executable contract.
- Minimal safe fixer: non-whitelisted/high-risk write-back remains blocked.
- Report-first and manual-review-preserving output (`detected_not_auto_modified`, `manual_review_required`, degrade path).
- Manual/fallback/error boundaries must remain explicit and testable.

## 3. Does this project now need root CLAUDE.md?

## Judgment: **Yes, minimally needed now**.

Reason:

- Governance information is distributed and partially stale; contributor/agent behavior can drift.
- Upcoming TASK-004/005A/005B/005/006/007 increases integration complexity; a thin root control layer is needed before those tasks to reduce accidental boundary breaks.
- Existing safeguards are code-level, but governance-level precedence and task handoff are not centralized.

## 4. What root CLAUDE.md should and should not do

### 4.1 Should do (minimal responsibilities)

- Define governance precedence (runtime > tests > mapping docs > legacy notes).
- Freeze product boundary: Word-first, profile-driven, report-first, minimal safe fixer.
- Declare forbidden expansions for current phase (no LaTeX bridge, no citation-manager scope takeover, no hidden auto-rewrite of student content).
- Define task execution hygiene:
  - smallest-change-first,
  - no silent scope creep,
  - preserve manual/fallback/error boundaries,
  - evidence-linked doc updates when runtime truth changes.

### 4.2 Should not do

- Not a replacement for rulebook content.
- Not a second technical spec duplicating `RULE_TO_ENGINE_MAPPING` or runtime registry.
- Not a heavy workflow engine with mandatory multi-file status bureaucracy.
- Not a policy to auto-edit thesis semantic content.

## 5. Migratable vs Non-migratable governance patterns

### 5.1 Migratable (from BTC_WATCHFLOW / thesis workflow experience)

- Single control-plane entry for contributor/agent operating rules.
- Explicit source-of-truth precedence and anti-drift checks.
- Lightweight task-state continuity focused on next actionable boundary.
- Risk register style focused on product-boundary violations and unsafe automation.

### 5.2 Non-migratable (or only partially migratable)

- Heavy enterprise workflow layers (`PLAN.md` + dense state machines + frequent chore updates) as default.
- Cross-domain abstractions that dilute Word-first thesis fixing.
- Governance that assumes multi-system orchestration (not needed for current OSS scope).
- Over-prescriptive reviewer/formatter meta-rules that duplicate executable tests.

## 6. Recommended minimal governance layer (for next task)

Recommended minimal set for `TASK-THESIS-OSS-GOV-001`:

1. Root `CLAUDE.md` (required, concise).
2. `docs/governance/TASK_INDEX.md` (optional but recommended): ordered task spine + status.
3. `docs/governance/CHANGE_LOG.md` (optional): only architecture/governance-impact entries, not every minor edit.

Not required now:

- `GOVERNANCE/PLAN.md` as mandatory orchestrator.
- `TASK_STATE.json` as hard dependency.

Rationale:

- Current repo is still a lightweight OSS tool with clear code paths and tests.
- Add only what prevents drift and improves handoff; avoid introducing maintenance overhead that slows implementation.

## 7. Heavy governance to avoid now

- Mandatory machine-state files for every task transition.
- Multi-layer duplicated rule catalogs (same decision duplicated across 3+ files).
- Governance rules that require updating many artifacts for one small change.
- Any governance trigger that can be misused as justification for automatic content rewriting.

## 8. Execution advice for TASK-THESIS-OSS-GOV-001

Proceed, but keep the deliverable minimal and bounded:

- Create root `CLAUDE.md` as control-plane, not content-plane.
- Include an explicit “do-not-expand” section for non-goals.
- Define update protocol when rule decisions change:
  - runtime registry/tests first,
  - then mapping/rulebook provenance sync.
- Require that legacy docs (`roadmap/architecture/decisions`) are either marked historical or linked to current governance index to reduce confusion.

## 9. Impact on subsequent tasks

### TASK-THESIS-OSS-004

- Clarifies rulebook/runtime reconciliation criteria and precedence.
- Reduces risk of parallel “truths” between mapping doc and registry decisions.

### TASK-THESIS-OSS-005A / 005B / 005

- Keeps review adapter scoped to review/comment pipeline, not uncontrolled auto-fix expansion.
- Enforces `auto_fix_allowed=false` semantics for review findings.

### TASK-THESIS-OSS-006

- Supports profile-level review strategy variants (English / humanities / STEM) without breaking core safety invariants.

### TASK-THESIS-OSS-007

- Improves OSS release readiness by making governance expectations explicit and transferable to external contributors.

## 10. Risk List

- R1: Source-of-truth drift between rulebook/mapping/registry/profile defaults.
- R2: Legacy docs interpreted as active contract, causing wrong implementation decisions.
- R3: Governance overgrowth slows delivery and discourages OSS contributors.
- R4: Review pipeline unintentionally treated as auto-fix authority.
- R5: External format-tool research (LaTeX/Overleaf/SciSpace/EndNote/Zotero/Pandoc) over-influences scope and shifts product away from Word-first.

## 11. Next-task boundary

`TASK-THESIS-OSS-GOV-AUDIT-001` ends at audit and recommendations.

Not included in this task:

- creating root `CLAUDE.md`,
- introducing governance runtime/state machinery,
- changing formatter behavior,
- changing review auto-fix boundary,
- broad rewriting of existing docs.

Recommended next task: `TASK-THESIS-OSS-GOV-001` with minimal-control-plane implementation only.
