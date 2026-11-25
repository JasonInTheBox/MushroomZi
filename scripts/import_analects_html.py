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
ORIGINAL_MARKER = re.compile(r"^\[(\d+-\d+(?:-\d+)?)(?:\s+』)?\]?\s*(.*)$", re.DOTALL)
TRANSLATION_MARKER = re.compile(r"^\[(\d+:\d+(?:-\d+)?)\]\s*(.*)$", re.DOTALL)
UNBRACKETED_TRANSLATION_MARKER = re.compile(r"^(\d+:\d+(?:-\d+)?)\s+(.*)$", re.DOTALL)
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
        self.current_original = None
        self.current_translation = None
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
            self.paragraph = {"parts": [], "noteRefs": [], "bookAnchor": None, "style": attrs.get("style", "")}
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
                if kind == "original":
                    self.current_original = event
                    self.current_translation = None
                elif kind == "translation":
                    self.current_translation = event
                return

        match = UNBRACKETED_TRANSLATION_MARKER.match(text)
        if match:
            event = {
                "kind": "translation",
                "marker": match.group(1),
                "text": clean_text(match.group(2)),
                "noteRefs": list(dict.fromkeys(paragraph["noteRefs"])),
            }
            self.book["events"].append(event)
            self.book["lastEvent"] = event
            self.current_translation = event
            return

        style = paragraph["style"].casefold()
        if "times new roman" in style:
            kind_hint = "translation"
        elif any(font in style for font in ("明朝", "simsun", "batang")) or CJK.search(text):
            kind_hint = "original"
        else:
            kind_hint = None

        last_event = self.book.get("lastEvent")
        target = {
            "original": self.current_original,
            "translation": self.current_translation,
        }.get(kind_hint)
        if target is None and kind_hint is None:
            target = last_event
        if target:
            target["text"] = clean_text(f"{target['text']} {text}")
            target["noteRefs"] = list(dict.fromkeys(target["noteRefs"] + paragraph["noteRefs"]))
            self.book["lastEvent"] = target
            return
        if kind_hint:
            event = {
                "kind": kind_hint,
                "marker": None,
                "text": text,
                "noteRefs": list(dict.fromkeys(paragraph["noteRefs"])),
            }
            self.book["events"].append(event)
            self.book["lastEvent"] = event
            if kind_hint == "original":
                self.current_original = event
                self.current_translation = None
            else:
                self.current_translation = event

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
        self.current_original = None
        self.current_translation = None
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


def _source_marker(event):
    return event.get("marker") or "(unmarked)"


def _marker_number(book_number, marker):
    match = re.fullmatch(rf"{book_number}[-:](\d+)(?:-\d+)?", marker or "")
    return int(match.group(1)) if match else None


def validate_overrides(parsed, overrides):
    if not isinstance(overrides, dict) or set(overrides) != {"schemaVersion", "mappings"}:
        raise ValueError("override file must contain only schemaVersion and mappings")
    if type(overrides["schemaVersion"]) is not int or overrides["schemaVersion"] != 1 or not isinstance(overrides["mappings"], list):
        raise ValueError("override schemaVersion must be 1 and mappings must be a list")

    source_counts = {}
    for book in parsed["books"]:
        for event in book["events"]:
            kind = event.get("kind")
            if kind in ("original", "translation"):
                marker = _source_marker(event)
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


