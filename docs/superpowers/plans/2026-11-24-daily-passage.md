# UTC Daily Passage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show an attributed, bilingual daily Analects passage selected by UTC date, with clearly labeled generated commentary.

**Architecture:** The server filters the existing sorted corpus to passages with publishable English translation and both generated commentary kinds in `en` and `zh-Hant`. It passes only the eligible daily-card fields to a small Client Component, which selects by UTC epoch day and refreshes at midnight. A dependency-free `.mjs` helper holds the date-to-index rule and is covered by Node's built-in test runner.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, Node `node:test`.

**Spec:** `docs/superpowers/specs/2026-11-24-daily-passage-design.md`

## Global Constraints

- Keep the static reader usable without an API, database, or model service.
- Show attribution for the user-authorized English translation.
- Label generated commentary and keep it distinct from scholarship.
- Use UTC as the universal day boundary.

## Review Focus

- UTC midnight changes selection and the visible date together (test adjacent UTC days).
- Dates within the same UTC day select the same passage (test different timestamps).
- Negative epoch days still map to a valid index; an empty pool has no selection (test both).
- Ineligible passages cannot appear in the daily pool (build-time filtering and assertions).
- The first render is hydration-stable and the open page refreshes at midnight (build and lint).

---

### Task 1: UTC selection and corpus commentary

**Files:** Create `web/src/lib/daily-passage.mjs` and `web/src/lib/daily-passage.test.mjs`; modify `web/package.json` and `content/books/book-01.json`.

**Interfaces:** Consumes the existing passage JSON schema and Node's built-in test runner. Produces `getDailyPassageIndex(timestamp, passageCount) -> number` (`-1` for an empty pool) and eligible bilingual generated commentary records.

- [x] Test same-day stability, UTC midnight rollover, cycling, pre-epoch dates, and empty pools with `node:test`.
- [x] Run the focused test and confirm it fails because the helper is missing.
- [x] Implement the minimal UTC epoch-day index and add bilingual generated explanation/application records to eligible seed passages.
- [x] Run the test and corpus validator.

### Task 2: Homepage card and project record

**Files:** Create `web/src/components/daily-passage.tsx`; modify `web/src/app/(home)/page.tsx`, `docs/product-specification.md`, and `docs/architecture-decisions.md`.

**Interfaces:** Consumes sorted `ReaderPassage[]`, the UTC index helper, and the commentary records from Task 1. Produces a static-export-safe homepage card that refreshes from the browser's UTC clock.

- [x] Add the client card with eligible, minimal serializable data, attribution, bilingual generated labels, and UTC-midnight refresh.
- [x] Update the project status and record UTC selection and generated-commentary provenance.
- [x] Run unit tests, lint, build, and diff checks.
