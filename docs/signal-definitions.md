# Signal definitions

## Relevance levels

Relevance combines deterministic page/context similarity signals and is represented as:

- `low`
- `medium`
- `high`
- `very_high`

Thresholds are intentionally visible in the source code and may evolve with benchmark data.

## Placement values

- `editorial_context`: link detected inside `<main>` or `<article>`.
- `navigation`: link detected inside `<nav>` or `<header>`.
- `sidebar`: link detected inside `<aside>`.
- `footer`: link detected inside `<footer>`.
- `unknown`: HTML structure is insufficient to make a confident landmark classification.

## Review flags

Examples include:

- `high_external_link_density`
- `many_unique_external_domains`
- `many_followed_external_links`
- `source_not_indexable`
- `source_unavailable`
- `target_unavailable`
- `sponsored_attribute_present`
- `weak_context_match_manual_review_required`

A flag means "inspect this evidence," not "Google considers this link spam."

## Confidence

Confidence describes how complete the observable evidence is. It is not confidence in ranking impact.
