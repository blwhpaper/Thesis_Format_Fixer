# Absorbable Principles Map (TASK-THESIS-OSS-003)

## Absorption Principles
1. **No direct code copy**: We strictly do not copy code from external open-source projects.
2. **External OSS implementation adoption requires license + architecture + maintenance review**.
3. **Absorb principles by default**: We extract architectural patterns, testing strategies, and edge-case handling concepts.
4. **Keep Word-first, profile-driven, safe A/B/C boundary**.

## Exclusions and Refined Adoptions
Based on our project differentiation:
- **Zotero CSL / GB/T 7714**:
  - implementation dependency: Reject
  - principle absorption: P0
  - reason: citation style should become declarative profile metadata, not a built-in citation manager.
- **Pandoc reference-doc / thesis templates** & **GB/T 7714 LaTeX/biblatex package**:
  - pipeline adoption: Reject
  - principle absorption: P1/P0 depending on item
  - reason: absorb style/content separation, template discipline, validation mindset; do not adopt LaTeX/Pandoc pipeline.
- **153lsr/thesis-typeset**: Absorb YAML/profile-driven thesis formatting structure.
- **Lang-Li-1/format-thesis**: Study docx operation categories and safety risks.
- **77AutumN/uestc-thesis-formatter**: Absorb profile mapping idea only.
- **opavon/ThesisTemplate**: Absorb Word style/template separation.
- **Blackbox SaaS checkers**: Reject (opaque logic, privacy concerns).
- **School templates directly hardcoded into the repository**: Reject (violates universal profile-driven goal).

## Concept Mapping

### Pattern: Separation of Detection and Mutation
- **Source Concept**: Linter design (e.g., ESLint).
- **Our Map**: Reinforces our architecture of `thesis_format_fixer.detectors` vs `thesis_format_fixer.formatters`. Ensures `check` mode remains read-only and side-effect free.

### Pattern: Configuration Inheritance
- **Source Concept**: Rule engines.
- **Our Map**: Informs how our YAML profiles should overlay custom university rules atop a `base_rulebook` without duplicating core structural validation logic.

### Pattern: Non-Destructive Mutations
- **Source Concept**: Code formatters (e.g., Prettier).
- **Our Map**: Validates our `never_overwrite_input_docx` safety boundary. Fosters the idea of keeping an AST-like representation of DOCX elements to apply changes deterministically.
