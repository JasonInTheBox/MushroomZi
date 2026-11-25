# Analects HTML Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Import the 20-book source snapshot into validated per-book JSON while preserving provenance, Muller’s comments and notes, and existing project commentary.

**Architecture:** A Python standard-library parser reads the source HTML into ordered passage events and a footnote map. A report mode proposes source-order alignments without changing corpus files; the approved mapping file records numbering exceptions for the separate write mode.

**Tech Stack:** Python standard library (`html.parser`, `json`, `argparse`, `unittest`), existing JSON Schema validator, current Next.js static site.

**Spec:** [Analects HTML Corpus Import Design](../specs/2026-11-25-analects-html-import-design.md)

## Global Constraints

- The tracked HTML is the source snapshot; the site reads JSON only.
- Keep original text, English translation, sourced scholarly material, and generated project commentary distinct.
- Use no new runtime dependencies.
- Record the existing user-authorized reuse basis with translator/author, source URL, passage, and note/comment citation.
- Mapping report approval was given on 2026-11-25 (UTC); the corpus write is complete.
- Keep the local-first stack, hosting, and model-provider decisions as recorded in A-010; do not add a live service.

## Review Focus

1. Repeated labels remain separate; source-only originals remain in the corpus; a translation with no preceding original blocks a write. See `test_report_keeps_exact_repeated_source_blocks_as_distinct_passages`, `test_report_preserves_source_only_original`, and `test_translation_without_preceding_original_blocks_corpus_write`.
2. Footnote references must resolve to note bodies despite repeated legacy HTML anchors. Test `test_note_text_uses_reference_target_and_excludes_backlink_labels` and `test_build_corpus_attaches_linked_notes_to_referencing_passage`.
3. Continuation paragraphs must remain with the right translation or comment. Test `test_translation_and_comment_continuations_stay_separate`.
4. Re-import must retain project-authored themes and generated commentary. Test `test_merge_preserves_existing_generated_content_and_is_stable`.
5. Sourced scholarship must require attribution and rights metadata; generated commentary remains valid without third-party rights. Test `test_scholarly_interpretation_requires_source_and_rights` and `test_generated_commentary_needs_no_source_rights`.

## File Structure

- `.gitignore` — exclude the project-local `.worktrees/` directory.
- `scripts/import_analects_html.py` — parse source events, build mapping report, merge source data, and expose report/write CLI modes.
- `scripts/test_import_analects_html.py` — focused parser, audit, merge, and CLI tests.
- `scripts/fixtures/analects-import-sample.html` — small HTML fixture covering continuations, comments, footnote links, and notes.
- `content/source-import-overrides.json` — reviewed source marker occurrences mapped to canonical passage numbers, including the `(unmarked)` sentinel.
- `content/schema/passage.schema.json` — require source and rights records for `scholarly_interpretation` entries.
- `docs/superpowers/reviews/2026-11-25-analects-source-mapping-review.md` — generated proposed mappings and anomaly excerpts for the user’s review; it does not contain corpus output.
- `content/books/book-01.json` … `content/books/book-20.json` — final imported corpus, written only after mapping approval.
- `README.md`, `docs/product-specification.md`, and `docs/architecture-decisions.md` — import workflow, provenance, selected stack, and milestone status.

## Tasks

### Task 1: Parse source HTML into ordered events

**Files:**
- Create: `scripts/import_analects_html.py`
- Create: `scripts/test_import_analects_html.py`
- Create: `scripts/fixtures/analects-import-sample.html`

**Interfaces:**
- `parse_source_html(html: str) -> dict` returns `{"books": [{"number": int, "title": {"chinese": str, "pinyin": str}, "events": [{"kind": "original" | "translation" | "comment", "marker": str | None, "text": str, "noteRefs": list[str]}]}], "notes": {anchor_id: text}}`.
- Event order follows the source HTML. Footnote marker labels are recorded in `noteRefs` and excluded from the event text.

- [x] **Step 1: Write parser tests** for the fixture: `test_parse_source_sections_and_markers` asserts book 1 and title `學而` plus `[1-1]` and `[1:1]`; `test_translation_and_comment_continuations_stay_separate` asserts each continuation stays with its entry; `test_note_text_uses_reference_target_and_excludes_backlink_labels` asserts `note-1-1` resolves to the fixture note and its marker number is absent from translation text.
- [x] **Step 2: Run the focused tests and confirm they fail** with missing parser behavior.

  Run: `python -m unittest discover -s scripts -p test_import_analects_html.py -v`

