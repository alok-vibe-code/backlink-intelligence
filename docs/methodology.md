# Methodology

Backlink Intelligence follows an evidence-first methodology. It does not infer a proprietary search-engine score.

## 1. Source accessibility and indexability

The tool records response status, final URL, canonical URL, and robots directives. These are observable technical signals.

## 2. Link evidence

For an existing backlink it records:

- whether the target URL is present,
- anchor text,
- `rel` attributes,
- surrounding paragraph/context,
- broad placement classification.

## 3. Relevance

The deterministic v1 engine compares source and destination using term-frequency cosine similarity plus normalized term overlap. It reports separate page, title/H1, heading, and contextual similarities.

These similarity values are workflow evidence, not ranking probabilities.

## 4. Outbound-link behavior

The tool measures external links, unique external domains, link density, and rel-attribute distributions. High-density patterns are review flags, not a "toxic link" verdict.

## 5. Prospect qualification

The qualifier combines availability, indexability, relevance, placement potential, and review flags into one of three operational recommendations:

- prioritize
- manual review
- low priority

The recommendation is intentionally explainable and reversible by a human reviewer.

## 6. Contextual placement

Paragraphs are ranked using target-page similarity, destination-specific intent, and a smaller anchor-term overlap component. Destination intent emphasizes terms that distinguish the target from the requested anchor, helping a cost/pricing paragraph outrank a generic paragraph that only mentions the entity. Very short and extremely long paragraphs are excluded from candidate generation.

Before/After output prioritizes preservation of publisher text. Anchor matching requires complete word boundaries, preserves the capitalization already present in publisher copy, and may conservatively use an existing singular/plural grammatical form rather than creating partial-link artifacts. If no natural source phrase is available, a conservative contextual sentence is appended.

## 7. Monitoring

A monitoring baseline captures the observable state of a link. Future checks compare link existence, anchor, rel attributes, placement, source/target status, canonical, and robots directives.

## Human review

All outputs are aids for SEO and editorial review. The tool does not automatically alter external pages, send outreach, purchase links, or publish placements.
