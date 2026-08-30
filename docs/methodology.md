# Methodology

Backlink Intelligence is designed around one principle:

> **Evaluate observable link evidence and editorial context instead of treating a single third-party authority metric as the final decision.**

## What the project evaluates

The methodology is organized around five evidence groups.

### 1. Source-page evidence

Examples include:

- HTTP availability and redirects
- title, H1, and main content
- canonical and robots directives
- approximate content depth
- external-link counts and unique external domains
- outbound-link density and neighborhood

### 2. Link evidence

Examples include:

- whether the target link exists
- anchor text
- link type and attributes
- surrounding sentence and paragraph
- approximate location within the document
- whether the link appears to be inside editorial main content

### 3. Relevance evidence

Relevance is intended to be measured at several levels rather than as one binary label:

- broader site/domain topic signals
- source page ↔ destination page
- local link context ↔ destination page

Initial implementations should prefer explainable local methods. More advanced semantic models may be added as optional components later.

### 4. Editorial-fit evidence

For proposed link placements, the tool should examine:

- whether the target genuinely expands the source discussion
- whether the preferred anchor is grammatically and semantically natural
- how much original publisher text would need to change
- whether a new sentence is more appropriate than forced insertion
- whether the candidate paragraph should be rejected entirely

### 5. Lifecycle evidence

After a backlink is acquired, monitoring may examine:

- continued link presence
- anchor changes
- `rel` changes
- target changes
- source/target redirects
- HTTP availability
- canonical/noindex changes
- material placement changes

## Recommendation model

The project should expose dimensions such as:

- relevance,
- editorial fit,
- risk/review signals,
- confidence,
- and recommendation.

A future recommendation such as **Prioritize** should always include the reasons that support it and the concerns that might require human review.

## What the methodology does not claim

Backlink Intelligence does not claim to:

- know how Google values a specific backlink,
- reproduce PageRank or search-engine ranking systems,
- determine whether a site is "toxic" from a proprietary formula,
- guarantee rankings,
- guarantee penalties,
- or replace professional review.

## Background article

The conceptual motivation is discussed in:

[Backlink Quality Beyond DA & DR](https://alokblog.com/backlink-quality-beyond-da-dr/)
