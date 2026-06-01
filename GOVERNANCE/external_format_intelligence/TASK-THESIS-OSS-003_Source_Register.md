# Source Register (TASK-THESIS-OSS-003)

## Local Repository Evidence
The following internal files establish the current baseline architecture, decisions, and rule scope for Thesis_Format_Fixer:
- `README.md`: Defines project positioning, CLI/GUI usage, and safe fix boundaries (A/B/C classes).
- `docs/architecture.md`: Outlines the `src` layout, thin CLI, placeholder runner, and extension points.
- `docs/decisions.md`: Records key architectural decisions such as `src` layout and repository-tracked rulebooks.
- `docs/rule_scope.md`: Defines the deterministic vs. human-reviewable scope of rules (A/B/C classes).
- `rules/FORMAT_RULEBOOK_v1.md` through `rules/FORMAT_RULEBOOK_v3.md`: Establish the evolution of formatting rules, precedence, and evidence principles.
- `rules/profiles/*.yaml`: Establish the schema version and generic configuration structure for profile-driven formatting.

*Note: `CLAUDE.md` was not found in the repository root at audit time.*

## External Evidence
The following categories of external intelligence were audited to inform the architectural evolution of Thesis_Format_Fixer:
- `153lsr/thesis-typeset`
- `Lang-Li-1/format-thesis`
- `77AutumN/uestc-thesis-formatter`
- `opavon/ThesisTemplate`
- Pandoc reference-doc / thesis templates
- Zotero CSL / GB/T 7714
- GB/T 7714 LaTeX/biblatex package
