# Thesis Format Fixer - Contributor & Agent Protocol

## 1. Project Purpose

Word-first thesis format fixer, public OSS safe, configurable profiles.

## 2. Unique Startup Chain

Every new implementation or review session must follow exactly this chain:

1. `AGENTS.md` or `CLAUDE.md`
2. `docs/roadmap.md`
3. `docs/governance/TASK_STATE.md`
4. `docs/governance/TASK_INDEX.md`
5. current task card
6. previous closeout
7. `git status --short --branch`

Do not treat chat history or model memory as a valid shortcut.

## 3. Conflict Precedence

Use this strict precedence when instructions conflict:

`repo current state > AGENTS.md/CLAUDE.md > docs/roadmap.md > TASK_STATE > TASK_INDEX > current task card > previous closeout > chat history/model memory`

## 4. Current Route

- `TASK-THESIS-P2-001`: completed
- `TASK-THESIS-P2-002`: completed
- `TASK-THESIS-P2-003`: completed
- `TASK-THESIS-P2-004`: completed
- `current/next = TASK-THESIS-P2-005 Anchor-aware Idempotency`

## 5. Runtime Source of Truth

- repo current state is authoritative for what actually exists
- original specification files remain policy provenance
- rulebook is the engineering translation layer
- tests are behavioral regression constraints
- generated outputs must not be reverse-engineered to infer rules
- historical audits may explain why decisions were made, but they are not the runtime task pointer once superseded

## 6. Allowed Modification Scope

- `src/`
- `tests/`
- `docs/`
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`

Only modify `README.md` / `CLAUDE.md` / `AGENTS.md` when governance-related.

## 7. Forbidden Scope

- no private school rules
- no LaTeX pipeline
- no Microsoft Word COM dependency
- no Office.js dependency
- no hidden auto-rewrite
- Word-first
- profile-first

## 8. Engineering Invariants

- preserve original document content
- formatting changes must be auditable
- no silent content rewriting
- manual/fallback/error boundaries must be preserved
- high-risk Word structure changes should be report/check first, not auto-fix first
- profile/rule conflict must be explicit

## 9. Branch/Task Rule

- one task = one short-lived branch
- no long-lived business branch
- main must stay releasable

## 10. Validation Protocol

Before committing or finalizing changes, run:

- `git status --short --branch`
- `git diff --check`
- `.venv/bin/python -m pytest -q`
- package/import smoke if available

Suggested smoke command:

- `PYTHONPATH=src .venv/bin/python -c "import thesis_format_fixer"`

Inspect the diff before commit and report any skipped validation with reason.

## 11. Closeout Protocol

When finishing a task, the closeout must include:

- changed files
- validation commands/results
- unresolved architecture debt or governance gaps
- next task recommendation

## 12. Runtime Governance Files

- `docs/governance/TASK_STATE.md` is the runtime task pointer
- `docs/governance/TASK_INDEX.md` is the ordered task registry
- task cards define current task scope and acceptance
- closeouts define previous handoff context
