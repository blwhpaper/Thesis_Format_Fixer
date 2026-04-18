# Architecture (TASK-001)

## Goals

- Use `src` layout for packaging stability.
- Keep CLI thin; business flow in `app/runner.py`.
- Reserve clear extension points for future tasks.

## Package Structure

- `thesis_format_fixer.cli`: argument parsing and dispatch.
- `thesis_format_fixer.app.runner`: run modes (`check` / `fix`) placeholders.
- `thesis_format_fixer.io.rulebook`: lightweight rulebook loader for smoke tests.
- `thesis_format_fixer.rules`: future machine-readable rule models.
- `thesis_format_fixer.detectors`: future issue detection logic.
- `thesis_format_fixer.formatters`: future DOCX mutation logic.
- `thesis_format_fixer.reporters`: future output/report rendering.
- `thesis_format_fixer.utils`: shared utility functions.

## Runtime Flow (Current)

1. User calls `thesis-format-fixer`.
2. CLI parses command and validates required flags.
3. Runner validates input/output path shape.
4. Program prints `待实现` and exits.
