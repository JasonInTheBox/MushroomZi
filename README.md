# Mushroom Zi 蘑菇子

A bilingual reader for the *Analects*. See [`docs/product-specification.md`](docs/product-specification.md) for what it is and [`docs/architecture-decisions.md`](docs/architecture-decisions.md) for how it is built.

| Path | Contents |
|---|---|
| `content/` | The corpus: one JSON file per book, plus JSON Schemas |
| `Analects of Confucius 論語.html` | User-supplied source snapshot for provenance; not loaded by the site build |
| `scripts/` | Python corpus validator, reviewed HTML importer, and tests |
| `web/` | Next.js static site that renders the corpus |

## Setup

Requires Python 3.12+ and Node.js 20.9+.

```sh
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
cd web && npm install
```

Keep the virtual environment active when building: `npm run build` calls `python` to validate the corpus first.
The reader uses system font stacks, so the production build does not need to fetch fonts from the network.

## Commands

| Run from | Command | Does |
|---|---|---|
| root | `python scripts/validate_corpus.py` | Check every book file against the schema and ID/placeholder rules |
| root | `python -m unittest discover -s scripts` | Run validator and importer tests |
| root | `python scripts/import_analects_html.py --report docs/superpowers/reviews/2026-11-25-analects-source-mapping-review.md` | Rebuild the source-order mapping report without changing corpus files |
| root | `python scripts/import_analects_html.py --write --overrides content/source-import-overrides.json` | Re-import the approved source mappings into the corpus |
| `web/` | `npm run dev` | Local site at http://localhost:3000, including translations whose rights are unverified |
| `web/` | `npm run build` | Validate, then export the static site to `web/out/` (only rights-cleared translations) |
| `web/` | `npm run lint` | ESLint |
| `web/` | `npm test` | Test UTC daily-passage selection |

CI runs the tests, lint, and build on every push and pull request (`.github/workflows/ci.yml`).

The tracked HTML snapshot currently produces 489 Classical Chinese passage records, 488 English translation blocks, 34 Muller comments, and 59 linked footnotes. One original passage has no translation in the source and is kept without an English entry; its English catalog link is omitted. The mapping report records the 54 reviewed numbering adjustments.
