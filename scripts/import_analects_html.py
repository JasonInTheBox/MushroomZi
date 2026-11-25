import argparse
import json
import os
import re
import sys
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory

from validate_corpus import build_book_validator, semantic_errors


BOOK_ANCHOR = re.compile(r"^div-(\d+)$")
NOTE_ANCHOR = re.compile(r"^note-\d+-\d+$")
NOTE_LINK = re.compile(r"#(note-\d+-\d+)$")
ORIGINAL_MARKER = re.compile(r"^\[(\d+-\d+)\]\s*(.*)$", re.DOTALL)
TRANSLATION_MARKER = re.compile(r"^\[(\d+:\d+)\]\s*(.*)$", re.DOTALL)
COMMENT_MARKER = re.compile(r"^\[\s*Comment\s*\]\s*(.*)$", re.DOTALL | re.IGNORECASE)
NOTE_NUMBER = re.compile(r"^\s*\d+\.\s*$")
LEADING_NOTE_NUMBER = re.compile(r"^\s*\d+\.\s*")
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "Analects of Confucius 論語.html"
SOURCE_URL = "https://www.acmuller.net/con-dao/analects.html"
MULLER_RIGHTS = {
    "reuseStatus": "licensed",
    "license": "User-authorized reuse with attribution required",
}


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


def _excerpt(text, limit=110):
    text = clean_text(text)
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def _passage_id(book_number, marker):
    match = re.fullmatch(rf"{book_number}[-:](\d+)", marker or "")
    return f"analects.{book_number:02}.{int(match.group(1)):02}" if match else None


def _marker_key(marker):
    return marker.replace("-", ":") if marker else None


def validate_overrides(parsed, overrides):
    if not isinstance(overrides, dict) or set(overrides) != {"schemaVersion", "mappings"}:
        raise ValueError("override file must contain only schemaVersion and mappings")
    if type(overrides["schemaVersion"]) is not int or overrides["schemaVersion"] != 1 or not isinstance(overrides["mappings"], list):
        raise ValueError("override schemaVersion must be 1 and mappings must be a list")

    source_counts = {}
    for book in parsed["books"]:
        for event in book["events"]:
            kind, marker = event.get("kind"), event.get("marker")
            if kind in ("original", "translation") and marker:
                key = (book["number"], kind, marker)
                source_counts[key] = source_counts.get(key, 0) + 1

    result = {}
    required_fields = {"bookNumber", "sourceKind", "sourceMarker", "occurrence", "passageNumber"}
    for item in overrides["mappings"]:
        if not isinstance(item, dict) or set(item) != required_fields:
            raise ValueError(f"each mapping must contain exactly {sorted(required_fields)}")
        book_number, kind = item["bookNumber"], item["sourceKind"]
        marker, occurrence, passage_number = item["sourceMarker"], item["occurrence"], item["passageNumber"]
        if type(book_number) is not int or not 1 <= book_number <= 20:
            raise ValueError("bookNumber must be an integer from 1 to 20")
        if kind not in ("original", "translation") or not isinstance(marker, str) or not marker:
            raise ValueError("sourceKind and sourceMarker must identify a source event")
        if type(occurrence) is not int or occurrence < 1:
            raise ValueError("occurrence must be a positive integer")
        if type(passage_number) is not int or not 1 <= passage_number <= 99:
            raise ValueError("passageNumber must be an integer from 1 to 99")
        key = (book_number, kind, marker, occurrence)
        if key in result:
            raise ValueError(f"duplicate override for {key}")
        if occurrence > source_counts.get((book_number, kind, marker), 0):
            raise ValueError(f"override does not match a source occurrence: {key}")
        result[key] = passage_number
    return result


