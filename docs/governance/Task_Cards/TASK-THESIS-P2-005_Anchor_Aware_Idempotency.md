# TASK-THESIS-P2-005 Anchor-aware Idempotency

## 1. Task ID / Title

- Task ID: `TASK-THESIS-P2-005`
- Title: `Anchor-aware Idempotency`

## 2. Background and Predecessor

- Predecessor: `TASK-THESIS-P2-004`
- `TASK-THESIS-P2-004` completed the Review Report Artifact stage.
- `docs/architecture/TASK-THESIS-OSS-005_Word_Review_Adapter_Feasibility_Freeze.md` already identifies anchor-aware idempotency improvements as a future implementation task.
- This card is the runtime handoff target for future sessions that start with `P2-005 开工` or `TASK-THESIS-P2-005 开工`.

## 3. Task Objective

Implement anchor-aware idempotency improvements for the Word review comment pipeline while preserving the frozen boundaries:

- comments-only write-back
- no body text rewrite
- explicit skip/report behavior when anchors are missing or unsafe

## 4. Allowed Files / Directories

- `src/`
- `tests/`
- `docs/`
- governance files only when needed for task closeout or boundary clarification

## 5. Forbidden Scope

- no private school rules
- no LaTeX pipeline
- no Microsoft Word COM dependency
- no Office.js dependency
- no hidden auto-rewrite
- no Track Changes implementation
- no profile/business expansion beyond anchor-aware idempotency
- do not advance to `P2-006`

## 6. Expected Implementation Outputs

- Anchor-aware duplicate detection or equivalent idempotent matching behavior in the review comment path
- Stable handling for repeated application against the same document
- Explicit result reporting for added/skipped/duplicate/unsupported outcomes
- Minimal doc updates if runtime behavior or task closeout requires them

## 7. Expected Tests

- Unit tests covering idempotent re-application behavior
- Tests for missing or moved anchors
- Regression coverage preserving comments-only and no-body-rewrite boundaries
- Update existing review adapter tests instead of replacing boundary assertions

## 8. Validation Commands

- `git status --short --branch`
- `git diff --check`
- `.venv/bin/python -m pytest -q`
- package/import smoke if available

Suggested smoke command:

- `PYTHONPATH=src .venv/bin/python -c "import thesis_format_fixer"`

## 9. Closeout Requirements

Future `TASK-THESIS-P2-005` closeout must include:

- changed files
- validation commands and results
- unresolved risks or follow-up debt
- next recommended task
- explicit confirmation that Word-first, profile-first, and comments-only boundaries remain intact

## 10. Governance Boundary Statement

This card defines the future `P2-005` business task. This governance task must not implement `P2-005`.