- [x] **Step 3: Implement `parse_source_html`** with `html.parser.HTMLParser`; normalize whitespace and decode entities while preserving source punctuation and Unicode.
- [x] **Step 4: Run the focused tests and confirm they pass.**
- [x] **Step 5: Commit** the parser and fixture tests.

  Run: `git add scripts/import_analects_html.py scripts/test_import_analects_html.py scripts/fixtures/analects-import-sample.html; git commit -m "feat: parse Analects source HTML"`

### Task 2: Audit mappings and prepare the review report

**Files:**
- Modify: `scripts/import_analects_html.py`
- Modify: `scripts/test_import_analects_html.py`
- Create: `docs/superpowers/reviews/2026-11-25-analects-source-mapping-review.md`

**Interfaces:**
- `build_mapping_report(parsed: dict) -> dict` reports book counts, source labels, proposed passage pairings, unresolved items, and excerpts. It never writes under `content/books/`.
- CLI: `python scripts/import_analects_html.py --report docs/superpowers/reviews/2026-11-25-analects-source-mapping-review.md` writes only the review report.

- [x] **Step 1: Add tests**: source-order proposals retain exact duplicates, identify source-only passages, list unmapped translations, and cover the real-source numbering anomalies plus all linked notes.
- [x] **Step 2: Run focused tests and confirm they fail** on the missing audit/report behavior.

  Run: `python -m unittest discover -s scripts -p test_import_analects_html.py -v`

- [x] **Step 3: Implement `build_mapping_report`** with source-order pairings, canonical IDs, printed labels, warnings, duplicates, and source-only entries.
- [x] **Step 4: Generate and inspect the report.** The user approved the source-order proposal and confirmed the repeated Book 14 entry should remain.
- [x] **Step 5: Commit** the audit/report code and proposed mapping report; leave the corpus untouched.

  Run: `git add scripts/import_analects_html.py scripts/test_import_analects_html.py docs/superpowers/reviews/2026-11-25-analects-source-mapping-review.md; git commit -m "feat: report Analects source mappings"`

### Task 3: Add sourced-scholarship rights validation and mapping overrides

**Files:**
- Modify: `content/schema/passage.schema.json`
- Modify: `scripts/test_validate_corpus.py`
- Modify: `scripts/import_analects_html.py`
- Modify: `scripts/test_import_analects_html.py`

**Interfaces:**
- Override file: `{"schemaVersion": 1, "mappings": [{"bookNumber": int, "sourceKind": "original" | "translation", "sourceMarker": str, "occurrence": int, "passageNumber": int}]}`. Entries cover only reviewed exceptions from the report.
- Translation IDs are `analects.{book:02}.{passage:02}.en.muller`; comment IDs are `{passageId}.muller.comment.{ordinal:02}`; note IDs are `{passageId}.muller.note.{sourceNoteOrdinal:02}`.
- Each imported scholarly entry uses `author: "A. Charles Muller"`, `language: "en"`, `kind: "scholarly_interpretation"`, a passage-and-locator citation, and `rights: {"reuseStatus":"licensed","license":"User-authorized reuse with attribution required"}`.
- The existing rights schema is reused. A `scholarly_interpretation` commentary item requires `source` and `rights`; generated project commentary does not.

- [x] **Step 1: Add failing schema tests** `test_scholarly_interpretation_requires_source_and_rights` and `test_generated_commentary_needs_no_source_rights`, proving sourced scholarship without source/rights is rejected and generated commentary without third-party rights remains valid.
- [x] **Step 2: Run the focused validator tests and confirm they fail.**

  Run: `python -m unittest discover -s scripts -p test_validate_corpus.py -v`

