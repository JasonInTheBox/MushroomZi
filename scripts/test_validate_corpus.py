"""Run with: python -m unittest discover scripts"""
import unittest
from pathlib import Path

from validate_corpus import build_book_validator, semantic_errors


def make_book(passage_id="analects.01.01", commentary_text="A real note."):
    return {
        "book": {"id": "analects.book.01", "number": 1},
        "passages": [
            {
                "id": passage_id,
                "number": 1,
                "original": {"text": "子曰。學而時習之"},
                "translations": [],
                "commentary": [
                    {"id": "c1", "text": commentary_text, "context": "Work"},
                ],
            }
        ],
    }


class SemanticErrorsTest(unittest.TestCase):
    def check(self, book):
        return semantic_errors(book, Path("book-01.json"), {})

    def test_valid_book_has_no_errors(self):
        self.assertEqual(self.check(make_book()), [])

    def test_placeholder_commentary_is_reported(self):
        errors = self.check(make_book(commentary_text="..."))
        self.assertEqual(len(errors), 1)
        self.assertIn("commentary 'c1' text is still a placeholder", errors[0])

    def test_passage_id_must_match_book_number(self):
        errors = self.check(make_book(passage_id="analects.02.01"))
        self.assertEqual(len(errors), 1)
        self.assertIn("has book number 2", errors[0])


def make_schema_book(commentary):
    source = {"title": "The Analects", "citation": "Book 1, passage 1"}
    return {
        "schemaVersion": 1,
        "book": {"id": "analects.book.01", "number": 1, "title": {"chinese": "學而"}},
        "passages": [{
            "id": "analects.01.01",
            "number": 1,
            "original": {
                "language": "zh", "script": "Hant", "textType": "classical_chinese",
                "text": "子曰。學而時習之", "source": source,
            },
            "translations": [{
                "id": "analects.01.01.en.muller", "language": "en", "text": "Learn and practice.",
                "translator": "A. Charles Muller", "source": source,
                "rights": {"reuseStatus": "licensed", "license": "User-authorized reuse with attribution required"},
            }],
            "commentary": commentary,
            "themes": [],
        }],
    }


class CommentarySchemaTest(unittest.TestCase):
    def setUp(self):
        self.validator = build_book_validator()

    def valid_scholarship(self):
        return {
            "id": "analects.01.01.muller.note.01",
            "kind": "scholarly_interpretation",
            "language": "en",
            "text": "A cited scholarly note.",
            "author": "A. Charles Muller",
            "source": {"title": "The Analects", "citation": "Book 1, passage 1, note 1"},
            "rights": {"reuseStatus": "licensed", "license": "User-authorized reuse with attribution required"},
        }

    def test_scholarly_interpretation_requires_source_and_rights(self):
        missing_source = self.valid_scholarship()
        del missing_source["source"]
        missing_rights = self.valid_scholarship()
        del missing_rights["rights"]
        for item in (missing_source, missing_rights):
            with self.subTest(missing=sorted(set(("source", "rights")) - set(item))):
                self.assertTrue(list(self.validator.iter_errors(make_schema_book([item]))))

    def test_generated_commentary_needs_no_source_rights(self):
        generated = {
            "id": "analects.01.01.explanation.en.generated",
            "kind": "project_explanation", "language": "en", "text": "A modern explanation.",
            "author": "Mushroom Zi (AI-generated)",
        }
        self.assertFalse(list(self.validator.iter_errors(make_schema_book([generated]))))

    def test_cited_user_authorized_muller_material_is_valid(self):
        self.assertFalse(list(self.validator.iter_errors(make_schema_book([self.valid_scholarship()]))))


if __name__ == "__main__":
    unittest.main()
