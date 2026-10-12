# Mushroom Zi — Product Specification

**Status:** Baseline requirements transcribed from the project brief. This is a living product document; it does not imply that implementation has started.

## Product overview

Mushroom Zi (蘑菇子) is a public, bilingual, interactive web application dedicated to the *Analects* (《论语》). Its name is a playful reference to 君子 (*junzi*), the exemplary person in Confucian thought, combined with a mushroom identity.

The product has two goals:

1. Help people understand the *Analects* and consider how its ideas apply to everyday life.
2. Give the developer a structured, long-term path for learning full-stack engineering, NLP, machine learning, LLM engineering, retrieval, and eventually AI agents through building the project.

## Audiences and principles

- Serve readers exploring Confucian texts, whether or not they have prior knowledge.
- Be a thoughtful learning companion, not an authority that tells people what to believe.
- Explain ideas accessibly while preserving intellectual honesty, attribution, and interpretive nuance.
- Keep reading and daily lessons useful even when AI services are unavailable.

## Content requirements

- The long-term corpus should cover all 20 books of the *Analects*.
- Start with a small, carefully verified collection and expand it over time.
- Use [A. Charles Muller's Analects page](http://www.acmuller.net/con-dao/analects.html) as the initial working reference when researching passages. Record precise source and translation attribution, and verify reuse rights before reproducing its translation in the public corpus.
- A passage may include:
  - Classical Chinese source text.
  - One or more English translations.
  - Clear explanations and modern everyday applications.
  - Relevant philosophical themes and concepts.
  - Multiple interpretations when reliable sources support them.
  - Translation references, source attribution, license information, and provenance.
- Distinguish source text, translations, established scholarly interpretation, and original modern or AI-generated commentary.
- Chinese and English are both supported. Simplified and traditional Chinese forms and pinyin may be added where useful.

## Ways to explore

1. **Traditional navigation:** browse by book and passage.
2. **Thematic exploration:** browse concepts such as learning, friendship, relationships, leadership, virtue, self-cultivation, and responsibility.

## Daily passage

Provide a daily passage with the original text, translation, explanation, and a relatable modern application. The initial selection is deterministic and date-based and requires neither an AI API nor a database.

## Mushroom Zi companion

Mushroom Zi is inspired by a disciple of Confucius. Its voice is curious, humble, reflective, approachable, and intellectually honest. It must not impersonate Confucius.

Planned capabilities:

1. **Ask Mushroom Zi:** answer questions about the text, concepts, passages, and interpretations.
2. **Situational guidance:** find teachings relevant to a personal or everyday situation.
3. **Guided reflection:** help users reason through a situation with relevant passages and reflective questions, rather than issuing absolute moral instructions.
4. **Passage assistance:** explain difficult expressions, historical context, translations, and philosophical concepts.

Responses should cite specific passages, explain why they are relevant, separate quotations from interpretation and modern application, and acknowledge uncertainty or differing interpretations.

## Initial release scope

- A small verified passage collection.
- Bilingual reading and traditional and thematic exploration.
- A deterministic daily passage.
- No accounts or personalized curriculum are required for the initial release.
- AI features are part of the product direction, but core reading and daily content must not depend on them.

## Design and experience

The primary style is modern literary minimalism, with traditional Chinese ink-wash aesthetics as a secondary influence.

- Warm ivory or off-white backgrounds, readable Chinese and English typography, generous whitespace, and editorial layouts.
- Subtle black, charcoal, and muted earthy colors; restrained traditional Chinese motifs.
- Intentional transitions and occasional subtle ink-wash-inspired animation.
- A charming mushroom identity may appear if it complements the literary feel.
- Prioritize accessibility, readable typography, performance, responsiveness, and reduced-motion support.
- Avoid generic AI-startup styling, unnecessary gradients, excessive cards, overly playful UI, and distracting animation.

## Quality and trust

- The *Analects* remains the authoritative source material.
- Source attribution, translation references, licensing, and provenance must be tracked.
- Explanations should be clear and accessible without presenting a single interpretation as settled when reliable sources differ.
- AI output must be grounded in cited material and clearly identified as generated commentary where applicable.
