# Thesis Format Fixer Agent Entry

## Purpose

This file is the primary agent governance entrypoint for this repository.

## Unique Startup Chain

Every new implementation or review session must follow exactly this chain:

1. `AGENTS.md` or `CLAUDE.md`
2. `docs/roadmap.md`
3. `docs/governance/TASK_STATE.md`
4. `docs/governance/TASK_INDEX.md`
5. current task card
6. previous closeout
7. `git status --short --branch`

Do not skip forward based on chat history or model memory.

## Conflict Precedence

Use this strict precedence when instructions conflict:

`repo current state > AGENTS.md/CLAUDE.md > docs/roadmap.md > TASK_STATE > TASK_INDEX > current task card > previous closeout > chat history/model memory`

## Current Route

- `TASK-THESIS-P2-001`: completed
- `TASK-THESIS-P2-002`: completed
- `TASK-THESIS-P2-003`: completed
- `TASK-THESIS-P2-004`: completed
- `current/next = TASK-THESIS-P2-005 Anchor-aware Idempotency`

## Allowed Modification Scope

- `src/`
- `tests/`
- `docs/`
- `README.md`
- `CLAUDE.md`
- `AGENTS.md`

Only modify `README.md` / `CLAUDE.md` / `AGENTS.md` when governance-related.

## Forbidden Scope

- no private school rules
- no LaTeX pipeline
- no Microsoft Word COM dependency
- no Office.js dependency
- no hidden auto-rewrite
- Word-first
- profile-first

## Validation Commands

Run these before final closeout:

- `git status --short --branch`
- `git diff --check`
- `.venv/bin/python -m pytest -q`
- package/import smoke if available

Suggested smoke command:

- `PYTHONPATH=src .venv/bin/python -c "import thesis_format_fixer"`

## Runtime Notes

- `docs/governance/TASK_STATE.md` is the runtime task pointer.
- `docs/governance/TASK_INDEX.md` is the ordered governance registry.
- Historical governance audits remain in the repo for provenance, but they are not the runtime task pointer once superseded by the files above.
