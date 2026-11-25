import re
from html.parser import HTMLParser


BOOK_ANCHOR = re.compile(r"^div-(\d+)$")
NOTE_ANCHOR = re.compile(r"^note-\d+-\d+$")
NOTE_LINK = re.compile(r"#(note-\d+-\d+)$")
ORIGINAL_MARKER = re.compile(r"^\[(\d+-\d+)\]\s*(.*)$", re.DOTALL)
TRANSLATION_MARKER = re.compile(r"^\[(\d+:\d+)\]\s*(.*)$", re.DOTALL)
COMMENT_MARKER = re.compile(r"^\[\s*Comment\s*\]\s*(.*)$", re.DOTALL | re.IGNORECASE)
NOTE_NUMBER = re.compile(r"^\s*\d+\.\s*$")
LEADING_NOTE_NUMBER = re.compile(r"^\s*\d+\.\s*")
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")


def clean_text(value):
    return re.sub(r"\s+", " ", value).strip()


class _AnalectsParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.books = []
        self.notes = {}
        self.book = None
        self.paragraph = None
        self.in_notes = False
        self.skipping_note_link = False
        self.note_anchor = None
        self.note_anchor_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "p":
            if self.paragraph is not None:
                self.finish_paragraph()
            self.paragraph = {"parts": [], "noteRefs": [], "bookAnchor": None}
        elif tag == "br" and self.paragraph is not None:
            self.paragraph["parts"].append(" ")

        if tag != "a":
            return

        anchor_id = attrs.get("id", "")
        if self.paragraph is not None and BOOK_ANCHOR.fullmatch(anchor_id):
            self.paragraph["bookAnchor"] = anchor_id

        note_link = NOTE_LINK.search(attrs.get("href", ""))
        if self.paragraph is not None and note_link:
            self.paragraph["noteRefs"].append(note_link.group(1))
            self.skipping_note_link = True

        if self.in_notes and NOTE_ANCHOR.fullmatch(anchor_id):
            self.note_anchor = anchor_id
            self.note_anchor_parts = []

    def handle_endtag(self, tag):
        if tag == "a":
            if self.note_anchor is not None:
                note_text = clean_text("".join(self.note_anchor_parts))
                if note_text and not NOTE_NUMBER.fullmatch(note_text):
                    note_text = clean_text(LEADING_NOTE_NUMBER.sub("", note_text))
                    self.notes.setdefault(self.note_anchor, note_text)
                self.note_anchor = None
                self.note_anchor_parts = []
            self.skipping_note_link = False
        elif tag == "p" and self.paragraph is not None:
            self.finish_paragraph()

    def handle_data(self, data):
        if self.skipping_note_link:
            return
        if self.paragraph is not None:
            self.paragraph["parts"].append(data)
        if self.note_anchor is not None:
            self.note_anchor_parts.append(data)

    def finish_paragraph(self):
        paragraph = self.paragraph
        self.paragraph = None
        text = clean_text("".join(paragraph["parts"]))

        if paragraph["bookAnchor"]:
            self.start_book(paragraph["bookAnchor"], text)
            return

        if text.casefold() == "notes":
            self.in_notes = True
            return

        if self.in_notes or self.book is None or not text:
            return

        for kind, pattern in (
            ("original", ORIGINAL_MARKER),
            ("translation", TRANSLATION_MARKER),
            ("comment", COMMENT_MARKER),
        ):
            match = pattern.match(text)
            if match:
                marker = match.group(1) if kind != "comment" else None
                body = match.group(1) if kind == "comment" else match.group(2)
                event = {
                    "kind": kind,
                    "marker": marker,
                    "text": clean_text(body),
                    "noteRefs": list(dict.fromkeys(paragraph["noteRefs"])),
                }
                self.book["events"].append(event)
                self.book["lastEvent"] = event
                return

        if self.book["events"] and self.book.get("lastEvent"):
            event = self.book["lastEvent"]
            event["text"] = clean_text(f"{event['text']} {text}")
            event["noteRefs"] = list(
                dict.fromkeys(event["noteRefs"] + paragraph["noteRefs"])
            )

    def start_book(self, anchor, heading):
        match = BOOK_ANCHOR.fullmatch(anchor)
        display = re.match(r"^\s*\d+\.\s*(.*)$", heading)
        title_text = display.group(1) if display else heading
        chinese = "".join(CJK.findall(title_text))
        pinyin = clean_text(CJK.sub("", title_text))
        self.book = {
            "number": int(match.group(1)) - 1,
            "title": {"chinese": chinese, "pinyin": pinyin},
            "events": [],
        }
        self.books.append(self.book)

    def result(self):
        if self.paragraph is not None:
            self.finish_paragraph()
        return {
            "books": [
                {key: value for key, value in book.items() if key != "lastEvent"}
                for book in self.books
            ],
            "notes": self.notes,
        }


def parse_source_html(html):
    parser = _AnalectsParser()
    parser.feed(html)
    parser.close()
    return parser.result()
