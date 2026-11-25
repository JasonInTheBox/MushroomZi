import unittest
from pathlib import Path

try:
    from import_analects_html import parse_source_html
except ImportError:
    parse_source_html = None


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


if __name__ == "__main__":
    unittest.main()
