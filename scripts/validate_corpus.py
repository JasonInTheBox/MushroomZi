import json
import re
import sys
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

data_path = Path("content/books/book-01.json")
data = json.loads(data_path.read_text(encoding="utf-8"))

schema_path = Path("content/schema/book.schema.json")
passage_schema_path = schema_path.with_name("passage.schema.json")

book_schema = json.loads(schema_path.read_text(encoding="utf-8"))
passage_schema = json.loads(passage_schema_path.read_text(encoding="utf-8"))

book_schema["$id"] = schema_path.resolve().as_uri()
passage_schema_uri = passage_schema_path.resolve().as_uri()

registry = Registry().with_resource(
    passage_schema_uri,
    Resource.from_contents(passage_schema),
)

Draft202012Validator.check_schema(book_schema)

validator = Draft202012Validator(
    book_schema,
    registry=registry,
    format_checker=Draft202012Validator.FORMAT_CHECKER,
)

schema_errors = list(validator.iter_errors(data))

if schema_errors:
    print("Schema validation failed:")
    for error in schema_errors:
        location = ".".join(str(part) for part in error.absolute_path)
        print(f"- {location or '(document)'}: {error.message}")
    sys.exit(1)

print("JSON Schema checks passed.")

book_number = data["book"]["number"]
seen_ids = set()
errors = []

for passage in data["passages"]:
    passage_id = passage["id"]

    if passage_id in seen_ids:
        errors.append(f"Duplicate passage ID: {passage_id}")
    seen_ids.add(passage_id)

    match = re.fullmatch(r"analects\.(\d{2})\.(\d{2})", passage_id)
    if match is None:
        errors.append(f"{passage_id}: expected an ID like analects.01.01")
        continue

    id_book_number = int(match.group(1))
    id_passage_number = int(match.group(2))

    if id_book_number != book_number:
        errors.append( f"{passage_id}: its book number does not match "
            f"book.number ({book_number})")

    if id_passage_number != passage["number"]:
        errors.append(f"{passage_id}: its passage number does not match "
            f"passage.number ({passage['number']})")

if errors:
    print("Validation failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print ("Passage ID checks passed.")
