# Mushroom Zi 蘑菇子

A bilingual reader for the *Analects*. See [`docs/product-specification.md`](docs/product-specification.md) for what it is and [`docs/architecture-decisions.md`](docs/architecture-decisions.md) for how it is built.

| Path | Contents |
|---|---|
| `content/` | The corpus: one JSON file per book, plus JSON Schemas |
| `scripts/` | Python corpus validator and its tests |
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

## Commands

| Run from | Command | Does |
|---|---|---|
| root | `python scripts/validate_corpus.py` | Check every book file against the schema and ID/placeholder rules |
| root | `python -m unittest discover scripts` | Run the validator tests |
| `web/` | `npm run dev` | Local site at http://localhost:3000, including translations whose rights are unverified |
| `web/` | `npm run build` | Validate, then export the static site to `web/out/` (only rights-cleared translations) |
| `web/` | `npm run lint` | ESLint |

CI runs the tests, lint, and build on every push and pull request (`.github/workflows/ci.yml`).
