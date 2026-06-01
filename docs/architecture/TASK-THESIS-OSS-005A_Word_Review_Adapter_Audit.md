# TASK-THESIS-OSS-005A: Word Review Adapter Architecture Audit

## 1. Executive Decision
- **Primary Mechanism**: The V1 Review Adapter will use the upstream `python-docx` (>= 1.2.0) native comments API (`Document.add_comment`).
- **Comment-Only First**: All review feedback (rule violations, AI suggestions) will be inserted as Word comments anchored to the relevant text.
- **Track Changes Deferred**: Programmatic Track Changes (redlines) are strictly deferred/optional/experimental due to high risks of document corruption and manual rejection failures.

## 2. Source Evaluation & Categorization

| Source | Category | Rationale |
| :--- | :--- | :--- |
| `python-docx` | **Adopt** | Upstream >= 1.2.0 natively supports `add_comment` with run-level anchoring. Active, MIT licensed, our existing baseline. |
| `docx2python` | **Adopt (QA)** | Read-only extraction of comments. Useful for regression testing our generated comments. |
| `docx-comments` | **Study** | Good reference for threading and Word Online compatibility (`commentsExtended.xml`), but introduces too much low-level OOXML risk for V1. |
| `docx-revisions` | **Study** | Capable of reading/writing `<w:ins>`/`<w:del>`. Good candidate if Track Changes is eventually needed, but too fragile for V1. |
| `docxreviews2txt` | **Study** | Useful test-side helper for reading Track Changes as `<ins>`/`<del>` tags, if adopted later. |
| `bayoo-docx` | **Avoid** | Unmaintained fork of python-docx since 2019. Strands us from upstream bug fixes. |
| Commercial APIs (Aspose, Spire) | **Avoid** | Violates OSS/MIT goals. |
| Raw OOXML Manipulation | **Avoid** | Unnecessary risk of corrupting `_rels`, `comments.xml`, and ID matching. Leave OOXML strictly to `python-docx`. |

## 3. WordReviewAdapter V1 Minimal Boundary
The `WordReviewAdapter` will act as a safe integration layer between the internal `Reviewer` findings and the Word document:
- **Add Comments Only**: Only inserts comments.
- **Neutral Author Metadata**: Uses a fixed identity (e.g., `author="ThesisFormatFixer", initials="TFF"`) to prevent personal metadata leaks.
- **No Body Prose Rewrite**: Will not alter user text for grammatical or stylistic fixes. Suggestions remain in comments.
- **No Track Changes**: V1 will completely exclude any programmatic redlines.
- **No Direct XML**: The adapter will exclusively use the `python-docx` high-level API. No direct `w:commentRangeStart` or `OxmlElement` hacking outside the adapter's isolated boundaries (and ideally none at all).

## 4. Data Flow
1. **Review Finding**: The review pipeline generates a `ReviewFinding` (with rule_id, block_id, target text snippet).
2. **Anchor Resolution**: The adapter looks up the `block_id` and scans paragraphs/runs to locate the target text boundaries.
3. **Run Range**: The adapter maps the text boundaries to a contiguous slice of `Run` objects (splitting runs if the finding starts/ends mid-run).
4. **Comment Insertion**: The adapter calls `document.add_comment(runs=anchor_runs, text=formatted_message, author="TFF")`.
5. **Report**: The adapter reports success or failure (e.g., anchor not found) back to the execution record.

## 5. Safety Invariants
- **Preserve Original Prose**: Never mutate original text for review findings.
- **Comments are Removable**: Users can safely right-click -> "Delete Comment" in Word to restore the original state without residue.
- **Idempotency Required**: Repeated runs on the same document must not duplicate TFF comments. The adapter must check existing comments before insertion.
- **No Personal Metadata Leak**: Hardcoded, neutral author tags.
- **Missing Anchor Fallback**: If the adapter cannot safely locate the exact run range for a finding, it drops the comment insertion and bubbles it up to the JSON/Markdown report, avoiding forced/misplaced comments.

## 6. Test Strategy for 005B
- **Fixture Creation**: Create a minimal `.docx` fixture with known paragraphs and runs.
- **Single Comment**: Test adding a comment to a single run.
- **Multiple Comments**: Test adding multiple comments across different paragraphs.
- **Idempotency**: Test that a repeated fix run does not add identical comments to the same location.
- **Missing Anchor**: Test graceful fallback when the target string does not match the block text.
- **Structural Sanity**: The output document must be openable in MS Word without triggering a "corrupted document / repair" prompt.

## 7. Explicit Non-Goals
- No GUI for reviewing comments (Word is the GUI).
- No Track Changes / `<w:ins>` / `<w:del>`.
- No grammar rewrite / text replacement.
- No commercial dependencies (e.g., Aspose).
- No raw OOXML manipulation unless strictly necessary and perfectly isolated later.

## 8. Open Risks and Future Tasks
- **Run Splitting**: Word comments require run boundaries. We must safely split runs without losing formatting if a finding targets a sub-string within a single run.
- **Multi-run Anchor Spans**: Accurately mapping character indices to an array of runs.
- **Complex Structures**: Comments inside tables, headers, or footnotes might behave differently than in body paragraphs.
- **Word Online Compatibility**: Modern threaded comments might require `commentsExtended.xml` which base `python-docx` might not fully support out-of-the-box.
- **Structured Finding Codes**: Parsing `[TFF-RULE: X]` out of existing comments reliably to enforce idempotency.