def _assign_book_events(book, override_map=None):
    number = book["number"]
    override_map = override_map or {}
    result, entries, occurrences, unresolved, duplicates = {}, {}, {}, [], {}
    current_passage = None
    next_number = 1

    for order, event in enumerate(book["events"], 1):
        kind = event.get("kind")
        if kind not in ("original", "translation"):
            if kind == "comment" and current_passage in entries:
                entry = entries[current_passage]
                entry["comments"].append(event["text"])
                entry["note_refs"] = list(dict.fromkeys(entry["note_refs"] + event.get("noteRefs", [])))
            continue

        marker = _source_marker(event)
        source_key = (number, kind, marker)
        occurrences[source_key] = occurrences.get(source_key, 0) + 1
        event_key = (*source_key, occurrences[source_key])
        group = duplicates.setdefault((kind, marker), {"occurrences": 0, "texts": set()})
        group["occurrences"] += 1
        group["texts"].add(event["text"])

        if kind == "original":
            passage_number = override_map.get(event_key)
            if passage_number is None:
                labeled_number = _marker_number(number, event.get("marker"))
                passage_number = labeled_number if labeled_number is not None and labeled_number >= next_number else next_number
            if passage_number in entries:
                raise ValueError(f"multiple original source events map to book {number}, passage {passage_number}")
            entries[passage_number] = {
                "original": event,
                "translation": None,
                "comments": [],
                "note_refs": list(event.get("noteRefs", [])),
                "original_marker": event.get("marker"),
                "translation_marker": None,
                "order": order,
            }
            current_passage = passage_number
            next_number = max(next_number, passage_number + 1)
            result[event_key] = passage_number
            continue

        if current_passage is None:
            unresolved.append({"kind": kind, "marker": marker, "text": event["text"], "order": order, "note_refs": event.get("noteRefs", []), "comments": [], "reason": "translation has no preceding original"})
            continue
        passage_number = override_map.get(event_key, current_passage)
        entry = entries.get(passage_number)
        if entry is None:
            unresolved.append({"kind": kind, "marker": marker, "text": event["text"], "order": order, "note_refs": event.get("noteRefs", []), "comments": [], "reason": "translation maps to a passage without an original"})
            continue
        if entry["translation"] is not None:
            unresolved.append({"kind": kind, "marker": marker, "text": event["text"], "order": order, "note_refs": event.get("noteRefs", []), "comments": [], "reason": "multiple translations map to one passage"})
            continue
        entry["translation"] = event
        entry["translation_marker"] = event.get("marker")
        entry["note_refs"] = list(dict.fromkeys(entry["note_refs"] + event.get("noteRefs", [])))
        result[event_key] = passage_number

    for passage_number, entry in entries.items():
        if entry["translation"] is None:
            unresolved.append({
                "kind": "original",
                "marker": entry["original_marker"] or "(unmarked)",
                "text": entry["original"]["text"],
                "order": entry["order"],
                "passage_number": passage_number,
                "reason": "no translation appears before the next original block",
                "note_refs": entry["note_refs"],
                "comments": entry["comments"],
            })
    return result, entries, unresolved, duplicates


def resolve_source_mappings(parsed, overrides):
    """Assign passages in source order and reject translations without originals."""
    override_map = validate_overrides(parsed, overrides)
    result = {}
    for book in parsed["books"]:
        assignments, _, unresolved, _ = _assign_book_events(book, override_map)
        unassigned = [item for item in unresolved if item["kind"] == "translation"]
        if unassigned:
            issue = unassigned[0]
            raise ValueError(f"unresolved source mappings in book {book['number']}: {issue['reason']} ({issue['marker']})")
        result.update(assignments)
    return result


