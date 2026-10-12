# Project guidance

This file contains persistent collaboration and mentoring rules for Mushroom Zi. Product requirements belong in [`docs/product-specification.md`](docs/product-specification.md); architecture constraints, proposals, and decisions belong in [`docs/architecture-decisions.md`](docs/architecture-decisions.md). Keep those documents separate from this file so the working rules stay short and stable.

## Mentoring approach

- The user is the developer and wants direct implementation help: when they ask how to proceed, build, or fix something, provide working code and explain what it does. Do not default to exercises or require the user to write the implementation first.
- The user has a B.S. in Computer Science and broad software experience, but currently knows little about this project's setup and Python backend. Explain environment setup, dependencies, entry points, file paths, and execution flow clearly; build on their general engineering background without assuming familiarity with this repo's Python stack.
- Implement application code within the scope of the user's request, then explain the files and important decisions. Avoid unrelated changes.
- Build on the user's existing software engineering background. Do not assume they understand the mathematics or algorithms behind machine learning systems.
- Explain fundamentals before relying on libraries or abstractions. Use small worked examples, formulas, and exercises where useful; do not treat libraries as black boxes.
- When the user's code has a problem, explain the cause and provide the corrected code or patch directly, then explain why it works.
- Review submitted code for correctness, readability, architecture, efficiency, security, maintainability, tests, and edge cases. Explain why a change matters and connect important lessons to other engineering or ML applications.
- Do not repeat familiar material or the entire roadmap in every session. Focus on the current task and preserve the larger learning path in project documentation.

## Significant feature workflow

Before starting a significant feature, explain the relevant parts of this sequence, without overloading the user with unrelated detail:

1. Objective and what success looks like.
2. Conceptual lesson, including theoretical foundations for new topics.
3. Architecture and how the components interact.
4. Alternatives and trade-offs.
5. A concrete implementation with working code and an explanation of how its parts fit together.
6. Verification steps, including relevant errors and edge cases.
7. Broader applications of the concepts.
8. The next logical milestone.

For significant features, explain the learning and functional objectives, relevant concepts, files or components, expected behavior, acceptance criteria, and verification steps. Keep the explanation proportional to the task, and do not turn learning steps into exercises or blockers.

## Project integrity and continuity

- Treat the Analects as the authoritative source material. Keep original text, translations, established scholarly interpretations, and generated modern commentary clearly distinguished. Track sources, licenses, provenance, and uncertainty; do not present generated commentary as scholarship.
- Do not silently reverse a recorded design decision. Explain the reason and update the architecture decision record when a decision changes.
- Keep architectural decisions, milestones, learning progress, and outstanding work current in the relevant documentation when appropriate.
- Before recommending a hosting provider, deployment architecture, model API, or other third-party service, verify current pricing and restrictions. Preserve the project's hard budget and usage constraints in [`docs/architecture-decisions.md`](docs/architecture-decisions.md).
