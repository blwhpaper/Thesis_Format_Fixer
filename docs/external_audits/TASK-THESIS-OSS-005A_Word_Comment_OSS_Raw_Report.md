A safe, Word‑first “review adapter” in Python is feasible today if you treat Word comments as the primary feedback channel and keep Track Changes strictly optional and constrained. Using modern `python-docx` (with its built‑in comments API) plus, optionally, `docx-revisions` for redlines gives you a good balance of power and safety, while avoiding raw OOXML surgery except in a thin, well‑tested layer.[1][2][3][4]

Below is an OSS‑focused audit structured around your questions and the requested A–D groupings.

***

## A. Directly usable libraries

### 1. `python-docx` (upstream, >= 1.2)

- **Capabilities.** Current `python-docx` explicitly supports creating and managing Word comments via `Document.add_comment(runs=..., text=..., author=..., initials=...)`, anchoring comments to one or more `Run` objects, including ranges spanning multiple paragraphs. Comments are stored in a dedicated `comments.xml` part and exposed through `document.comments` with random access by comment ID.[3][4]
- **Limitations.** It still does **not** support programmatic Track Changes (no OOXML `<w:ins>/<w:del>` API), and GitHub issues confirm revisions are not exposed as first‑class objects.[5][6]
- **License/status.** `python-docx` is MIT‑licensed and actively maintained, with recent releases and modern Python support.[7][8]

For a Word‑first thesis tool that already uses `python-docx`, this is the most natural foundation for a comment‑only review adapter.

***

### 2. `docx-comments`

- **What it does.** `docx-comments` is a Python module specifically for **complete comment manipulation**, built on OOXML: add anchored comments, reply (threaded), mark resolved/unresolved, delete or move anchors, and maintain compatibility with Word Online. It explicitly addresses gaps where `python-docx` alone fails to create fully wired comments, noting that vanilla `python-docx` historically created `comments.xml` entries without proper anchors in `document.xml` or modern extras like `commentsExtended.xml` and durable IDs.[9][10]
- **Usage model.** Typical usage wraps a `python-docx` `Document` and uses a `CommentManager` to add comments to a specific paragraph and run range, with typed `PersonInfo` for author metadata.[10][9]
- **Risks.** This library manipulates low‑level OOXML parts; on the plus side it is designed for Word/Word Online compatibility, but you inherit that complexity. You need to review its license and maintenance activity in the GitHub repo (not shown in the snippet) before adopting in core infrastructure.[9][10]

`docx-comments` is attractive if you need threaded comments, resolved status, or perfect Word Online parity, beyond what `python-docx` core offers.

***

### 3. `bayoo-docx` (python-docx fork with comments)

- **What it adds.** `bayoo-docx` is an MIT‑licensed fork of `python-docx` whose explicit goal is to add implementation for **comments and footnotes**, including a `Paragraph.add_comment()` method and the ability to comment both entire paragraphs and individual runs.[11][12][13][14]
- **Status.** The last PyPI release is from 2019, so it lags behind upstream in terms of general bug fixes and features.[12][11]
- **Fit.** Because it diverges from upstream, adopting it for a new project that already depends on `python-docx` is risky: you’d fork your dependency tree and miss current upstream improvements.[8][11]

Today, `upstream python-docx` has gained its own comments API, so `bayoo-docx` is mostly relevant as a reference implementation rather than a dependency to adopt.[4][3]

***

### 4. `docx-revisions` (Track Changes for `python-docx`)

- **Purpose.** `docx-revisions` extends `python-docx` to read and write revision markup in `.docx` files, handling OOXML `<w:ins>` and `<w:del>` elements and exposing APIs like `get_revisions()`, `insert_with_tracking()`, `delete_with_tracking()`, and `replace_with_tracking()`.[2][1]
- **Capabilities.** It can enumerate tracked changes per paragraph, including author metadata and accepted/original text, and create new tracked insertions and deletions that show up as Track Changes in Word.[2]
- **Risks.** Programmatic redlines are inherently fragile: if you generate inconsistent revision structures, manual “Reject” in Word can delete text instead of restoring the original, as seen in a similar context with Aspose’s `Compare()` API where Word’s manual rejection mis‑behaved even though programmatic `Revisions.RejectAll()` was fine.[15]

