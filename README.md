# thesis-format-fixer

`thesis-format-fixer` is a Python CLI project for checking and fixing **English graduation thesis DOCX formatting** against a rulebook.

Current stage: **TASK-005 report + batch pipeline skeleton**.

## Project Purpose

- Check and fix DOCX formatting issues for English graduation theses.
- Focus on **format compliance only**.
- Do **not** evaluate content quality, argument quality, grammar quality, or academic merit.

## Rule Boundary (A/B/C)

- A. **Machine-checkable structural/style rules**: targeted scope for this project.
- B. **Partially machine-checkable rules**: may require manual confirmation or reviewer override in future tasks.
- C. **Content-quality and academic judgment rules**: out of scope.

## Not Supported (Current)

- DOCX formatting deep repair logic (still guarded by V1 scope).
- Cover-page reconstruction.
- Page numbering / section / footnote reflow.
- GUI.
- Any TASK-006/TASK-007 scope.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## CLI Examples

```bash
# Single-file check (optional report output)
thesis-format-fixer check samples/input/demo.docx \
  --report-json samples/output/demo.check.report.json \
  --report-md samples/output/demo.check.report.md

# Single-file fix mode (V1 keeps safe passthrough copy + report)
thesis-format-fixer fix samples/input/demo.docx \
  --out samples/output/demo.fixed.docx

# Batch fix mode (recursive by default)
thesis-format-fixer batch-fix samples/input \
  --out-dir samples/output/batch
```

Output convention:

- Single `fix`:
  - fixed docx: `*.fixed.docx`
  - report json: `*.report.json` (default: same path stem as output docx)
  - report md: `*.report.md` (default: same path stem as output docx)
- Batch `batch-fix`:
  - each input docx gets independent `*.fixed.docx` + `*.report.json` + `*.report.md`
  - keeps relative directory structure from input dir
  - batch summary:
    - `batch_summary.json`
    - `batch_summary.md`

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
