# TASK-THESIS-OSS-006 Review Profiles (Minimal Strategy Layer)

## 1. Goal
Establish a minimal Review Profile layer for strategy differences (English / Humanities / Science-Engineering) that outputs structured finding policies only.

## 2. Layer Boundary
- Format Profile (`rules/profiles/*.yaml`, `profiles/engine.py`): format rules, check/fix boundaries.
- Review Profile (`rules/review_profiles/*.yaml`, `review/profiles.py`): review strategy, finding taxonomy, write-back safety contract.
- The two profile systems are intentionally separated and not merged in one schema.

## 3. Structured Finding Contract (Policy Side)
Each review rule policy defines required finding metadata:
- `rule_id`
- `category`
- `severity`
- `message_template`
- `anchor_strategy`
- `comment_allowed` (must be explicit `true`)
- `auto_rewrite_allowed` (must be explicit `false`)

Notes:
- Runtime AI review is out of scope in this task.
- Policy layer only defines what a valid finding should look like.

## 4. Write-back Safety Invariants
- Review profile must never allow direct body rewrite.
- `auto_rewrite_allowed=true` is rejected by validation.
- Findings are designed for Word comment write-back only (via `WordReviewAdapter` in later integration tasks).
- If anchor cannot be resolved, downstream adapter must report skipped and not force misplaced comments.

## 5. Minimal Implementation Scope in 006
- `src/thesis_format_fixer/review/profiles.py`
  - `ReviewProfile`
  - `ReviewRule`
  - `load_review_profile(path)`
  - `validate_review_profile(profile)`
- Example profiles:
  - `rules/review_profiles/english_academic.yaml`
  - `rules/review_profiles/humanities_thesis.yaml`
  - `rules/review_profiles/science_engineering_thesis.yaml`
- Tests: `tests/test_review_profiles_006.py`

## 6. Explicit Non-Goals (This Task)
- No runner/cli wiring.
- No AI model invocation.
- No direct `.docx` write-back in this task.
- No Track Changes.
- No body auto-rewrite.

## 7. 006A Contract Mapping Addendum
- Added a minimal typed mapping layer (`review/contracts.py`) between `ReviewRule` and `WordReviewAdapter.ReviewFinding`.
- Mapping enforces safety invariants:
  - `auto_rewrite_allowed` must stay `false`
  - `comment_allowed` must stay `true`
  - `body_text_mutation_allowed` must stay `false`
- Missing anchor position (`paragraph_index`) is emitted as skipped-ready mapping result and is never fabricated.