For your use case, `docx-revisions` should be treated as an **opt‑in, advanced mode**, not your baseline review mechanism.

***

### 5. `docx2python` and `docxreviews2txt` (read‑side helpers)

- **`docx2python`.** This extraction library can now pull comments out of `.docx` files via a `comments` attribute on its `DocxContent`, returning tuples like `(reference_text, author, date, comment_text)`. It’s useful for verifying what your adapter wrote, or for building side‑channel QA reports.[16][17]
- **`docxreviews2txt`.** This CLI tool extracts **review changes** from `.docx` as plain text, explicitly using `<ins>` and `<del>` HTML tags corresponding to tracked changes, which it generates from the document’s OOXML revision markup. This is read‑only but helpful if you later add tracking and want a text diff export.[18]

Both are good to have in your test harness; neither is your primary write‑side API.

***

### 6. Commercial APIs accessible from Python (for reference)

If you ever decide to pay for a high‑assurance engine:

- **Aspose.Words for Python.** Provides rich APIs for comments and revisions, including enabling `doc.track_revisions` to turn on tracking and then iterating `doc.revisions` to review or accept changes.[19][20]
- **Spire.Doc for Python.** Offers `Document.TrackChanges` for enabling tracking, plus methods to accept or reject changes.[21]
- **Syncfusion DocIO (.NET).** Exposes `HasChanges` and `Revisions.AcceptAll()`/`RejectAll()` for managing tracked changes, but is a .NET library typically used via C# rather than native Python.[22]

These are powerful but proprietary; integrating them into a pure‑Python OSS project would complicate your licensing story.

***

## B. Possible but risky low‑level OOXML approaches

### 1. Direct ZIP + XML manipulation

A common suggestion is to treat `.docx` as a ZIP, open `word/document.xml`, and insert the relevant OOXML manually while copying everything else unchanged. This can be done from Python using `zipfile` and an XML library; older answers mention `openxmllib` for convenience.[23][24][25]

While technically straightforward, this puts you in charge of:

- Keeping relationships in `_rels/document.xml.rels` consistent (e.g., linking to `comments.xml`).[24][25]
- Maintaining multiple parts (`document.xml`, `comments.xml`, potentially `commentsExtended.xml`, `people.xml`) and durable IDs consistent for features like threaded comments and Word Online.[10][9]

For a thesis formatter, this is more responsibility than you want in application code; it belongs, if at all, in a dedicated small library with strong tests.

***

### 2. Manual comments via OOXML (`commentRangeStart` / `commentRangeEnd`)

Several resources show how to create comments by adding:

- A `<w:comment>` (with `w:id`, `w:author`, `w:date`, `w:initials`) in `comments.xml`.[26][27]
- A matching `<w:commentRangeStart w:id="N"/>` and `<w:commentRangeEnd w:id="N"/>` around the target text, plus a `<w:commentReference w:id="N"/>` run in `document.xml`.[28][29][30]

The official OOXML description for `commentRangeStart` makes clear that:

- The `@id` must match both the `commentRangeEnd` and the `commentReference`, or the comment may be ignored.[29]
- If any of these are missing or mismatched, Word may silently drop the comment or require a repair.[29]

The “Adding valid comments” code you’ve likely seen (re‑posted on multiple sites) shows this pattern using `docx.opc` and `OxmlElement` to construct the comments part and range markers. This is a workable pattern **inside a library**, but it’s easy to mis‑anchor comments in the presence of complex runs, fields, and tables.[27][26]

***

### 3. Manual Track Changes (`<w:ins>` / `<w:del>`)

Track changes are encoded as `<w:ins>` and `<w:del>` wrappers around runs in `document.xml`. You can, in principle, insert these by hand:[25][2]

- Turn on tracking by adding `<w:trackRevisions/>` to `settings.xml` (documented in various answers).[31][32]
- Wrap inserted text in `<w:ins>` with author/date metadata, wrap deletions in `<w:del>`, and update numbering as needed.[25][2]

