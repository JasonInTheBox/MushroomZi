# Reader navigation design

## Intent

Help readers browse passages by book and move between passages without leaving their chosen language route.

## Goals and non-goals

- Group the existing home-page passage links under their book titles, with English and Chinese links.
- Add previous/next links to each passage page, ordered by book number and passage number, while preserving `/en` or `/zh`.
- Keep navigation static and accessible through normal links.
- Defer the daily passage, thematic browsing, and new corpus content. Daily content needs a rights-cleared translation, attributed commentary, and a local-date-versus-UTC decision.

## Constraints

Reuse `getAllPassages()` and Next.js `Link`; preserve static generation and the production translation rights filter. Do not add dependencies or client-side state.

## Approaches

1. **Navigation first (recommended):** grouped table of contents plus previous/next links. This completes a useful part of the next roadmap milestone with the existing corpus.
2. **Daily content first:** curate rights-cleared translation and project commentary before building the daily selector. This satisfies more of the eventual daily requirement but delays the independent navigation work.

## Proposed decision

Proceed with navigation first, interpreting the request to continue to the next roadmap step as approval of that direction. For the first and last passages, omit the unavailable previous or next link. Update the product status and roadmap after implementation.