def resolve_source_mappings(parsed, overrides):
    """Return event-occurrence mappings only when each book pairs one-to-one."""
    override_map = validate_overrides(parsed, overrides)
    result = {}

    for book in parsed["books"]:
        number = book["number"]
        occurrences, entries, distinct_by_marker = {}, {}, {}
        for event in book["events"]:
            kind, marker = event.get("kind"), event.get("marker")
            if kind not in ("original", "translation") or not marker:
                continue
            source_key = (number, kind, marker)
            occurrences[source_key] = occurrences.get(source_key, 0) + 1
            key = (kind, marker, event["text"])
            entries.setdefault(key, []).append(occurrences[source_key])
            distinct_by_marker.setdefault((kind, marker), set()).add(event["text"])

        assigned_by_kind = {"original": {}, "translation": {}}
        for (kind, marker, text), indexes in entries.items():
            explicit = {
                override_map[(number, kind, marker, index)]
                for index in indexes
                if (number, kind, marker, index) in override_map
            }
            if len(explicit) > 1:
                raise ValueError(f"conflicting overrides for repeated source block: {number} {marker}")
            passage_number = next(iter(explicit), None)
            if passage_number is None:
                if len(distinct_by_marker[(kind, marker)]) > 1:
                    raise ValueError(f"unresolved source mappings for repeated marker: {number} {marker}")
                passage_id = _passage_id(number, marker)
                if passage_id is None:
                    raise ValueError(f"unresolved source mappings for invalid marker: {number} {marker}")
                passage_number = int(passage_id.rsplit(".", 1)[1])
            assigned_by_kind[kind].setdefault(passage_number, []).append((marker, text))
            for index in indexes:
                result[(number, kind, marker, index)] = passage_number

        for kind, assignments in assigned_by_kind.items():
            collisions = [passage for passage, sources in assignments.items() if len(sources) > 1]
            if collisions:
                raise ValueError(f"multiple {kind} source blocks map to passage(s) {collisions} in book {number}")
        original_numbers = set(assigned_by_kind["original"])
        translation_numbers = set(assigned_by_kind["translation"])
        if original_numbers != translation_numbers:
            missing_translations = sorted(original_numbers - translation_numbers)
            missing_originals = sorted(translation_numbers - original_numbers)
            raise ValueError(
                f"unresolved source mappings in book {number}: "
                f"missing translations for {missing_translations}; "
                f"missing originals for {missing_originals}"
            )
    return result


def _citation(book_number, passage_number, marker, locator=None):
    marker_match = re.fullmatch(rf"{book_number}[-:](\d+)", marker or "")
    if marker_match and int(marker_match.group(1)) == passage_number:
        citation = f"Book {book_number}, passage {passage_number}"
    else:
        citation = f"Book {book_number}, printed label {marker} (mapped to passage {passage_number})"
    return f"{citation}, {locator}" if locator else citation


def _source_record(citation):
    return {"title": "The Analects", "url": SOURCE_URL, "citation": citation}


def _note_ordinal(note_id):
    match = re.fullmatch(r"note-\d+-(\d+)", note_id)
    if match is None:
        raise ValueError(f"invalid source note ID: {note_id}")
    return int(match.group(1))


