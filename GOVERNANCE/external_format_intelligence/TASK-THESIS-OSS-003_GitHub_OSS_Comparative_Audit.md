# GitHub OSS Comparative Audit (TASK-THESIS-OSS-003)

## Project Differentiation
Thesis_Format_Fixer maintains a strict differentiation from other ecosystem tools:
- **Word-first**: Focuses explicitly on `.docx` formats, rather than Markdown or LaTeX compilation.
- **Profile-driven**: Rules are externalized to profile configurations, decoupled from hardcoded logic.
- **Student override-aware**: Recognizes manual formatting overrides and avoids destructive changes.
- **Safe auto-fix**: Strictly adheres to A/B/C safety boundaries; creates a new file rather than overwriting.
- **Audit report**: Generates comprehensive `.json` and `.md` reports of formatting issues.

## OSS Audit Table

| repo_or_tool | type | primary_scenario | input_output | edits_existing_docx_or_template_only | license_or_access_note | strengths | limitations | absorption_priority | absorption_decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 153lsr/thesis-typeset | docx formatter | Automated Word formatting | docx -> docx | Edits existing | Open Source | Good regex-based heading detection | Hardcoded to specific school | P0 | Absorb YAML/profile-driven thesis formatting structure; do not copy school-specific rules or implementation |
| Lang-Li-1/format-thesis | docx formatter | Word checking | docx -> docx | Edits existing | Open Source | Clean use of python-docx | Limited basic margins/fonts | P1 | Study docx operation categories and safety risks; do not copy implementation |
| 77AutumN/uestc-thesis-formatter | Word-to-LaTeX/Pandoc pipeline | Word format fixing | docx -> docx | Edits existing | Open Source | School-specific edge cases covered | Very tightly coupled to UESTC | P2 | Absorb profile mapping idea only; reject pipeline adoption |
| obilogy/toc-formatter | docx formatter | TOC rebuilding | docx -> docx | Edits existing | Open Source | Automates TOC generation | Brittle on complex headings | P2 | Study localized TOC repair boundary; do not copy implementation snippets |
| opavon/ThesisTemplate | Word template | Boilerplate DOCX | null -> docx | Template only | Open Source | Standardized visual baseline | No automatic fixing capability | P1 | Absorb Word style/template separation; do not adopt static templates directly |
| cagix/pandoc-thesis | Pandoc pipeline | Markdown to Thesis | md -> pdf/docx | Template only | Open Source | Style/content separation | Pipeline adoption: Reject | P1 | Absorb style/content separation |
| maehr/academic-pandoc-template | Pandoc pipeline | Academic writing | md -> pdf/docx | Template only | Open Source | Robust reference handling | Pipeline adoption: Reject | P1 | Absorb template discipline |
| dfolio/pandoc-df-thesis-template | Pandoc pipeline | Thesis writing | md -> pdf/docx | Template only | Open Source | Good validation mindset | Pipeline adoption: Reject | P0 | Absorb validation mindset |
| Zotero CSL GB/T 7714 / citation-style-language styles | Citation styles | Reference styling | metadata -> text | Template only | Open Source | Standardized citation metadata | Implementation dependency: Reject | P0 | Citation style should become declarative profile metadata |
| GB/T 7714 LaTeX/biblatex package | LaTeX package | Reference styling | bib -> pdf | Template only | Open Source | High fidelity styling | Pipeline adoption: Reject | P0 | Absorb declarative standard |
