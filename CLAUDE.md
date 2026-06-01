# Thesis Format Fixer - Contributor & Agent Protocol

## 1. Project Purpose
Word-first thesis format fixer, public OSS safe, configurable profiles.

## 2. Runtime Source of Truth
- 原始规范文件优先 (Original specification files take precedence)
- rulebook 是工程化翻译层 (The rulebook is an engineering translation layer)
- tests 是行为回归约束 (Tests serve as behavioral regression constraints)
- generated outputs 不得反推规则 (Generated outputs must not be reverse-engineered to infer rules)

## 3. Required Startup Protocol
When starting a new session or task, you must strictly follow this order:
1. 先读 CLAUDE.md (Read this file first).
2. 查 `git status` (Check current git status).
3. 识别当前任务、分支、允许修改范围 (Identify current task, branch, and allowed modification scope).
4. 审计架构、数据流、职责边界、风险 (Audit architecture, data flow, responsibility boundaries, and risks).
5. 再做最小修改 (Only then, make the minimal necessary modifications).

## 4. Engineering Invariants
- preserve original document content
- formatting changes must be auditable
- no silent content rewriting
- manual/fallback/error boundaries must be preserved
- high-risk Word structure changes should be report/check first, not auto-fix first
- profile/rule conflict must be explicit

## 5. Branch/Task Rule
- one task = one short-lived branch
- no long-lived business branch
- main must stay releasable

## 6. Validation Protocol
Before committing or finalizing changes, you must:
- run relevant pytest
- run `git diff --check`
- inspect `git diff` before commit
- report skipped validation with reason

## 7. Closeout Protocol
When finishing a task, your final report must include:
- changed files
- validation commands/results
- unresolved architecture debt
- next task recommendation

## 8. Current Roadmap Pointer
- TASK-THESIS-OSS-004 Generic Format Profile Engine is next after governance setup unless user overrides
- do not jump to review adapter before profile engine unless explicitly instructed