def build_corpus(parsed, overrides, existing_books):
    mappings = resolve_source_mappings(parsed, overrides)
    result = []

    for book in parsed["books"]:
        number = book["number"]
        entries, occurrences = {}, {}
        note_ids_by_passage, current_passage = {}, None
        for event in book["events"]:
            kind, marker = event.get("kind"), event.get("marker")
            if kind in ("original", "translation"):
                key = (number, kind, marker)
                occurrences[key] = occurrences.get(key, 0) + 1
                passage_number = mappings[(number, kind, marker, occurrences[key])]
                current_passage = passage_number
                entry = entries.setdefault(passage_number, {
                    "original": None, "translation": None, "comments": [],
                    "original_marker": None, "translation_marker": None,
                })
                field = "original" if kind == "original" else "translation"
                if entry[field] is not None and entry[field]["text"] != event["text"]:
                    raise ValueError(f"multiple {kind} texts map to book {number}, passage {passage_number}")
                entry[field] = event
                entry[f"{field}_marker"] = marker
            elif kind == "comment":
                if current_passage is None:
                    raise ValueError(f"comment has no preceding passage in book {number}")
                entry = entries.setdefault(current_passage, {
                    "original": None, "translation": None, "comments": [],
                    "original_marker": None, "translation_marker": None,
                })
                entry["comments"].append(event["text"])
            if current_passage is not None:
                refs = event.get("noteRefs", [])
                note_ids_by_passage[current_passage] = list(dict.fromkeys(note_ids_by_passage.get(current_passage, []) + refs))

        existing = existing_books.get(number, {})
        old_passages = {passage["number"]: passage for passage in existing.get("passages", [])}
        passages = []
        for passage_number, entry in sorted(entries.items()):
            if entry["original"] is None or entry["translation"] is None:
                raise ValueError(f"unresolved source mappings for book {number}, passage {passage_number}")
            passage_id = f"analects.{number:02}.{passage_number:02}"
            old = old_passages.get(passage_number, {})
            original = deepcopy(old.get("original", {}))
            variants = original.get("variants")
            original.update({
                "language": "zh", "script": "Hant", "textType": "classical_chinese",
                "text": entry["original"]["text"],
                "source": _source_record(_citation(number, passage_number, entry["original_marker"])),
            })
            if variants is not None:
                original["variants"] = variants

            translation_marker = entry["translation_marker"]
            translation = {
                "id": f"{passage_id}.en.muller",
                "language": "en",
                "text": entry["translation"]["text"],
                "translator": "A. Charles Muller",
                "source": _source_record(_citation(number, passage_number, translation_marker)),
                "rights": deepcopy(MULLER_RIGHTS),
            }
            translations = [
                item for item in old.get("translations", [])
                if not (item.get("id") == translation["id"] or (
                    item.get("translator") == "A. Charles Muller" and item.get("source", {}).get("url") == SOURCE_URL
                ))
            ]
            translations.append(translation)

            commentary = [
                deepcopy(item) for item in old.get("commentary", [])
                if not item.get("id", "").startswith(f"{passage_id}.muller.")
            ]
            for ordinal, text in enumerate(entry["comments"], 1):
                commentary.append({
                    "id": f"{passage_id}.muller.comment.{ordinal:02}",
                    "kind": "scholarly_interpretation", "language": "en", "text": text,
                    "author": "A. Charles Muller",
                    "source": _source_record(_citation(
                        number, passage_number, entry["original_marker"], f"inline comment {ordinal}"
                    )),
                    "rights": deepcopy(MULLER_RIGHTS),
                })

            seen_note_ordinals = set()
            for note_id in note_ids_by_passage.get(passage_number, []):
                note_text = parsed["notes"].get(note_id)
                if not note_text:
                    raise ValueError(f"missing source text for linked note {note_id}")
                ordinal = _note_ordinal(note_id)
                if ordinal in seen_note_ordinals:
                    raise ValueError(f"source note ID collision in book {number}, passage {passage_number}: {ordinal}")
                seen_note_ordinals.add(ordinal)
                commentary.append({
                    "id": f"{passage_id}.muller.note.{ordinal:02}",
                    "kind": "scholarly_interpretation", "language": "en", "text": note_text,
                    "author": "A. Charles Muller",
                    "source": _source_record(_citation(
                        number, passage_number, entry["original_marker"], f"footnote {note_id}"
                    )),
                    "rights": deepcopy(MULLER_RIGHTS),
                })

            passages.append({
                "id": passage_id,
                "number": passage_number,
                "original": original,
                "translations": translations,
                "commentary": commentary,
                "themes": deepcopy(old.get("themes", [])),
            })

        title = deepcopy(existing.get("book", {}).get("title", {}))
        title["chinese"] = book["title"]["chinese"]
        title.setdefault("pinyin", book["title"]["pinyin"])
        result.append({
            "schemaVersion": 1,
            "book": {"id": f"analects.book.{number:02}", "number": number, "title": title},
            "passages": passages,
        })
    return result


def write_books(books, output_dir):
    if not isinstance(books, list):
        raise ValueError("refusing to write: corpus records must be a list")
    try:
        numbers = [book["book"]["number"] for book in books]
    except (KeyError, TypeError) as error:
        raise ValueError("refusing to write: each record must include book.number") from error
    if any(type(number) is not int for number in numbers) or sorted(numbers) != list(range(1, 21)):
        raise ValueError("refusing to write: corpus must contain exactly books 1 through 20")

    validator = build_book_validator()
    seen_ids, serialized = {}, {}
    errors = []
    for book in books:
        number = book["book"]["number"]
        path = Path(f"book-{number:02}.json")
        schema_errors = list(validator.iter_errors(book))
        for error in schema_errors:
            location = ".".join(str(part) for part in error.absolute_path)
            errors.append(f"{path.name}: {location or '(document)'}: {error.message}")
        if not schema_errors:
            errors.extend(semantic_errors(book, path, seen_ids))
        serialized[path.name] = json.dumps(book, ensure_ascii=False, indent=2) + "\n"
    if errors:
        raise ValueError("refusing to write invalid corpus:\n- " + "\n- ".join(errors))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    unexpected = {path.name for path in output_dir.glob("book-*.json")} - set(serialized)
    if unexpected:
        raise ValueError(f"refusing to write with unexpected book files: {sorted(unexpected)}")
    backups = {
        name: (output_dir / name).read_bytes()
        for name in serialized if (output_dir / name).exists()
    }
    with TemporaryDirectory(dir=output_dir.parent, prefix=".analects-import-") as staging_dir:
        staging = Path(staging_dir)
        for name, text in serialized.items():
            (staging / name).write_text(text, encoding="utf-8", newline="\n")
        replaced = []
        try:
            for name in serialized:
                os.replace(staging / name, output_dir / name)
                replaced.append(name)
        except OSError:
            for name in reversed(replaced):
                target = output_dir / name
                if name in backups:
                    restore = staging / f"{name}.backup"
                    restore.write_bytes(backups[name])
                    os.replace(restore, target)
                else:
                    target.unlink(missing_ok=True)
            raise