But incorrect revision structures can lead to exactly the kind of corruption users fear. Aspose users, for instance, reported that a generated compare document produced revisions where **manual** rejection in Word deleted text instead of restoring the original, even though programmatic `Revisions.RejectAll()` behaved correctly—evidence that getting revision markup 100% Word‑compatible is non‑trivial.[15]

Given your safety requirements, this level of manual work should be avoided in your app layer.

***

## C. Not recommended / unsupported approaches

### 1. Server‑side Word automation (`pywin32`, COM)

You can use COM automation to open `.doc`/`.docx` files, toggle `TrackRevisions`, and call `Revisions.RejectAll()` etc., as shown in various `win32com` examples. These approaches:[33][34]

- Require Word installed and supported on the host,  
- Are Windows‑only, and  
- Are explicitly not supported by Microsoft for unattended/server scenarios.[24][33]

They violate your cross‑platform, OSS, local‑Git‑workflow goals and are unsuitable for a thesis review CLI or service.

***

### 2. Word JavaScript add‑ins / Office.js change tracking

Modern Word JavaScript APIs allow setting `document.changeTrackingMode = Word.ChangeTrackingMode.trackAll` to programmatically track user changes in an add‑in. This is great for interactive add‑ins but:[35]

- Ties your pipeline to Office/Office Online runtime,  
- Doesn’t help a Python‐based batch tool working on `.docx` files offline, and  
- Complicates deployment and QA significantly.  

For your Word‑first, batch‑oriented thesis tool, Office.js is the wrong layer.

***

### 3. Rolling your own revision engine from scratch

Given how easy it is for even mature libraries to generate problematic revision structures (Aspose’s `Compare()` case where rejecting certain changes deleted text instead of restoring it), building your own full redline engine directly on OOXML is **high‑risk**:[15]

- You must correctly handle nested revisions, field codes, tables, and list numbering.  
- You must pass the “Accept All / Reject All in Word UI” test for a wide variety of documents.  

Unless you’re prepared to invest heavily in conformance testing, defer this and rely on specialized libraries (such as `docx-revisions`) if you really need Track Changes.

***

### 4. Depending on ageing forks (`bayoo-docx`) as your core

`bayoo-docx` is MIT‑licensed and implements comments and footnotes, but its last release is from 2019. With upstream `python-docx` now offering its own comments API, basing a new project on that fork would strand you on old code and increase your maintenance burden. It is better used as a reference for OOXML patterns than as a primary dependency.[14][3][4][11][12]

***

## D. Recommended minimal adapter strategy

### 1. Architectural stance: comments first, redlines optional

- **Baseline**: Use **comments only** to express academic and formatting feedback, and continue to apply safe auto‑fixes directly to styles/formatting as your engine already does.  
- **Optional advanced mode**: If needed, add **Track Changes** later via `docx-revisions`, limited to a small subset of transformations (e.g., inserting or deleting short phrases) and marked clearly as experimental.[1][2]

This mirrors how many academic tools operate: comments are the primary review channel; tracked edits are reserved for cases where the tool proposes concrete text changes, and they are always easily reversible.[32][36]

***

### 2. Use `python-docx` comments API as your primary adapter

**Core idea**: Implement a `WordReviewAdapter` that wraps a `python-docx` `Document` and exposes high‑level methods like `add_comment(anchor, rule_id, message)` built on `Document.add_comment`.[3][4]

Key details, grounded in the official comments docs:

- **Anchoring by runs.** `Document.add_comment(runs=...)` anchors a comment to a set of runs; the library will insert the required `<w:commentRangeStart>`, `<w:commentRangeEnd>`, and `<w:commentReference>` markers with matching IDs in `document.xml` and a `<w:comment>` in `comments.xml`.[4][29]
- **Valid ranges.** Comments must start and end at even run boundaries, and ranges can span multiple paragraphs but must be contiguous in document order, as per the comment‑anatomy and range requirements. Your adapter should work in terms of runs rather than raw character indices.[4][29]
- **Metadata.** You can set `author` and `initials` to something like `ThesisFormatFixer` / `TFF` to avoid leaking personal information; the docs show these fields are just strings you control.[4]
- **Introspection.** `document.comments` gives you a collection you can scan for your own comments (e.g., by a `[RULE:...]` prefix) so you can make the adapter **idempotent** (don’t duplicate comments on repeated runs).[4]