def _citation(book_number, passage_number, marker, locator=None):
    marker_number = _marker_number(book_number, marker)
    if marker and re.fullmatch(rf"{book_number}[-:]\d+", marker) and marker_number == passage_number:
        citation = f"Book {book_number}, passage {passage_number}"
    elif not marker:
        citation = f"Book {book_number}, source order (mapped to passage {passage_number})"
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
                key = (number, kind, _source_marker(event))
                occurrences[key] = occurrences.get(key, 0) + 1
                passage_number = mappings[(number, kind, _source_marker(event), occurrences[key])]
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
            if entry["original"] is None:
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

            translations = [
                deepcopy(item) for item in old.get("translations", [])
                if not (item.get("id") == f"{passage_id}.en.muller" or (
                    item.get("translator") == "A. Charles Muller" and item.get("source", {}).get("url") == SOURCE_URL
                ))
            ]
            if entry["translation"] is not None:
                translation_marker = entry["translation_marker"]
                translation = {
                    "id": f"{passage_id}.en.muller",
                    "language": "en",
                    "text": entry["translation"]["text"],
                    "translator": "A. Charles Muller",
                    "source": _source_record(_citation(number, passage_number, translation_marker)),
                    "rights": deepcopy(MULLER_RIGHTS),
                }
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
    """Propose passage IDs by source order and retain every source occurrence."""
    books, overrides = [], []
    totals = {
        "original_passages": 0,
        "translation_blocks": 0,
        "printed_original_markers": 0,
        "printed_translation_markers": 0,
        "comments": 0,
    }
    linked_note_ids, referenced_notes = set(), set()

    for book in parsed["books"]:
        number = book["number"]
        assignments, entries, unresolved, duplicate_groups = _assign_book_events(book)
        occurrences = {}
        pairings = []
        for passage_number, entry in sorted(entries.items()):
            original, translation = entry["original"], entry["translation"]
            refs = entry["note_refs"]
            notes = [{"id": note_id, "text": parsed["notes"].get(note_id, "")} for note_id in refs]
            warnings = []
            original_marker = entry["original_marker"]
            original_label_number = _marker_number(number, original_marker)
            if original_label_number is None:
                warnings.append(f"unmarked original assigned to passage {passage_number}")
            elif original_label_number != passage_number:
                warnings.append(f"original label {original_marker} mapped to passage {passage_number}")
            translation_marker = entry["translation_marker"]
            if translation_marker:
                translation_label_number = _marker_number(number, translation_marker)
                if translation_label_number is None:
                    warnings.append(f"translation label {translation_marker} mapped to passage {passage_number}")
                elif translation_label_number != passage_number:
                    warnings.append(f"translation label {translation_marker} mapped to passage {passage_number}")
            pairings.append({
                "passage_id": f"analects.{number:02}.{passage_number:02}",
                "passage_number": passage_number,
                "original_marker": original_marker or "(unmarked)",
                "translation_marker": translation_marker or "—",
                "original": original["text"],
                "translation": translation["text"] if translation else None,
                "comments": entry["comments"],
                "notes": notes,
                "warnings": warnings,
            })
            linked_note_ids.update(refs)
            referenced_notes.update(refs)

        for item in unresolved:
            refs = item.get("note_refs", [])
            item["excerpt"] = _excerpt(item["text"])
            item["notes"] = [{"id": note_id, "text": parsed["notes"].get(note_id, "")} for note_id in refs]
            item["passage_id"] = (
                f"analects.{number:02}.{item['passage_number']:02}"
                if item.get("passage_number") is not None else None
            )
            linked_note_ids.update(refs)
            referenced_notes.update(refs)

        for event in book["events"]:
            kind = event.get("kind")
            if kind == "comment":
                totals["comments"] += 1
            elif kind in ("original", "translation"):
                totals["original_passages" if kind == "original" else "translation_blocks"] += 1
                if event.get("marker"):
                    totals["printed_original_markers" if kind == "original" else "printed_translation_markers"] += 1
                refs = event.get("noteRefs", [])
                linked_note_ids.update(refs)
                referenced_notes.update(refs)
                marker = _source_marker(event)
                key = (number, kind, marker)
                occurrences[key] = occurrences.get(key, 0) + 1
                passage_number = assignments.get((*key, occurrences[key]))
                label_number = _marker_number(number, event.get("marker"))
                if passage_number is not None and (label_number is None or label_number != passage_number):
                    overrides.append({
                        "bookNumber": number,
                        "sourceKind": kind,
                        "sourceMarker": marker,
                        "occurrence": occurrences[key],
                        "passageNumber": passage_number,
                    })

        duplicates = [
            {
                "kind": kind,
                "marker": marker,
                "occurrences": group["occurrences"],
                "distinct_texts": len(group["texts"]),
                "excerpts": [_excerpt(text) for text in sorted(group["texts"])],
            }
            for (kind, marker), group in duplicate_groups.items()
            if group["occurrences"] > 1
        ]
        books.append({
            "number": number,
            "title": book["title"],
            "counts": {
                "original_passages": sum(event["kind"] == "original" for event in book["events"]),
                "translation_blocks": sum(event["kind"] == "translation" for event in book["events"]),
                "comments": sum(event["kind"] == "comment" for event in book["events"]),
            },
            "pairings": pairings,
            "unresolved": unresolved,
            "duplicates": duplicates,
        })

    note_ids = set(parsed["notes"])
    return {
        "counts": {
            "books": len(books),
            **totals,
            "linked_note_ids": len(linked_note_ids),
            "linked_notes_with_bodies": len(linked_note_ids & note_ids),
            "missing_note_bodies": sorted(linked_note_ids - note_ids),
            "unlinked_note_bodies": sorted(note_ids - referenced_notes),
            "unresolved_entries": sum(len(book["unresolved"]) for book in books),
            "numbering_adjustments": len(overrides),
        },
        "books": books,
        "overrides": overrides,
    }


