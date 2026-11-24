# Project guidance

This file contains persistent collaboration and mentoring rules for Mushroom Zi. Product requirements belong in [`docs/product-specification.md`](docs/product-specification.md); architecture constraints, proposals, and decisions belong in [`docs/architecture-decisions.md`](docs/architecture-decisions.md). Keep those documents separate from this file so the working rules stay short and stable.

## Every prompt

- Before acting, find the available skills relevant to the request and use them.
- After any change, state what each changed file or code change does, in a line or two each.
- Update the project documentation the change affects (see Project integrity and continuity).

## Writing code

- The agent writes all the code. When the user asks how to build or fix something, implement it directly; when their code has a problem, explain the cause, apply the fix, and explain why it works.
- Write the minimum code that fully solves the request: reuse existing helpers and dependencies, keep each meaning in one place, and use the fewest clear lines.
- Add concise comments where the reason behind code is not obvious from the code itself.
- Stay within the scope of the request.

## Mentoring approach

- The user has a B.S. in Computer Science and broad software experience, but currently knows little about this project's setup, its Python backend, or the mathematics behind machine learning. Explain environment setup, dependencies, entry points, file paths, and execution flow clearly, building on their general engineering background.
- Explain fundamentals before relying on libraries or abstractions, using small worked examples and formulas where useful.
- Review submitted code for correctness, readability, architecture, efficiency, security, maintainability, tests, and edge cases. Explain why a change matters and connect important lessons to other engineering or ML applications.
- Focus on the current task; the larger learning path lives in project documentation.

## Significant feature workflow

Before starting a significant feature, explain the relevant parts of this sequence, proportional to the task:

1. Objective and what success looks like.
2. Conceptual lesson, including theoretical foundations for new topics.
3. Architecture and how the components interact.
4. Alternatives and trade-offs.
5. A concrete implementation with working code and an explanation of how its parts fit together.
6. Verification steps, including relevant errors and edge cases.
7. Broader applications of the concepts.
8. The next logical milestone.

## Project integrity and continuity

- Treat the Analects as the authoritative source material. Keep original text, translations, established scholarly interpretations, and generated modern commentary clearly distinguished. Track sources, licenses, provenance, and uncertainty; label generated commentary as generated, never as scholarship.
- When a recorded design decision changes, explain the reason and update the architecture decision record.
- Keep architectural decisions, milestones, learning progress, and outstanding work current in the relevant documentation.
- Before recommending a hosting provider, deployment architecture, model API, or other third-party service, verify current pricing and restrictions. Preserve the project's hard budget and usage constraints in [`docs/architecture-decisions.md`](docs/architecture-decisions.md).