def build_mapping_report(parsed):
    """Summarize source labels and only pair unique matching markers."""
    books = []
    total_originals = total_translations = total_comments = 0
    linked_note_ids = set()
    referenced_notes = set()

    for book in parsed["books"]:
        number = book["number"]
        original_groups, translation_groups = {}, {}
        duplicates, unresolved, pairings = [], [], []
        group_annotations = {}
        current_original = None
        original_count = translation_count = comment_count = 0

        for order, event in enumerate(book["events"], 1):
            kind = event["kind"]
            marker = event.get("marker") or "(unmarked)"
            if kind in ("original", "translation"):
                groups = original_groups if kind == "original" else translation_groups
                group = groups.setdefault(marker, {})
                entry = group.setdefault(event["text"], {
                    "marker": marker,
                    "text": event["text"],
                    "order": order,
                    "occurrences": 0,
                    "note_refs": [],
                })
                entry["occurrences"] += 1
                entry["order"] = min(entry["order"], order)
                entry["note_refs"] = list(dict.fromkeys(entry["note_refs"] + event.get("noteRefs", [])))
                if kind == "original":
                    original_count += 1
                    current_original = (marker, event["text"])
                    group_annotations.setdefault(current_original, {"comments": [], "note_refs": []})
                else:
                    translation_count += 1
                refs = event.get("noteRefs", [])
                if current_original:
                    annotation = group_annotations.setdefault(current_original, {"comments": [], "note_refs": []})
                    annotation["note_refs"] = list(dict.fromkeys(annotation["note_refs"] + refs))
                linked_note_ids.update(refs)
                referenced_notes.update(refs)
            elif kind == "comment":
                comment_count += 1
                if current_original:
                    annotation = group_annotations.setdefault(current_original, {"comments": [], "note_refs": []})
                    annotation["comments"].append(event["text"])
                    annotation["note_refs"] = list(dict.fromkeys(annotation["note_refs"] + event.get("noteRefs", [])))
                refs = event.get("noteRefs", [])
                linked_note_ids.update(refs)
                referenced_notes.update(refs)

        total_originals += original_count
        total_translations += translation_count
        total_comments += comment_count

        for kind, groups in (("original", original_groups), ("translation", translation_groups)):
            for marker, text_groups in groups.items():
                occurrences = sum(item["occurrences"] for item in text_groups.values())
                if occurrences > 1:
                    duplicates.append({
                        "kind": kind,
                        "marker": marker,
                        "occurrences": occurrences,
                        "distinct_texts": len(text_groups),
                        "excerpts": [_excerpt(text) for text in text_groups],
                    })

        originals_by_key, translations_by_key = {}, {}
        for marker, entries in original_groups.items():
            originals_by_key.setdefault(_marker_key(marker), []).extend(entries.values())
        for marker, entries in translation_groups.items():
            translations_by_key.setdefault(_marker_key(marker), []).extend(entries.values())

        all_keys = dict.fromkeys([*originals_by_key, *translations_by_key])
        for key in all_keys:
            original_entries = originals_by_key.get(key, [])
            translation_entries = translations_by_key.get(key, [])
            if len(original_entries) == len(translation_entries) == 1:
                original, translation = original_entries[0], translation_entries[0]
                annotation = group_annotations.get(
                    (original["marker"], original["text"]), {"comments": [], "note_refs": []}
                )
                refs = list(dict.fromkeys(annotation["note_refs"] + original["note_refs"] + translation["note_refs"]))
                pairings.append({
                    "passage_id": _passage_id(number, original["marker"]),
                    "original_marker": original["marker"],
                    "translation_marker": translation["marker"],
                    "original": original["text"],
                    "translation": translation["text"],
                    "comments": annotation["comments"],
                    "notes": [{"id": note_id, "text": parsed["notes"].get(note_id, "")} for note_id in refs],
                })
                continue

            for kind, entries, candidates in (
                ("original", original_entries, translation_entries),
                ("translation", translation_entries, original_entries),
            ):
                if not entries:
                    continue
                candidate_kind = "translation" if kind == "original" else "original"
                all_candidates = [entry for values in (translation_groups if kind == "original" else original_groups).values() for entry in values.values()]
                for entry in entries:
                    annotation = group_annotations.get(
                        (entry["marker"], entry["text"]),
                        {"comments": [], "note_refs": entry["note_refs"] if kind == "translation" else []},
                    )
                    nearby = sorted(
                        all_candidates,
                        key=lambda candidate: (
                            candidate["marker"] != (key or "").replace(":", "-" if candidate_kind == "original" else ":"),
                            abs(candidate["order"] - entry["order"]),
                        ),
                    )[:3]
                    reason = "missing counterpart" if not candidates else "repeated marker is ambiguous"
                    excerpt = _excerpt(entry["text"])
                    unresolved.append({
                        "kind": kind,
                        "marker": entry["marker"],
                        "reason": reason,
                        "passage_id": _passage_id(number, entry["marker"]) if kind == "original" else None,
                        "excerpt": excerpt,
                        "comments": annotation["comments"],
                        "notes": [
                            {"id": note_id, "text": parsed["notes"].get(note_id, "")}
                            for note_id in annotation["note_refs"]
                        ],
                        "candidates": [
                            {
                                "kind": candidate_kind,
                                "marker": item["marker"],
                                "passage_id": _passage_id(number, item["marker"]),
                                "excerpt": _excerpt(item["text"], 75),
                            }
                            for item in nearby
                        ],
                    })

        books.append({
            "number": number,
            "title": book["title"],
            "counts": {"original_markers": original_count, "translation_markers": translation_count, "comments": comment_count},
            "pairings": pairings,
            "unresolved": unresolved,
            "duplicates": duplicates,
        })

    note_ids = set(parsed["notes"])
    return {
        "counts": {
            "books": len(books),
            "original_markers": total_originals,
            "translation_markers": total_translations,
            "comments": total_comments,
            "linked_note_ids": len(linked_note_ids),
            "linked_notes_with_bodies": len(linked_note_ids & note_ids),
            "missing_note_bodies": sorted(linked_note_ids - note_ids),
            "unlinked_note_bodies": sorted(note_ids - referenced_notes),
        },
        "books": books,
    }