def render_mapping_report(report):
    counts = report["counts"]
    lines = [
        "# Analects source mapping review",
        "",
        "**Status: approved source-order proposal; applied to the corpus.** Each original block starts a passage; the following translation block maps to it until the next original. Duplicate labels receive distinct passage numbers. Original blocks without translations remain source-only.",
        "",
        "Source: [A. Charles Muller, The Analects](http://www.acmuller.net/con-dao/analects.html), from the tracked HTML snapshot.",
        "",
        "## Import summary",
        "",
        f"- Books: {counts['books']}",
        f"- Classical Chinese passages: {counts['original_passages']} ({counts['printed_original_markers']} printed labels)",
        f"- English translation blocks: {counts['translation_blocks']} ({counts['printed_translation_markers']} printed labels)",
        f"- Inline comments: {counts['comments']}",
        f"- Distinct linked footnote IDs: {counts['linked_note_ids']} ({counts['linked_notes_with_bodies']} with note text)",
        f"- Unlinked footnote bodies: {len(counts['unlinked_note_bodies'])}",
        f"- Source-only or unpaired entries: {counts['unresolved_entries']}",
        f"- Numbering adjustments recorded: {counts['numbering_adjustments']}",
        "",
    ]

    def cell(value):
        return clean_text(str(value)).replace("|", "\\|")

    for book in report["books"]:
        lines.extend([
            f"## Book {book['number']}: {book['title']['chinese']} ({book['title']['pinyin']})",
            "",
            f"Counts: {book['counts']['original_passages']} Chinese, {book['counts']['translation_blocks']} English, {book['counts']['comments']} comments.",
            "",
        ])
        if book["pairings"]:
            lines.extend([
                "### Proposed source-order mapping",
                "",
                "| Corpus ID | Printed labels | Classical Chinese excerpt | English excerpt | Mapping notes / Muller comments / footnotes |",
                "|---|---|---|---|---|",
            ])
            for item in book["pairings"]:
                annotations = list(item["warnings"])
                annotations.extend(f"Comment: {_excerpt(text, 70)}" for text in item["comments"])
                annotations.extend(f"{note['id']}: {_excerpt(note['text'], 70)}" for note in item["notes"])
                lines.append(
                    f"| {cell(item['passage_id'])} | {cell(item['original_marker'])} / {cell(item['translation_marker'])} | {cell(_excerpt(item['original'], 85))} | {cell(_excerpt(item['translation'] or '—', 85))} | {cell('; '.join(annotations) or '—')} |"
                )
            lines.append("")
        if book["unresolved"]:
            lines.extend([
                "### Source-only or unpaired entries",
                "",
                "| Kind | Source label | Reason | Excerpt | Muller footnotes |",
                "|---|---|---|---|---|",
            ])
            for item in book["unresolved"]:
                annotations = [f"{note['id']}: {_excerpt(note['text'], 70)}" for note in item["notes"]]
                lines.append(
                    f"| {cell(item['kind'])} | {cell(item['marker'])} | {cell(item['reason'])} | {cell(item['excerpt'])} | {cell('; '.join(annotations) or '—')} |"
                )
            lines.append("")
        if book["duplicates"]:
            lines.extend([
                "### Repeated source labels",
                "",
                "Each occurrence remains a separate passage in source order, including repeated identical text.",
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
                f"{report['counts']['unresolved_entries']} source-only or unpaired entries."
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
