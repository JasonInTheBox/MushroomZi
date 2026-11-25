import json
import os
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

try:
    from import_analects_html import parse_source_html
except ImportError:
    parse_source_html = None

try:
    from import_analects_html import build_mapping_report, main
except ImportError:
    build_mapping_report = main = None

try:
    from import_analects_html import resolve_source_mappings, validate_overrides
except ImportError:
    resolve_source_mappings = validate_overrides = None

try:
    from import_analects_html import build_corpus, write_books
except ImportError:
    build_corpus = write_books = None


FIXTURE = Path(__file__).parent / "fixtures" / "analects-import-sample.html"


class ParseSourceHtmlTest(unittest.TestCase):
    def parse_fixture(self):
        self.assertTrue(callable(parse_source_html), "source parser is not implemented")
        return parse_source_html(FIXTURE.read_text(encoding="utf-8"))

    def test_parse_source_sections_and_markers(self):
        book = self.parse_fixture()["books"][0]
        self.assertEqual(book["number"], 1)
        self.assertEqual(
            book["title"], {"chinese": "學而", "pinyin": "Xue er"}
        )
        self.assertEqual(
            [event["marker"] for event in book["events"]], ["1-1", "1:1", None]
        )
        self.assertEqual(book["events"][0]["text"], "子曰。學而時習之。")

    def test_translation_and_comment_continuations_stay_separate(self):
        events = self.parse_fixture()["books"][0]["events"]
        self.assertEqual(events[1]["text"], "The Master said: Learn and practice. Friends come from afar.")
        self.assertEqual(events[2]["text"], "The phrase describes repeated study. It also points to friendship.")

    def test_note_text_uses_reference_target_and_excludes_backlink_labels(self):
        parsed = self.parse_fixture()
        translation = parsed["books"][0]["events"][1]
        self.assertEqual(translation["noteRefs"], ["note-1-1"])
        self.assertNotIn("1", translation["text"])
        self.assertEqual(parsed["notes"], {"note-1-1": "A short footnote."})