def render_mapping_report(report):
    counts = report["counts"]
    lines = [
        "# Analects source mapping review",
        "",
        "**Status: proposed; no corpus files were written.** Unique matching labels are shown as proposed pairings. Repeated or unmatched labels remain unresolved and require review before import.",
        "",
        "Source: [A. Charles Muller, The Analects](http://www.acmuller.net/con-dao/analects.html), from the tracked HTML snapshot.",
        "",
        "## Source totals",
        "",
        f"- Books: {counts['books']}",
        f"- Classical Chinese blocks: {counts['original_markers']}",
        f"- English translation blocks: {counts['translation_markers']}",
        f"- Inline comments: {counts['comments']}",
        f"- Distinct linked footnote IDs: {counts['linked_note_ids']} ({counts['linked_notes_with_bodies']} with note text)",
        f"- Unlinked footnote bodies: {len(counts['unlinked_note_bodies'])}",
        f"- Unresolved marker entries: {sum(len(book['unresolved']) for book in report['books'])}",
        "",
    ]

    def cell(value):
        return clean_text(str(value)).replace("|", "\\|")

    for book in report["books"]:
        lines.extend([
            f"## Book {book['number']}: {book['title']['chinese']} ({book['title']['pinyin']})",
            "",
            f"Counts: {book['counts']['original_markers']} Chinese, {book['counts']['translation_markers']} English, {book['counts']['comments']} comments.",
            "",
        ])
        if book["pairings"]:
            lines.extend([
                "### Unique marker pairings",
                "",
                "| Proposed corpus ID | Printed labels | Classical Chinese excerpt | English excerpt | Muller comments / footnotes |",
                "|---|---|---|---|---|",
            ])
            for item in book["pairings"]:
                annotations = [f"Comment: {_excerpt(text, 70)}" for text in item["comments"]]
                annotations.extend(f"{note['id']}: {_excerpt(note['text'], 70)}" for note in item["notes"])
                lines.append(
                    f"| {cell(item['passage_id'])} | {cell(item['original_marker'])} / {cell(item['translation_marker'])} | {cell(_excerpt(item['original'], 85))} | {cell(_excerpt(item['translation'], 85))} | {cell('; '.join(annotations) or '—')} |"
                )
            lines.append("")
        if book["unresolved"]:
            lines.extend([
                "### Unresolved markers (no automatic pairing)",
                "",
                "| Kind | Source label | Reason | Excerpt | Muller comments / footnotes | Source-order candidates |",
                "|---|---|---|---|---|---|",
            ])
            for item in book["unresolved"]:
                candidates = "; ".join(
                    f"{candidate['kind']} {candidate['marker']} → {candidate['passage_id'] or 'no ID'}: {candidate['excerpt']}"
                    for candidate in item["candidates"]
                ) or "none"
                annotations = [f"Comment: {_excerpt(text, 70)}" for text in item["comments"]]
                annotations.extend(f"{note['id']}: {_excerpt(note['text'], 70)}" for note in item["notes"])
                lines.append(
                    f"| {cell(item['kind'])} | {cell(item['marker'])} | {cell(item['reason'])} | {cell(item['excerpt'])} | {cell('; '.join(annotations) or '—')} | {cell(candidates)} |"
                )
            lines.append("")
        if book["duplicates"]:
            lines.extend([
                "### Repeated source labels",
                "",
                "Exact repeated text is represented once in proposed pairings and identified here. Different texts under one label remain unresolved.",
                "",
                "| Kind | Label | Occurrences | Distinct texts | Excerpts |",
                "|---|---|---:|---:|---|",
            ])
            for item in book["duplicates"]:
                lines.append(
                    f"| {cell(item['kind'])} | {cell(item['marker'])} | {item['occurrences']} | {item['distinct_texts']} | {cell(' / '.join(item['excerpts']))} |"
                )
            lines.append("")

    if counts["missing_note_bodies"] or counts["unlinked_note_bodies"]:
        lines.extend(["## Footnote integrity", ""])
        lines.extend(f"- Missing note body: `{cell(note_id)}`" for note_id in counts["missing_note_bodies"])
        lines.extend(f"- Unlinked note body: `{cell(note_id)}`" for note_id in counts["unlinked_note_bodies"])
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit source passage labels and write a review report.")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--report", type=Path, help="Markdown path for the proposed mapping report")
    modes.add_argument("--write", action="store_true", help="write the resolved corpus to content/books")
    parser.add_argument("--overrides", type=Path, help="reviewed source mapping overrides (required with --write)")
    args = parser.parse_args(argv)
    if args.write and args.overrides is None:
        parser.error("--overrides is required with --write")
    if args.report and args.overrides is not None:
        parser.error("--overrides can only be used with --write")
    if args.report:
        report_path = args.report.resolve()
        books_path = (PROJECT_ROOT / "content" / "books").resolve()
        try:
            report_path.relative_to(books_path)
        except ValueError:
            pass
        else:
            print("Report path must not be inside content/books.", file=sys.stderr)
            return 1
    try:
        parsed = parse_source_html(SOURCE_PATH.read_text(encoding="utf-8"))
        if args.report:
            report = build_mapping_report(parsed)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_mapping_report(report), encoding="utf-8")
            print(
                f"Wrote proposed mapping report for {report['counts']['books']} books; "
                f"{sum(len(book['unresolved']) for book in report['books'])} unresolved marker entries."
            )
            return 0

        overrides = json.loads(args.overrides.read_text(encoding="utf-8"))
        existing_books = {
            data["book"]["number"]: data
            for path in (PROJECT_ROOT / "content" / "books").glob("book-*.json")
            for data in [json.loads(path.read_text(encoding="utf-8"))]
        }
        books = build_corpus(parsed, overrides, existing_books)
        write_books(books, PROJECT_ROOT / "content" / "books")
    except (OSError, ValueError) as error:
        print(f"Analects import stopped: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {len(books)} sourced books to content/books.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
