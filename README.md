# thesis-format-fixer

`thesis-format-fixer` is a Python CLI project for checking and fixing **English graduation thesis DOCX formatting** against a rulebook.

Current stage: **TASK-019 rule-source alignment and rulebook uplift (v3 freeze refresh)**.

Reference-review stage: **TASK-018 bibliography finding granularity uplift**.

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
- Any beyond current TASK-007 minimal review scope.

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

# Single-file check + V2 review (rule-engine only)
thesis-format-fixer check samples/input/demo.docx \
  --review-mode basic \
  --review-target headings,references,pagination

# Single-file fix mode (V1 keeps safe passthrough copy + report)
thesis-format-fixer fix samples/input/demo.docx \
  --out samples/output/demo.fixed.docx

# Batch fix mode (recursive by default)
thesis-format-fixer batch-fix samples/input \
  --out-dir samples/output/batch
```

## GUI (Minimal)

Launch GUI:

```bash
python -m thesis_format_fixer.gui
```

Minimal workflow (single file):

1. Select one `.docx` file.
2. Choose mode: `check` or `fix`.
3. Select output directory.
4. Click `Execute`.
5. Read result summary in GUI.
6. Click `Open Output Dir` to get generated reports/docx.

Batch workflow:

1. Choose mode: `batch-fix`.
2. Select input directory (GUI scans `.docx` recursively).
3. Select output directory.
4. Click `Execute`.
5. Read per-file status (`exit_code`, input, output) and run summary in GUI:
   - `total_files`
   - `succeeded`
   - `failed`
   - `output_dir`
6. Click `Open Output Dir` to inspect generated files and `batch_summary.json`.

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

- `rules/FORMAT_RULEBOOK_v3.md`
- `rules/FORMAT_RULEBOOK_v2.md`
- `rules/sources/10.1论文封皮.pdf`
- `rules/sources/8. 毕业论文正文写作格式要求.docx`
- `rules/sources/太院教字[2021]03号太原学院毕业论文（设计）管理办法（终稿）.pdf`

TASK-019 note:

- The school management regulation PDF is now part of the formal rule-source set.
- `FORMAT_RULEBOOK_v3` now explicitly freezes two additional constraints as **B-class check-only rules**:
  - No Chinese book-title marks `《》` in English contexts.
  - No page ranges for D-type references (`[D]`, `[D/OL]`).

## Bibliography Review Capabilities (TASK-018)

- Fine-grained findings for bibliography type marker legality and carrier legality.
- Type-specific structure checks for `[J]`, `[M]/[R]`, `[D]`, `[EB/OL]` and similar combinations.
- Collection-level checks for:
  - English entries must appear before Chinese entries.
  - English bibliography count must be at least 5.
- Additional frozen checks:
  - English entry must not contain `《》`.
  - `[D]` thesis entry must not contain page range.
- Output findings include stable `finding_code` and context fields (`rule_code`, `block_id`, `reference_index`, `reference_text`, `reason` / `expected_pattern`) for downstream report/review queue consumption.

## Repository Layout

- `src/` source-layout Python package
- `rules/` rulebook and source documents
- `docs/` architecture and planning notes
- `tests/` smoke tests
- `scripts/` local bootstrap/demo scripts
- `samples/` sample IO/report directories