This keeps all OOXML detail inside `python-docx` and your adapter logic, rather than scattered across the rule engine.

***

### 3. Mapping rule violations to comment anchors

In your thesis formatter, every rule violation already has some notion of location (paragraph index, run index, maybe character offset). The adapter should:

1. Convert that into a minimal list of `Run` objects forming the anchor range (possibly a single run).[4]
2. If a violation spans part of a run, split that run at the boundaries using `run.text` and `run._r` operations if necessary, since Word comment ranges must align to run boundaries.[29][4]
3. Call `document.add_comment(runs=runs_slice, text=rendered_message, author=..., initials=...)`.[3][4]

The automated OOXML code in python‑docx takes care of creating or updating `comments.xml` and wiring up the range markers, which is much safer than manual element insertion.[29][4]

***

### 4. Comment content and separation from text edits

To keep comments clearly separated from any direct edits:

- **Message structure.** Encode rule metadata in the comment text, e.g.:

  > `[TFF-RULE: P2.3_LINE_SPACING] Expected 1.5 lines but found 1.0. See Student Handbook §2.3.`  

  This keeps your profile/rule IDs visible without touching the original prose.  
- **No automatic wording changes.** For academic style or grammar suggestions (e.g., “use past tense”), provide **comment‑only** recommendations; don’t inject rephrased text into the document body unless the user explicitly opts in. This matches how legal and academic writing guides recommend using Word comments versus Track Changes to avoid silently rewriting author intent.[36]
- **Auto‑format still okay.** For purely formatting fixes (styles, spacing, headings), you can continue to auto‑fix the document, and optionally add a **summary comment** at the beginning describing what was auto‑applied, leaving the original wording untouched.[4]

This strongly enforces your “no direct rewriting of user prose” constraint.

***

### 5. Optional Track Changes via `docx-revisions` (advanced mode)

If you want an optional “redline version” that shows what your formatter changed:

- Use `docx-revisions`’s `RevisionDocument` to **compare a pre‑ and post‑fix document** and generate tracked insertions/deletions, or to apply tracked insert/delete operations as you transform paragraphs.[2]
- Limit the scope to **structural/formatting changes that Word represents as text edits**, and test thoroughly that “Accept All” and “Reject All” in Word behave correctly for your generated documents, given the fragility seen in other revision engines.[25][15]
- Clearly expose this as an advanced, experimental feature, with an option to instead export a **side‑by‑side diff report** in Markdown or PDF instead of editing the `.docx`.  

For your initial release, it’s reasonable to **defer** Track Changes entirely and revisit after the comment‑only adapter is solid.

***

### 6. Safety, compatibility, and privacy risks

With the above design, your main risk areas and mitigations are:

- **Document corruption.** By delegating comment wiring to `python-docx` instead of manual OOXML, you greatly reduce the chance of mismatched `commentRangeStart` / `commentRangeEnd` / `commentReference` IDs that could cause Word repair prompts.[29][4]
- **Word/Word Online compatibility.** Testing should include Word for Windows/Mac and Word Online; libraries like `docx-comments` explicitly target Word Online compatibility by adding `commentsExtended.xml` and people metadata, which you can study if you later need modern threaded comments.[9][10]
- **Comment anchoring & multi‑run spans.** Anchoring via runs, splitting runs when necessary, and respecting contiguous range constraints keeps anchors stable even across reflows.[29][4]
- **Multilingual text & formatting preservation.** Since comments are separate bodies with their own runs, you don’t alter the original runs’ fonts or language; Word’s OOXML model already handles Unicode, and the comment content can carry its own formatting.[4]
- **Privacy.** Always use a neutral `author` and avoid encoding user names/emails in comments; tools like `docx2python` and Aspose’s comment APIs show how easy it is to extract comment authors programmatically, which is a reminder to keep this metadata sanitized for documents that might be shared.[20][16]
- **Recoverability.** Because your adapter never deletes or rewrites original text for review purposes—only adds comments—users can always recover the original by simply removing comments, even if something goes wrong with a suggestion.[36][4]