class MappingReportTest(unittest.TestCase):
    def make_report(self, events):
        self.assertTrue(callable(build_mapping_report), "mapping report is not implemented")
        return build_mapping_report({
            "books": [{"number": 1, "title": {"chinese": "學而", "pinyin": "Xue er"}, "events": events}],
            "notes": {"note-1-1": "Footnote text."},
        })

    def event(self, kind, marker, text, note_refs=None):
        return {"kind": kind, "marker": marker, "text": text, "noteRefs": note_refs or []}

    def test_report_lists_unmatched_and_duplicate_markers(self):
        report = self.make_report([
            self.event("original", "1-1", "甲文"),
            self.event("translation", "1:1", "First translation."),
            self.event("translation", "1:1", "Alternate translation."),
            self.event("original", "1-2", "乙文"),
            self.event("translation", "1:3", "Unpaired English."),
        ])
        book = report["books"][0]
        unresolved = {(item["kind"], item["marker"]) for item in book["unresolved"]}
        self.assertIn(("original", "1-2"), unresolved)
        self.assertIn(("translation", "1:3"), unresolved)
        duplicates = {(item["kind"], item["marker"]) for item in book["duplicates"]}
        self.assertIn(("translation", "1:1"), duplicates)
        issue = next(item for item in book["unresolved"] if item["marker"] == "1-2")
        self.assertIn("乙文", issue["excerpt"])
        self.assertTrue(issue["candidates"])

    def test_report_deduplicates_exact_repeated_source_block(self):
        report = self.make_report([
            self.event("original", "1-1", "甲文"),
            self.event("original", "1-1", "甲文"),
            self.event("translation", "1:1", "First translation."),
            self.event("original", "1-2", "乙文"),
            self.event("original", "1-2", "丙文"),
            self.event("translation", "1:2", "Second translation."),
        ])
        book = report["books"][0]
        duplicate = next(item for item in book["duplicates"] if item["marker"] == "1-1")
        self.assertEqual(duplicate["occurrences"], 2)
        self.assertEqual(duplicate["distinct_texts"], 1)
        self.assertEqual(len([item for item in book["pairings"] if item["original_marker"] == "1-1"]), 1)
        self.assertIn(("original", "1-2"), {(item["kind"], item["marker"]) for item in book["unresolved"]})

    def test_report_keeps_comments_and_footnotes_with_unresolved_source(self):
        report = self.make_report([
            self.event("original", "1-2", "乙文"),
            self.event("translation", "1:2", "Translation.", ["note-1-1"]),
            self.event("translation", "1:2", "Alternate translation."),
            self.event("comment", None, "Muller comment."),
        ])
        issue = report["books"][0]["unresolved"][0]
        self.assertIn("Muller comment.", issue["comments"])
        self.assertEqual(issue["notes"], [{"id": "note-1-1", "text": "Footnote text."}])

    def test_report_mode_never_changes_book_files(self):
        self.assertTrue(callable(main), "report CLI is not implemented")
        project_root = Path(__file__).resolve().parents[1]
        books_dir = project_root / "content" / "books"
        before = {path.name: path.read_bytes() for path in books_dir.glob("book-*.json")}
        with TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "report.md"
            self.assertEqual(main(["--report", str(report_path)]), 0)
            self.assertTrue(report_path.exists())
            self.assertEqual(before, {path.name: path.read_bytes() for path in books_dir.glob("book-*.json")})

    def test_report_mode_refuses_a_corpus_output_path(self):
        project_root = Path(__file__).resolve().parents[1]
        book_path = project_root / "content" / "books" / "book-01.json"
        before = book_path.read_bytes()
        self.assertNotEqual(main(["--report", str(book_path)]), 0)
        self.assertEqual(book_path.read_bytes(), before)

    def test_live_source_counts_books_markers_and_note_links(self):
        self.assertTrue(callable(build_mapping_report), "mapping report is not implemented")
        source_path = Path(__file__).resolve().parents[1] / "Analects of Confucius 論語.html"
        parsed = parse_source_html(source_path.read_text(encoding="utf-8"))
        report = build_mapping_report(parsed)
        self.assertEqual(report["counts"]["books"], 20)
        self.assertEqual(report["counts"]["original_markers"], 483)
        self.assertEqual(report["counts"]["translation_markers"], 485)
        self.assertEqual(report["counts"]["comments"], 34)
        self.assertEqual(report["counts"]["linked_note_ids"], 59)
        self.assertEqual(report["counts"]["linked_notes_with_bodies"], 59)
        report_items = [item for book in report["books"] for item in book["pairings"] + book["unresolved"]]
        self.assertEqual(sum(len(item["comments"]) for item in report_items), 34)
        self.assertEqual(len({note["id"] for item in report_items for note in item["notes"]}), 59)

    def test_override_resolves_one_marker_occurrence(self):
        parsed = {"books": [{"number": 1, "events": [
            self.event("original", "1-1", "甲文"),
            self.event("translation", "1:2", "Translation."),
        ]}], "notes": {}}
        overrides = {"schemaVersion": 1, "mappings": [
            {"bookNumber": 1, "sourceKind": "translation", "sourceMarker": "1:2", "occurrence": 1, "passageNumber": 1},
        ]}
        resolved = resolve_source_mappings(parsed, overrides)
        self.assertEqual(resolved[(1, "translation", "1:2", 1)], 1)

    def test_duplicate_override_key_is_rejected(self):
        parsed = {"books": [{"number": 1, "events": [self.event("original", "1-1", "甲文")]}], "notes": {}}
        mapping = {"bookNumber": 1, "sourceKind": "original", "sourceMarker": "1-1", "occurrence": 1, "passageNumber": 1}
        with self.assertRaisesRegex(ValueError, "duplicate override"):
            validate_overrides(parsed, {"schemaVersion": 1, "mappings": [mapping, mapping.copy()]})

    def test_out_of_range_passage_number_is_rejected(self):
        parsed = {"books": [{"number": 1, "events": [self.event("original", "1-1", "甲文")]}], "notes": {}}
        overrides = {"schemaVersion": 1, "mappings": [
            {"bookNumber": 1, "sourceKind": "original", "sourceMarker": "1-1", "occurrence": 1, "passageNumber": 100},
        ]}
        with self.assertRaisesRegex(ValueError, "passageNumber"):
            validate_overrides(parsed, overrides)

    def test_unresolved_exception_blocks_corpus_write(self):
        parsed = {"books": [{"number": 1, "events": [
            self.event("original", "1-1", "甲文"),
            self.event("translation", "1:2", "Unmapped translation."),
        ]}], "notes": {}}
        with self.assertRaisesRegex(ValueError, "unresolved source mappings"):
            resolve_source_mappings(parsed, {"schemaVersion": 1, "mappings": []})

    def source_fixture(self):
        return {
            "books": [{"number": 1, "title": {"chinese": "學而", "pinyin": "Xue er"}, "events": [
                self.event("original", "1-1", "子曰。學而時習之。"),
                self.event("translation", "1:1", "Learn and practice.", ["note-1-1"]),
                self.event("comment", None, "Muller explains the phrase."),
            ]}],
            "notes": {"note-1-1": "A linked scholarly footnote."},
        }

    def existing_book(self):
        return {
            "schemaVersion": 1,
            "book": {"id": "analects.book.01", "number": 1, "title": {"chinese": "學而", "pinyin": "Xué ér"}},
            "passages": [{
                "id": "analects.01.01", "number": 1,
                "original": {"variants": {"simplified": "子曰。学而时习之"}},
                "translations": [
                    {"id": "analects.01.01.en.muller", "language": "en", "text": "Old translation.", "translator": "A. Charles Muller"},
                    {"id": "analects.01.01.en.other", "language": "en", "text": "Another translation.", "translator": "Another Translator"},
                ],
                "commentary": [
                    {"id": "analects.01.01.explanation.en.generated", "kind": "project_explanation", "language": "en", "text": "Generated text stays.", "author": "Mushroom Zi (AI-generated)"},
                    {"id": "analects.01.01.muller.comment.01", "kind": "scholarly_interpretation", "language": "en", "text": "Old imported comment.", "author": "A. Charles Muller"},
                ],
                "themes": ["learning"],
            }],
        }

    def valid_writer_books(self):
        books = []
        for number in range(1, 21):
            passage_id = f"analects.{number:02}.01"
            source = {"title": "The Analects", "citation": f"Book {number}, passage 1"}
            books.append({
                "schemaVersion": 1,
                "book": {"id": f"analects.book.{number:02}", "number": number, "title": {"chinese": "學而"}},
                "passages": [{
                    "id": passage_id, "number": 1,
                    "original": {"language": "zh", "script": "Hant", "textType": "classical_chinese", "text": "子曰。學而時習之", "source": source},
                    "translations": [{
                        "id": f"{passage_id}.en.muller", "language": "en", "text": "Learn and practice.",
                        "translator": "A. Charles Muller", "source": source,
                        "rights": {"reuseStatus": "licensed", "license": "User-authorized reuse with attribution required"},
                    }],
                    "commentary": [], "themes": [],
                }],
            })
        return books

    def test_build_corpus_uses_stable_muller_ids_and_citations(self):
        self.assertTrue(callable(build_corpus), "corpus builder is not implemented")
        books = build_corpus(self.source_fixture(), {"schemaVersion": 1, "mappings": []}, {})
        passage = books[0]["passages"][0]
        self.assertEqual(passage["translations"][0]["id"], "analects.01.01.en.muller")
        self.assertEqual(passage["commentary"][0]["id"], "analects.01.01.muller.comment.01")
        self.assertEqual(passage["commentary"][0]["source"]["citation"], "Book 1, passage 1, inline comment 1")
        self.assertEqual(passage["commentary"][1]["id"], "analects.01.01.muller.note.01")
        self.assertEqual(passage["commentary"][1]["source"]["citation"], "Book 1, passage 1, footnote note-1-1")
        self.assertEqual(passage["commentary"][1]["rights"]["reuseStatus"], "licensed")

    def test_build_corpus_attaches_linked_notes_to_referencing_passage(self):
        books = build_corpus(self.source_fixture(), {"schemaVersion": 1, "mappings": []}, {})
        passage = books[0]["passages"][0]
        note = next(item for item in passage["commentary"] if item["kind"] == "scholarly_interpretation" and ".note." in item["id"])
        self.assertEqual(note["text"], "A linked scholarly footnote.")
        self.assertEqual(note["author"], "A. Charles Muller")

    def test_build_corpus_cites_printed_label_when_override_changes_number(self):
        parsed = self.source_fixture()
        parsed["books"][0]["events"][1]["marker"] = "1:2"
        overrides = {"schemaVersion": 1, "mappings": [
            {"bookNumber": 1, "sourceKind": "translation", "sourceMarker": "1:2", "occurrence": 1, "passageNumber": 1},
        ]}
        passage = build_corpus(parsed, overrides, {})[0]["passages"][0]
        self.assertEqual(
            passage["translations"][0]["source"]["citation"],
            "Book 1, printed label 1:2 (mapped to passage 1)",
        )

    def test_merge_preserves_generated_content_and_is_stable(self):
        existing = {1: self.existing_book()}
        first = build_corpus(self.source_fixture(), {"schemaVersion": 1, "mappings": []}, existing)
        second = build_corpus(self.source_fixture(), {"schemaVersion": 1, "mappings": []}, existing)
        passage = first[0]["passages"][0]
        self.assertEqual(first, second)
        self.assertEqual(passage["themes"], ["learning"])
        self.assertIn("Generated text stays.", [item["text"] for item in passage["commentary"]])
        self.assertNotIn("Old imported comment.", [item["text"] for item in passage["commentary"]])
        self.assertEqual(passage["original"]["variants"]["simplified"], "子曰。学而时习之")
        self.assertIn("Another translation.", [item["text"] for item in passage["translations"]])

    def test_write_refuses_unresolved_mappings_without_changing_files(self):
        self.assertTrue(callable(main), "write CLI is not implemented")
        project_root = Path(__file__).resolve().parents[1]
        books_dir = project_root / "content" / "books"
        before = {path.name: path.read_bytes() for path in books_dir.glob("book-*.json")}
        with TemporaryDirectory() as temporary_directory:
            override_path = Path(temporary_directory) / "overrides.json"
            override_path.write_text('{"schemaVersion":1,"mappings":[]}', encoding="utf-8")
            self.assertNotEqual(main(["--write", "--overrides", str(override_path)]), 0)
        self.assertEqual(before, {path.name: path.read_bytes() for path in books_dir.glob("book-*.json")})

    def test_writer_validates_then_writes_all_books_to_output_directory(self):
        self.assertTrue(callable(write_books), "corpus writer is not implemented")
        books = self.valid_writer_books()
        with TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "books"
            write_books(books, output_dir)
            written = sorted(output_dir.glob("book-*.json"))
            self.assertEqual(len(written), 20)
            self.assertEqual(json.loads(written[0].read_text(encoding="utf-8")), books[0])

    def test_writer_rejects_incomplete_corpus_without_touching_files(self):
        self.assertTrue(callable(write_books), "corpus writer is not implemented")
        with TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "books"
            output_dir.mkdir()
            existing = output_dir / "book-01.json"
            existing.write_text("sentinel", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly books 1 through 20"):
                write_books([], output_dir)
            self.assertEqual(existing.read_text(encoding="utf-8"), "sentinel")

    def test_writer_rolls_back_if_a_file_replace_fails(self):
        books = self.valid_writer_books()
        real_replace = os.replace
        calls = 0

        def fail_second_replace(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated replace failure")
            return real_replace(source, target)

        with TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "books"
            output_dir.mkdir()
            for number in range(1, 21):
                (output_dir / f"book-{number:02}.json").write_text(f"old-{number}", encoding="utf-8")
            with patch("import_analects_html.os.replace", side_effect=fail_second_replace):
                with self.assertRaisesRegex(OSError, "simulated replace failure"):
                    write_books(books, output_dir)
            self.assertEqual(
                [(output_dir / f"book-{number:02}.json").read_text(encoding="utf-8") for number in range(1, 21)],
                [f"old-{number}" for number in range(1, 21)],
            )


if __name__ == "__main__":
    unittest.main()
