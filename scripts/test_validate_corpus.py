"""Run with: python -m unittest discover scripts"""
import unittest
from pathlib import Path

from validate_corpus import semantic_errors


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


if __name__ == "__main__":
    unittest.main()