- [x] **Step 3: Extend the schema conditionally** for scholarly entries and add tests for valid user-authorized, cited Muller material.
- [x] **Step 4: Add override loading tests** for `test_override_resolves_one_marker_occurrence`, `test_duplicate_override_key_is_rejected`, and `test_out_of_range_passage_number_is_rejected`.
- [x] **Step 5: Implement override validation** so source-order corrections are explicit and translations without an original are rejected.
- [x] **Step 6: Run both focused test modules and commit** schema and audit safeguards.

  Run: `python -m unittest discover -s scripts -p test_import_analects_html.py -v` and `python -m unittest discover -s scripts -p test_validate_corpus.py -v`.

  Commit: `git add content/schema/passage.schema.json scripts/test_validate_corpus.py scripts/import_analects_html.py scripts/test_import_analects_html.py; git commit -m "feat: validate sourced scholarship provenance"`

### Task 4: Build and test safe corpus generation

**Files:**
- Modify: `scripts/import_analects_html.py`
- Modify: `scripts/test_import_analects_html.py`

**Interfaces:**
- `build_corpus(parsed: dict, overrides: dict, existing_books: dict[int, dict]) -> list[dict]` creates schema-shaped book records with original text, Muller translation, scholarly comments/notes, and provenance.
- `write_books(books: list[dict], output_dir: Path) -> None` validates all records before writing the 20 files; tests use a temporary output directory, while CLI `--write` uses `content/books/`.
- CLI: `python scripts/import_analects_html.py --write --overrides content/source-import-overrides.json` writes all 20 books when translation blocks are assigned and overrides validate; an original with no source translation is allowed.

- [x] **Step 1: Add failing tests**: `test_build_corpus_uses_stable_muller_ids_and_citations`, `test_build_corpus_attaches_linked_notes_to_referencing_passage`, and `test_merge_preserves_existing_generated_content_and_is_stable`.
- [x] **Step 2: Run focused tests and confirm they fail.**

  Run: `python -m unittest discover -s scripts -p test_import_analects_html.py -v`

- [x] **Step 3: Implement `build_corpus`**. Store imported comments and notes as separate English `scholarly_interpretation` entries attributed to A. Charles Muller. Preserve any citations inside note text. Keep existing generated entries and themes unchanged.
- [x] **Step 4: Add temporary-directory writer tests** for unresolved mappings, validation, and rollback on a failed replacement.
- [x] **Step 5: Run focused tests and commit** the generation/merge logic.

  Run: `python -m unittest discover -s scripts -p test_import_analects_html.py -v`.

  Commit: `git add scripts/import_analects_html.py scripts/test_import_analects_html.py; git commit -m "feat: build Analects corpus from source"`

### Task 5: Review mappings, write corpus, update docs, and verify (complete)

**Files:**
- Create: `content/source-import-overrides.json`
- Modify: `content/books/book-01.json` … `content/books/book-20.json` after user approval of the report.
- Modify: `web/src/app/(home)/page.tsx` and `web/src/app/[lang]/passage/[id]/page.tsx` to hide unavailable English routes and skip source-only passages in English navigation.
- Modify: `README.md`
- Modify: `docs/product-specification.md`
- Modify: `docs/architecture-decisions.md`
- Modify: `scripts/test_import_analects_html.py` if real-source regressions are found.

- [x] **Step 1: Record the approved exception mappings** in `content/source-import-overrides.json`, then run the write command with that file.
- [x] **Step 2: Verify corpus integrity.**

  Run: `python -m unittest discover scripts`

  Expected: all validator and importer tests pass.

  Run: `python scripts/validate_corpus.py`

  Expected: all 20 book files validate with unique IDs and no placeholders.

- [x] **Step 3: Update docs** with the source import command, attribution/rights policy, 20-book corpus status, and remaining annotation-display milestone.
- [x] **Step 4: Run frontend verification** because each imported passage adds static routes and one source-only passage removes an English route.

  Run from `web/`: `npm run lint`, `npx tsc --noEmit`, `npm test`, and `npm run build`.

  Expected: no lint/type/test errors and static export completes.

- [x] **Step 5: Review the final diff** with `git diff --check` and inspect representative passages; the implementation commit remains the next step.

  Run: `git add content/source-import-overrides.json content/books/book-*.json README.md docs/product-specification.md docs/architecture-decisions.md; git commit -m "feat: import cited Analects corpus"`

## Execution Notes

Use the current `analects-source-extraction` branch inside `.worktrees/analects-source-extraction`, within the user-authorized project folder. Do not merge or push as part of implementation. Stop after the local commit so the user can review and decide whether to push.