These align well with your risk list: corruption, compatibility, anchoring, multi‑run spans, multilingual text, formatting, privacy, and recoverability.

***

## Comparison table: key libraries and approaches

| Library / approach        | License / cost            | Maintenance signal (recent activity)                | Comment support                                  | Track Changes support                            | Implementation risk for you                    |
|---------------------------|---------------------------|-----------------------------------------------------|--------------------------------------------------|--------------------------------------------------|-----------------------------------------------|
| `python-docx`             | MIT, free[8][7] | Active; recent releases on PyPI[8]            | Native `add_comment`, `document.comments`[4][3] | None (no OOXML revisions API)[5][6] | **Low** – best baseline dependency            |
| `docx-comments`           | OSS (license to verify)   | New (2026 PyPI releases)[9][10]           | Full OOXML comment manipulation, threads, resolve, move anchors; Word Online compatible[9][10] | None                                            | **Medium** – powerful, but deeper OOXML layer |
| `bayoo-docx`              | MIT[12][13]       | Last release 2019[11][12]                  | Paragraph/run `add_comment`[11]             | None                                            | **Medium–High** – aging fork of python-docx   |
| `docx-revisions`          | OSS (likely MIT; check)   | New (2026 PyPI & GitHub)[1][2]           | Read comments via python-docx only               | Read/write `<w:ins>`, `<w:del>`; accept/inspect revisions[2] | **High** – Track Changes is fragile           |
| `docx2python`             | OSS (GitHub)              | Active; recent releases, added comments in 2.10[16][17] | Reads comments (reference_text, author, date, text)[16] | Reads revisions only via raw XML, if at all    | **Low** for read‑only QA                      |
| `docxreviews2txt`         | OSS, CLI[18]          | Recent (2024 PyPI)[18]                         | Reads comments via underlying OOXML             | Extracts tracked changes as `<ins>/<del>` text[18] | **Low** for read‑only review exports          |
| Aspose.Words for Python   | Commercial[19]        | Actively maintained enterprise library[19][15] | Full comment API, extraction and insertion[19][20] | Full track‑changes model with revisions collection[19][15] | **Low** technically, **High** licensing       |
| Spire.Doc for Python      | Commercial[21]        | Actively marketed[21]                          | Comment APIs (via .NET bridge)                  | `Document.TrackChanges` and accept/reject[21] | **Medium** – proprietary, Windows‑weighted    |
| Syncfusion DocIO (.NET)   | Commercial[22]        | Enterprise tier                                     | Comment APIs                                     | Track changes with `HasChanges`, `AcceptAll`[22] | **High** integration complexity from Python   |
| Python‑Redlines (wrapper) | MIT, wrapper over C#[37] | Recent (2024 announcement)[37]                  | Depends on underlying tech                       | Generates redline docs via a C# tool[37]    | **High** – cross‑runtime, narrow focus        |

(Where license details weren’t in snippets above, you’d confirm in each project’s repo before shipping.)

***

## How other tools separate comments from edits

- Word’s own guidance distinguishes **Track Changes** (inline modifications as red/blue insertions/deletions) from **comments** (balloons in the margin), and legal writing guides recommend using comments when you want to give feedback **without changing the document text itself**.[32][36]
- Libraries like Aspose and Spire expose comments and revisions as distinct APIs, letting you add comments while leaving text unchanged, or turn on `track_revisions` / `TrackChanges` to log actual edits, which mirrors this separation programmatically.[19][21]
- Tools such as `docxreviews2txt` and `docx2python` likewise treat comments and tracked changes as separate “channels” to extract: comments are annotations; `<ins>/<del>` markup is the history of content edits.[17][16][18]

Your thesis tool should follow this pattern and treat comments as the safe, primary channel for reviewer feedback.

***

## Concise recommendation for your thesis review tool

For a Python‑based, Word‑first thesis formatter, I recommend:

