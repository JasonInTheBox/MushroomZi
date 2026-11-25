# Analects HTML Corpus Import Design

**Status:** Approved by the user on 2026-11-25 (UTC). The user selected the local-first stack, chose to import Muller’s inline comments and footnotes with the text and translation, and requested review of proposed mappings before corpus files are written.

## Intent

Turn the tracked `Analects of Confucius 論語.html` snapshot into the project’s version-controlled, per-book JSON corpus. Preserve the Classical Chinese text, A. Charles Muller’s English translation, his inline comments, and linked footnotes as distinct, attributed source material. Keep generated Mushroom Zi commentary separate.

## Goals

- Extract all 20 books to `content/books/book-01.json` through `book-20.json` using a repeatable local Python command and the standard library.
- Preserve source wording while removing HTML markup and footnote marker numbers from the passage and translation text.
- Store each Muller comment and linked note as `scholarly_interpretation`, attributed to Muller and cited to its book, passage, and source location.
- Preserve quotations and citations that appear inside Muller’s notes as part of the note text; do not present those writers’ works as separately imported entries.
- Record the user-authorized attribution basis for imported source translations and annotations. This remains user authorization, not an independently verified third-party license.
- Preserve existing generated commentary and themes when refreshing imported source fields.
- Detect unpaired, duplicated, or unresolved source markers and refuse to write an incomplete corpus. Resolve source numbering anomalies through a small, explicit mapping file and retain the HTML’s printed marker in citations where it differs from the corpus number.
- Produce a proposed mapping report without modifying corpus files. The user reviews and approves the exceptions before the importer writes any corpus data.
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

The snapshot has 20 book headings, 483 Classical Chinese markers, 485 English markers, and 59 distinct linked footnote references. The marker counts do not align cleanly: some Chinese or English labels are missing, repeated, or duplicated. For example, Book 14 repeats a Chinese marker for two different texts, and Book 17 repeats marker 17-10 for different texts. A best-effort positional match could silently attach the wrong translation or note, so extraction must audit and explicitly resolve these cases before writing canonical JSON.

## Data and architecture

- Add a local importer under `scripts/` that reads the tracked HTML, groups passage blocks by book, separates the `[Comment]` blocks, follows footnote links, and emits the 20 JSON files.
- Keep the current corpus schema and validator as the final data contract, extending the commentary schema so `scholarly_interpretation` entries require both a source citation and a rights record; generated project commentary does not need a third-party rights record.
- Mark imported translations and scholarly interpretations with the existing `licensed` status and the user-authorized attribution wording. Use the Muller source URL, passage citation, and note/comment locator.
- Store imported comments and notes in `passage.commentary` with `kind: scholarly_interpretation`, `author: A. Charles Muller`, and English language. Use stable IDs based on passage ID, entry kind, and source note locator.
- Keep generated commentary entries and `themes` already present for a passage. New passages receive empty generated commentary and themes until curated.
- Keep source-label corrections in a small, reviewed import mapping. The report shows source labels, proposed corpus IDs, short Chinese and English excerpts, and linked comment/note references. The importer does not write when a verse, translation, comment, or note cannot be assigned with confidence; after a complete report is reviewed and approved, a separate write step updates corpus files.
- Add focused fixtures and tests for HTML text extraction, comment continuation, note-link association, duplicate labels, mismatch reporting, and preservation of existing generated content.
- Document the import/check commands, source provenance, chosen stack, and remaining review steps in the existing project docs. The site continues to consume JSON only.

## Verification and risks

Run the importer in report/check mode first and show the proposed mappings to the user. Only after the user approves them, write and validate all book files. Run the Python validator tests and corpus validator, plus the frontend lint/type/build checks because the larger corpus will create many more static passage routes. Spot-check representative passages with multiple inline comments and multiple footnotes, a passage whose source marker needs normalization, and the existing generated daily passages.

The source markup is not a clean data interchange format. The import report and explicit mapping checks are required to prevent silent source-to-translation mismatches. Text normalization must remain limited to whitespace and removed HTML/footnote marker markup; edits to wording require separate editorial review.
