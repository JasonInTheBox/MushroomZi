# Analects HTML Corpus Import Design

**Status:** Implemented after the user approved source-order mapping on 2026-11-25 (UTC). All 20 books are imported, including Muller’s inline comments and footnotes. One source original has no translation in the snapshot and remains source-only.

## Intent

Turn the tracked `Analects of Confucius 論語.html` snapshot into the project’s version-controlled, per-book JSON corpus. Preserve the Classical Chinese text, A. Charles Muller’s English translation, his inline comments, and linked footnotes as distinct, attributed source material. Keep generated Mushroom Zi commentary separate.

## Goals

- Extract all 20 books to `content/books/book-01.json` through `book-20.json` using a repeatable local Python command and the standard library.
- Preserve source wording while removing HTML markup and footnote marker numbers from the passage and translation text.
- Store each Muller comment and linked note as `scholarly_interpretation`, attributed to Muller and cited to its book, passage, and source location.
- Preserve quotations and citations that appear inside Muller’s notes as part of the note text; do not present those writers’ works as separately imported entries.
- Record the user-authorized attribution basis for imported source translations and annotations. This remains user authorization, not an independently verified third-party license.
- Preserve existing generated commentary and themes when refreshing imported source fields.
- Detect unpaired and repeated source markers. Pair translation blocks with the current original in source order, retain repeated source entries, and keep an original source-only when the HTML has no translation. Resolve numbering anomalies through a small, explicit mapping file and retain the HTML’s printed marker in citations where it differs from the corpus number.
- Produce a mapping report without modifying corpus files. The user reviewed and approved the source-order proposal before the corpus write.
- Validate the completed corpus with the existing JSON Schema and semantic validator.

## Non-goals

- Display the imported scholarly comments and footnotes in the reader UI in this milestone. They will be available in the structured corpus for a later presentation decision.
- Generate missing translation, commentary, pinyin, simplified text, or themes.
- Parse the HTML at site runtime or modify the source snapshot.
- Import Legge, Waley, or other cited scholars’ works as separate source records.

## Approaches considered

1. **Repeatable local importer — selected.** Parse the tracked HTML into the existing per-book JSON format, report source irregularities, and require reviewed mappings for ambiguous numbering. This fits the selected local-first stack and makes later re-imports auditable.
2. **Manual copy into JSON.** Avoids parser code but is slow across roughly 480 numbered passages, hard to repeat, and easy to misalign notes.
3. **Use the HTML directly in the site.** Avoids initial extraction but couples the reader to presentation markup and makes passage-level provenance, validation, and future search difficult.

## Current source findings

The parser finds 20 book headings, 489 original passage blocks (488 printed labels), 488 translation blocks (487 printed labels), 34 inline comments, and 59 linked footnote references with bodies. It recognizes malformed closing markers, unbracketed English labels, and the Book 13 `29-30` range. Book 14 repeats original label `14-37` with identical text; both occurrences are retained as passages 37 and 38, which shifts later IDs. Book 17 repeats `17-10` for different texts; both are retained as passages 10 and 11. The imported corpus has one source-only original, Book 14 passage 28. The 54 reviewed mapping exceptions are recorded in `content/source-import-overrides.json` and the full proposal is preserved in the mapping review.

## Data and architecture

- Add a local importer under `scripts/` that reads the tracked HTML, groups passage blocks by book, separates the `[Comment]` blocks, follows footnote links, and emits the 20 JSON files.
- Keep the current corpus schema and validator as the final data contract, extending the commentary schema so `scholarly_interpretation` entries require both a source citation and a rights record; generated project commentary does not need a third-party rights record.
- Mark imported translations and scholarly interpretations with the existing `licensed` status and the user-authorized attribution wording. Use the Muller source URL, passage citation, and note/comment locator.
- Store imported comments and notes in `passage.commentary` with `kind: scholarly_interpretation`, `author: A. Charles Muller`, and English language. Use stable IDs based on passage ID, entry kind, and source note locator.
- Keep generated commentary entries and `themes` already present for a passage. New passages receive empty generated commentary and themes until curated.
- Keep source-label corrections in a small, reviewed import mapping. The report shows source labels, proposed corpus IDs, short Chinese and English excerpts, and linked comment/note references. The importer rejects translation blocks that have no preceding original and keeps missing translations empty rather than inventing content.
- Add focused fixtures and tests for HTML text extraction, comment continuation, note-link association, duplicate labels, mismatch reporting, and preservation of existing generated content.
- Document the import/check commands, source provenance, chosen stack, and remaining review steps in the existing project docs. The site continues to consume JSON only.

## Verification and risks

Run the importer in report/check mode first and show the proposed mappings to the user. Only after the user approves them, write and validate all book files. Run the Python validator tests and corpus validator, plus the frontend lint/type/build checks because the larger corpus will create many more static passage routes. Spot-check representative passages with multiple inline comments and multiple footnotes, a passage whose source marker needs normalization, and the existing generated daily passages.

The source markup is not a clean data interchange format. The import report and explicit mapping checks prevent silent source-to-translation mismatches. Text normalization remains limited to whitespace and removed HTML/footnote marker markup; wording edits require separate editorial review. The reader omits English links and static English routes for the source-only passage while keeping its Chinese route available.
