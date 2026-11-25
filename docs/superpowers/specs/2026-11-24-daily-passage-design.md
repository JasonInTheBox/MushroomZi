# Daily Passage Design

The homepage presents one passage per UTC calendar day, cycling in the corpus's existing book-and-passage order. Selection is deterministic from the UTC epoch day and requires a published English translation plus generated explanation and modern application in English and Traditional Chinese. The browser refreshes the selection at the next UTC midnight; no API, database, or model call is involved.

The card shows the Classical Chinese text, attributed English translation, and both language versions of each commentary section. Every generated section is labeled as AI-generated commentary and stored as `project_explanation` or `modern_application`, never as scholarship. The card links to both reader locales. If there are no eligible passages, it explains that no daily passage is available yet.