1. **Base your Word Review Adapter on modern `python-docx`’s comments API**, wrapping `Document.add_comment` in your own adapter interface and anchoring by runs, not by raw XML.[3][4]
2. **Keep all academic review feedback in comments only** for the initial implementation; no programmatic Track Changes or rewriting of user prose, beyond the controlled formatting fixes you already perform.[36][4]
3. **Add `docx-revisions` only as an optional, advanced module** if you later want a redline mode, and back it with aggressive “Accept/Reject in Word UI” testing to guard against revision corruption.[2][15]
4. Use tools like `docx2python` and `docxreviews2txt` in your QA harness to verify that comments and any revisions you create are structurally sound and semantically correct.[16][17][18]

This gives you a minimal, safe, and OSS‑friendly review adapter that respects your design constraints while remaining extensible for more sophisticated review workflows later.

Sources
[1] docx-revisions - PyPI https://pypi.org/project/docx-revisions/0.1.1/
[2] Python Tracked Changes Library - docx-revisions https://github.com/balalofernandez/docx-revisions
[3] Source code for docx.document https://python-docx.readthedocs.io/en/latest/_modules/docx/document.html
[4] Working with Comments — python-docx 1.2.0 documentation https://python-docx.readthedocs.io/en/latest/user/comments.html
[5] revisions/track changes · Issue #340 · python-openxml/python-docx https://github.com/python-openxml/python-docx/issues/340
[6] Is there a way to read the revisions? · Issue #930 · python-openxml/python-docx https://github.com/python-openxml/python-docx/issues/930
[7] python-docx - Oracle Help Center https://docs.oracle.com/en/database/oracle/agent-factory/25.3/pafli/Steve_Canny_python-docx.html
[8] python-docx https://pypi.org/project/python-docx/
[9] docx-comments https://pypi.org/project/docx-comments/
[10] docx-comments 0.1.0 on PyPI https://libraries.io/pypi/docx-comments
[11] bayoo-docx - PyPI https://pypi.org/project/bayoo-docx/
[12] bayoo-docx - PyPI https://pypi.org/project/bayoo-docx/0.1.3/
[13] dexterhahaha/bayoo-docx: Create and modify Word ... - GitHub https://github.com/JunyiXie/bayoo-docx
[14] BayooG/bayoo-docx: Create and modify Word documents with Python https://github.com/BayooG/bayoo-docx
[15] Compare() generates Track Changes where Reject deletes text ... https://forum.aspose.com/t/compare-generates-track-changes-where-reject-deletes-text-instead-of-restoring-original/326280
[16] Docx2Python 2.10.0 will now extract comments from Word files https://www.reddit.com/r/Python/comments/1buwnrt/docx2python_2100_will_now_extract_comments_from/
[17] ShayHill/docx2python: Extract docx headers, footers, (formatted) text ... https://github.com/ShayHill/docx2python
[18] docxreviews2txt - PyPI https://pypi.org/project/docxreviews2txt/
[19] Handling Comments And... https://tutorials.aspose.com/words/python-net/document-structure-and-content-manipulation/document-revisions/
[20] Extract Comment and Reference Text with Python - Aspose Forum https://forum.aspose.com/t/extract-comment-and-reference-text-with-python/249689
[21] Enable Track Changes in Word in Python - e-iceblue https://www.e-iceblue.com/Tutorials/Python/Spire.Doc-for-Python/Program-Guide/Document-Operation/Python-Enable-Track-Changes-Accept-or-Reject-Tracked-Changes-in-Word.html
[22] FAQ about Track Changes | DocIO - Help.Syncfusion.com https://help.syncfusion.com/document-processing/word/word-library/net/faqs/track-changes-faqs
[23] Python – How to programmatically insert comments into a Microsoft Word document https://itecnote.com/tecnote/python-how-to-programmatically-insert-comments-into-a-microsoft-word-document/
[24] How to programmatically insert comments into a Microsoft Word document? https://stackoverflow.com/questions/568972/how-to-programmatically-insert-comments-into-a-microsoft-word-document
[25] How to examine a WOrd document for changes and comments? https://learn.microsoft.com/en-us/answers/questions/2123305/how-to-examine-a-word-document-for-changes-and-com
[26] Adding valid comments to docx documents using python https://stackoverflow.com/questions/79215799/adding-valid-comments-to-docx-documents-using-python
[27] [Python] Adding valid comments to docx documents using python https://www.4each.com.br/threads/python-adding-valid-comments-to-docx-documents-using-python.71101/
[28] How to: Insert a comment into a word processing document https://learn.microsoft.com/en-us/office/open-xml/word/how-to-insert-a-comment-into-a-word-processing-document?tabs=cs-0%2Ccs-1%2Ccs-2%2Ccs-3%2Ccs-4%2Ccs-5%2Ccs
[29] commentRangeStart (Comment Anchor Range Start) https://c-rex.net/samples/ooxml/e1/part4/OOXML_P4_DOCX_commentRangeStart_topic_ID0EFJMV.html
[30] how to get the comments and Corresponding content from a docx file ? · Issue #483 · python-openxml/python-docx https://github.com/python-openxml/python-docx/issues/483
[31] How to activate "Track changes"-Mode in a word document generated with python https://stackoverflow.com/questions/67061294/how-to-activate-track-changes-mode-in-a-word-document-generated-with-python
[32] Track changes in Word - Microsoft Support https://support.microsoft.com/en-us/office/track-changes-in-word-197ba630-0f5f-4a8e-9a77-3712475e806a
[33] Is there a way to programmatically reject changes to a word document using python, while not deleting comments from it? https://stackoverflow.com/questions/56667893/is-there-a-way-to-programmatically-reject-changes-to-a-word-document-using-pytho
[34] Can Python work with old word files .doc not .docx - Reddit https://www.reddit.com/r/learnpython/comments/1fq3cpb/can_python_work_with_old_word_files_doc_not_docx/
[35] Is there a way to programmatically track changes in a word doc? https://stackoverflow.com/questions/56570532/is-there-a-way-to-programmatically-track-changes-in-a-word-doc
[36] Legal Writing: Tools and Tips for formatting: Track Changes https://libguides.law.illinois.edu/c.php?g=1272613&p=9336248
[37] Python Tool for Docx Tracked Change Comparisons - Reddit https://www.reddit.com/r/Python/comments/198wuja/python_tool_for_docx_tracked_change_comparisons/
[38] How to Accept ("Preserve") DOCX Commented Changes In ... https://github.com/python-openxml/python-docx/issues/566
[39] Insert OOXML comment with track changes https://stackoverflow.com/questions/40261291/insert-ooxml-comment-with-track-changes
[40] How to Add Comments to DOCX Files Using XML Manipulation https://instagit.com/anthropics/skills/add-docx-comments-xml-manipulation/
[41] Python: Python-based Methods for Extracting Comments from Word Documents https://copyprogramming.com/howto/how-to-extract-comments-from-word-python
[42] insert comment · Issue #93 · python-openxml/python-docx https://github.com/python-openxml/python-docx/issues/93
[43] Working with Comments - python-docx-oss's documentation! https://python-docx-oss.readthedocs.io/en/latest/user/comments.html
[44] Track Changes in Word Docs - Datalab Documentation https://documentation.datalab.to/docs/recipes/extract-redlines-and-comments/track-changes-from-word-documents
[45] Inserting a comment in docx file using python 3 - Stack Overflow https://stackoverflow.com/questions/53892070/inserting-a-comment-in-docx-file-using-python-3
[46] Comments missing from MS Word import. Modern comments the ... https://forum.literatureandlatte.com/t/comments-missing-from-ms-word-import-modern-comments-the-problem/130612
[47] python-docx not working 'ModuleNotFound' : Forums https://www.pythonanywhere.com/forums/topic/14766/
[48] 'Document' object has no attribute 'comments' · Issue #1215 - GitHub https://github.com/python-openxml/python-docx/issues/1215
[49] Insert comment in MS Word file using python - YouTube https://www.youtube.com/watch?v=OB-jAk4S6Ng
[50] python-docx-template/LICENSE.txt at master · elapouya/python-docx-template https://github.com/elapouya/python-docx-template/blob/master/LICENSE.txt
[51] python-docx/LICENSE at master · openlawlibrary/python-docx https://github.com/openlawlibrary/python-docx/blob/master/LICENSE
[52] license - BayooG/bayoo-docx - GitHub https://github.com/BayooG/bayoo-docx/blob/master/LICENSE
[53] elapouya/python-docx-template https://github.com/elapouya/python-docx-template
