# Decisions Log

## DEC-001: src-layout packaging

- **Decision**: use `src/` layout with setuptools.
- **Reason**: avoids accidental imports from project root and improves release hygiene.

## DEC-002: thin CLI + runner boundary

- **Decision**: keep argument parsing in `cli.py`, execution placeholders in `app/runner.py`.
- **Reason**: stable command contract now, implementation evolves later.

## DEC-003: rulebook tracked in repository

- **Decision**: keep canonical markdown rulebook in `rules/FORMAT_RULEBOOK_v1.md` and source docs in `rules/sources/`.
- **Reason**: reproducible basis for future detector/formatter behavior.
