# TASK-THESIS-OSS-005 Word Review Adapter Feasibility Freeze (V1)

## 1. 005 Series Completion Status
- 005A completed:
  - External raw audit: `docs/external_audits/TASK-THESIS-OSS-005A_Word_Comment_OSS_Raw_Report.md`
  - Architecture audit: `docs/architecture/TASK-THESIS-OSS-005A_Word_Review_Adapter_Audit.md`
- 005B completed:
  - Comment-only adapter skeleton landed in `src/thesis_format_fixer/review/adapter.py`
  - Covered by unit tests in `tests/test_word_review_adapter_005b.py`
- 005C completed:
  - Real DOCX save/reopen integration coverage in `tests/test_word_review_adapter_005c_docx_integration.py`

## 2. V1 Decisions (Frozen)
- Comments first.
- AI review outputs structured findings only.
- Word write-back is comments only.
- No body prose rewrite.
- Track Changes deferred and experimental only (not release baseline).

## 3. Review Data Contract (V1)
### 3.1 `ReviewFinding` fields (Word adapter contract)
- `rule_id: str`
- `message: str`
- `paragraph_index: int`
- `run_index: int | None = None`
- `anchor_text: str | None = None`

### 3.2 `ReviewApplyResult` fields
- `total: int`
- `added: int`
- `skipped: int`
- `duplicate: int`
- `unsupported: int`
- `details: tuple[dict[str, Any], ...]`

### 3.3 Comment text signature
- Frozen format: `[TFF-RULE:{rule_id}] {message}`
- Neutral author metadata:
  - `author = "ThesisFormatFixer"`
  - `initials = "TFF"`

## 4. Runtime Boundary (Frozen)
- Current `WordReviewAdapter` is standalone.
- It is not wired into `runner`/`cli` write-back flow.
- Existing `review_mode` in `runner`/`cli` produces report findings, not Word comments.
- Future wiring into runtime must be explicit opt-in, not implicit behavior change.

## 5. Safety Invariants (Frozen)
- Preserve body text.
- No silent rewrite.
- Missing anchor must be skipped and reported.
- Duplicate protection required.
- Comments must be removable by Word UI without document text mutation.
- No personal metadata leak via comment author fields.

## 6. Track Changes Feasibility Verdict
- Not part of V1 release boundary.
- Only future optional experiment.
- Must pass Word UI accept/reject behavior tests before any release claim.

## 7. Next Implementation Tasks (Post-Freeze)
- Optional review artifact output interface (structured findings export/write-back plan).
- Optional CLI review command (explicit command surface, opt-in).
- Anchor-aware idempotency improvements (location + signature aware).
- Comment insertion coverage for tables/header/footer/footnotes.
- Structured finding codes taxonomy and parsing rules.

## 8. Explicit Handoff to TASK-THESIS-OSS-006
- Review Profiles can now define what findings to produce.
- Review Profiles must not assume direct body edits.
- Review Profiles must output structured findings suitable for comment write-back.

## 9. Out-of-Scope Guardrail (for this freeze)
- No runner/cli/check/fix integration in this task.
- No AI model invocation in this task.
- No Track Changes implementation.
- No `docx-revisions` dependency.
- No run splitting implementation.
- No complex table/footnote anchor engine changes.
- No adapter behavior rewrite.
