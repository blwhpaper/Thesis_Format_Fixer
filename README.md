# thesis-format-fixer

`thesis-format-fixer` is a Python CLI project for checking and fixing **English graduation thesis DOCX formatting** against a rulebook.

Current stage: **project skeleton only** (TASK-001). No real formatting fix logic is implemented yet.

## Project Purpose

- Check and fix DOCX formatting issues for English graduation theses.
- Focus on **format compliance only**.
- Do **not** evaluate content quality, argument quality, grammar quality, or academic merit.

## Rule Boundary (A/B/C)

- A. **Machine-checkable structural/style rules**: targeted scope for this project.
- B. **Partially machine-checkable rules**: may require manual confirmation or reviewer override in future tasks.
- C. **Content-quality and academic judgment rules**: out of scope.

## Not Supported (Current)

- DOCX formatting repair logic (not implemented yet).
- Cover-page reconstruction.
- Page numbering / section / footnote reflow.
- GUI.
- Any TASK-002+ scope.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## CLI Examples

```bash
thesis-format-fixer check samples/input/demo.docx
thesis-format-fixer fix samples/input/demo.docx --out samples/output/demo.fixed.docx
```

Current behavior: validates arguments, prints `待实现`, exits with meaningful status code.

## Rule Sources in Repository

- `rules/FORMAT_RULEBOOK_v1.md`
- `rules/sources/10.1论文封皮.pdf`
- `rules/sources/8. 毕业论文正文写作格式要求.docx`

## Repository Layout

- `src/` source-layout Python package
- `rules/` rulebook and source documents
- `docs/` architecture and planning notes
- `tests/` smoke tests
- `scripts/` local bootstrap/demo scripts
- `samples/` sample IO/report directories
