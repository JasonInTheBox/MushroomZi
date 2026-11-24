import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = PROJECT_ROOT / "content" / "books"
BOOK_SCHEMA_PATH = PROJECT_ROOT / "content" / "schema" / "book.schema.json"
PASSAGE_SCHEMA_PATH = BOOK_SCHEMA_PATH.with_name("passage.schema.json")

BOOK_ID_PATTERN = re.compile(r"analects\.book\.(\d{2})")
PASSAGE_ID_PATTERN = re.compile(r"analects\.(\d{2})\.(\d{2})")
BOOK_FILENAME_PATTERN = re.compile(r"book-(\d{2})")
PLACEHOLDER_PATTERN = re.compile(r"^(?:\.{3}|…|todo\b|\[todo\b|placeholder\b)", re.IGNORECASE,)

def load_json(path: Path):
    """Read a JSON file and return its decoded contents."""
    return json.loads(path.read_text(encoding="utf-8"))

def build_book_validator():
    """Build the validator and connect the local passage schema."""
    book_schema = load_json(BOOK_SCHEMA_PATH)
    passage_schema = load_json(PASSAGE_SCHEMA_PATH)

    # Give the relative $ref in book.schema.json a base location.
    book_schema["$id"] = BOOK_SCHEMA_PATH.as_uri()
    passage_schema_uri = PASSAGE_SCHEMA_PATH.as_uri()

    registry = Registry().with_resource(
        passage_schema_uri,
        Resource.from_contents(passage_schema),
    )

    Draft202012Validator.check_schema(book_schema)
    Draft202012Validator.check_schema(passage_schema)

    return Draft202012Validator(
        book_schema,
        registry=registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

def semantic_errors(book_data, path, seen_passage_ids):
    """Check relationships between IDs, numbers, and filenames."""
    errors = []
    book_number = book_data["book"]["number"]
    book_id = book_data["book"]["id"]

    book_id_match = BOOK_ID_PATTERN.fullmatch(book_id)
    if book_id_match and int(book_id_match.group(1)) != book_number:
        errors.append(
            f"{path.name}: book.id {book_id!r} does not match "
            f"book.number {book_number}"
        )

    filename_match = BOOK_FILENAME_PATTERN.fullmatch(path.stem)
    if filename_match is None:
        errors.append(
            f"{path.name}: filename must use the format book-01.json"
        )
    elif int(filename_match.group(1)) != book_number:
        errors.append(
            f"{path.name}: filename number does not match "
            f"book.number {book_number}"
        )

    for passage in book_data["passages"]:
        passage_id = passage["id"]
        original_text = passage["original"]["text"].strip()
        
        if PLACEHOLDER_PATTERN.match(original_text):
            errors.append(
                f"{path.name}: {passage_id} original text is still a placeholder"
            )

        for translation in passage["translations"]:
            expected_prefix = f"{passage_id}.{translation['language']}."
            if not translation["id"].startswith(expected_prefix):
                errors.append(
                    f"{path.name}: translation ID {translation['id']!r} "
                    f"must begin with {expected_prefix!r}"
                )

            translation_text = translation["text"].strip()
            if PLACEHOLDER_PATTERN.match(translation_text):
                errors.append(
                    f"{path.name}: translation {translation['id']!r} "
                    "is still a placeholder"
                )

        for item in passage["commentary"]:
            for field in ("text", "context"):
                value = item.get(field, "").strip()
                if PLACEHOLDER_PATTERN.match(value):
                    errors.append(
                        f"{path.name}: commentary {item['id']!r} "
                        f"{field} is still a placeholder"
                    )

        previous_path = seen_passage_ids.get(passage_id)
        if previous_path is not None:
            errors.append(
                f"{path.name}: duplicate passage ID {passage_id!r}; "
                f"also found in {previous_path.name}"
            )
        else:
            seen_passage_ids[passage_id] = path

        passage_id_match = PASSAGE_ID_PATTERN.fullmatch(passage_id)
        if passage_id_match is None:
            errors.append(
                f"{path.name}: passage ID {passage_id!r} must look like "
                "analects.01.01"
            )
            continue

        id_book_number = int(passage_id_match.group(1))
        id_passage_number = int(passage_id_match.group(2))

        if id_book_number != book_number:
            errors.append(
                f"{path.name}: {passage_id!r} has book number "
                f"{id_book_number}, but book.number is {book_number}"
            )

        if id_passage_number != passage["number"]:
            errors.append(
                f"{path.name}: {passage_id!r} has passage number "
                f"{id_passage_number}, but passage.number is "
                f"{passage['number']}"
            )

    return errors

def main():
    book_files = sorted(BOOKS_DIR.glob("book-*.json"))
    if not book_files:
        print(f"No book JSON files found in {BOOKS_DIR}", file=sys.stderr)
        return 1

    validator = build_book_validator()
    all_errors = []
    seen_passage_ids = {}
    validated_files = 0

    for path in book_files:
        try:
            book_data = load_json(path)
        except json.JSONDecodeError as error:
            all_errors.append(
                f"{path.name}: invalid JSON at line {error.lineno}, "
                f"column {error.colno}: {error.msg}"
            )
            continue
        except OSError as error:
            all_errors.append(f"{path.name}: could not read file: {error}")
            continue

        schema_errors = list(validator.iter_errors(book_data))
        if schema_errors:
            for error in schema_errors:
                location = ".".join(str(part) for part in error.absolute_path)
                all_errors.append(
                    f"{path.name}: {location or '(document)'}: "
                    f"{error.message}"
                )
            # Skip semantic checks if required fields are missing or invalid.
            continue

        validated_files += 1
        all_errors.extend(
            semantic_errors(book_data, path, seen_passage_ids)
        )

    if all_errors:
        print(f"Corpus validation failed with {len(all_errors)} issue(s):")
        for error in all_errors:
            print(f"- {error}")
        return 1

    print(f"Validated {validated_files} book file(s): all checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
