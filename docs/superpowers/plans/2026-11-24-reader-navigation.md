# Reader Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Let readers browse the corpus by book and move between neighboring passages while staying in English or Chinese.

**Architecture:** Keep the reader static. Order passages by book and passage number in the existing content helper, group them for the home-page table of contents, and render locale-preserving neighbor links in each passage route.

**Tech Stack:** Next.js 16, React 19, TypeScript, existing `next/link` and corpus JSON.

**Spec:** `docs/superpowers/specs/2026-11-24-reader-navigation-design.md`

## Global Constraints

- Do not add dependencies or client-side state.
- Keep the existing `/en` and `/zh` static route shape and the production translation rights filter.
- Keep product requirements in `docs/product-specification.md` and milestone/architecture notes in `docs/architecture-decisions.md`.

## Review Focus

- The first passage has no previous link; the last passage has no next link.
- Links across book boundaries follow numeric book and passage order.
- Neighbor links retain the current locale.
- Both home-page language links target the correct passage.
- The production rights filter still omits unverified translations.

---

### Task 1: Add static book and passage navigation

**Files:**
- Modify: `web/src/lib/content.ts`
- Modify: `web/src/app/(home)/page.tsx`
- Modify: `web/src/app/[lang]/passage/[id]/page.tsx`
- Modify: `docs/product-specification.md`
- Modify: `docs/architecture-decisions.md`

**Interfaces:**
- `getAllPassages(): ReaderPassage[]` remains the shared source for the catalog and static passage routes.
- Use the existing `lang` and `passage.id` route values to build internal links with `next/link`.

- [x] Order returned passages by `book.number`, then `passage.number`, so adjacency is explicit.
- [x] Group the home-page links by book title and keep English and Chinese links for each passage.
- [x] Add previous/next links to passage pages. Omit the unavailable link at either end and preserve the current language in every href.
- [x] Update product status and roadmap notes to record navigation as implemented and the daily selector as pending content rights, commentary, and date-boundary decisions.
- [x] Run lint, the production build, and generated-HTML checks with the project virtual environment activated. In this managed worktree, use `npm run build -- --webpack` because the shared `node_modules` junction is outside Turbopack’s filesystem root.
