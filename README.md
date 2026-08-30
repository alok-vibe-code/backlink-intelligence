# Backlink Intelligence

**Open-source backlink intelligence based on evidence, context, and editorial fit.**

Backlink Intelligence is a local-first, open-source SEO toolkit for evaluating backlink opportunities without reducing link quality to a single authority metric.

The project is designed around a practical workflow:

**Discover → Qualify → Place → Monitor**

It will help SEO professionals inspect page-level evidence, evaluate topical and contextual relevance, identify natural link-placement opportunities, generate transparent Before/After placement recommendations, and monitor acquired links for later changes.

> **Project status:** Foundation / pre-alpha. The repository architecture and methodology are live. Functional backlink auditing begins with `v0.1.0`.

## Why this project exists

Domain-level metrics can be useful inputs, but they do not explain the full context of an individual backlink opportunity. A link also has a source page, a destination, an anchor, a surrounding paragraph, a placement type, link attributes, crawl/indexability signals, and an outbound-link neighborhood.

Backlink Intelligence is being built to surface that evidence directly.

The project does **not** attempt to reproduce Google's ranking systems, label a link as objectively "good" or "bad," or claim that any individual signal determines search performance.

Instead, it aims to answer questions such as:

- Is the source page topically aligned with the destination?
- Does the target page genuinely expand the surrounding discussion?
- Where does the backlink appear on the page?
- Is the anchor natural in context?
- Does the source page show unusual outbound-link patterns that deserve review?
- Where could a target link fit naturally in an existing article?
- How much editorial rewriting would that placement require?
- Did an acquired backlink later disappear or change?

## Core workflow

| Stage | Question | Planned capabilities |
| --- | --- | --- |
| **Discover** | Which pages deserve attention? | Bulk prospect input and future discovery helpers |
| **Qualify** | Is this opportunity worth pursuing? | Relevance, destination fit, source-page evidence, outbound-link analysis, review flags |
| **Place** | Where can the link naturally fit? | Paragraph ranking, anchor analysis, contextual placement, Before/After recommendations |
| **Monitor** | Did the placement remain intact? | Link existence, anchor/attribute changes, redirects, indexability changes, historical snapshots |

## Signature feature: contextual placement recommendations

The planned placement engine accepts:

- a source article URL,
- a target URL, and
- a preferred keyword or anchor.

It will identify the strongest candidate paragraphs and return explainable placement recommendations.

### Before

> The original publisher paragraph is shown without modification.

### After

> The same paragraph is shown with the target resource integrated naturally, while preserving as much of the original copy as possible.

Each recommendation is intended to include:

- paragraph/context match,
- requested anchor,
- suggested anchor when the requested wording is awkward,
- placement strategy,
- editorial intervention level,
- original-text preservation,
- reasoning for the recommendation,
- and warnings when a paragraph should **not** be used.

The goal is not keyword insertion. The goal is **editorially defensible contextual placement**.

## Evidence-first design

Backlink Intelligence prefers transparent dimensions over an unexplained universal score.

Example output direction:

- **Page relevance:** High
- **Context relevance:** Very High
- **Destination fit:** High
- **Placement:** Editorial Context
- **Anchor fit:** Strong
- **Risk signals:** Review
- **Analysis confidence:** High
- **Recommendation:** Prioritize

A recommendation should always be accompanied by the evidence and limitations that produced it.

## Planned analysis areas

### Existing backlink audit

- source and target HTTP status
- redirects and final URLs
- title and H1 extraction
- canonical and robots directives
- backlink presence
- anchor text
- `rel` attributes (`nofollow`, `sponsored`, `ugc`)
- surrounding sentence and paragraph
- approximate placement classification
- main-content evidence

### Topical and contextual relevance

Relevance will be evaluated at multiple levels:

1. broader domain/topic signals,
2. source page ↔ destination page,
3. source paragraph/context ↔ destination page.

The core implementation is intended to remain local-first and explainable, initially using techniques such as term overlap, TF-IDF, cosine similarity, heading/title alignment, and phrase overlap.

### Source-page and outbound-link evidence

- total external links
- unique external domains
- external-link density
- follow/nofollow distribution
- repeated commercial patterns
- outbound-link neighborhood
- thin-content indicators
- indexability evidence

These are review signals, not a proprietary "toxicity score."

### Prospect qualification

Bulk CSV analysis is planned to help prioritize outreach targets using evidence such as:

- relevance,
- destination fit,
- editorial fit,
- outbound-link behavior,
- review flags,
- and confidence.

### Link monitoring

Planned monitoring will detect changes including:

- backlink removal,
- anchor changes,
- follow → nofollow changes,
- `sponsored`/`ugc` attribute changes,
- target changes,
- source/target redirects,
- 404/410 responses,
- noindex changes,
- canonical changes,
- and material placement changes.

## Roadmap

| Release | Milestone | Status |
| --- | --- | --- |
| `v0.1.0` | Backlink evidence auditor | Planned |
| `v0.2.0` | Context and placement classification | Planned |
| `v0.3.0` | Relevance engine | Planned |
| `v0.4.0` | Source quality and outbound-link evidence | Planned |
| `v0.5.0` | Bulk prospect qualification | Planned |
| `v0.6.0` | Contextual placement recommender | Planned |
| `v0.7.0` | Before/After placement recommendations | Planned |
| `v0.8.0` | Backlink monitoring | Planned |
| `v0.9.0` | Portfolio analysis and historical snapshots | Planned |
| `v1.0.0` | Stable integrated toolkit | Planned |

See the detailed [project roadmap](docs/roadmap.md).

## Planned interfaces

The analysis engine is intended to support several interfaces without duplicating the underlying logic:

- **CLI** for technical SEOs and developers
- **CSV / JSON / HTML reports** for SEO workflows
- **Python package** for integrations
- **Local browser UI** for non-technical users
- **Public web interface** as a later phase after the core engine is stable

A third-party user should never need to edit source code just to perform an analysis.

## Installation

The foundation package is already installable for development, but backlink-analysis commands are not yet implemented.

```bash
python -m pip install -e .
backlink-intelligence --version
backlink-intelligence status
```

## Current CLI

```bash
backlink-intelligence --help
backlink-intelligence --version
backlink-intelligence status
```

The `audit`, `qualify`, `place`, and `monitor` commands will be introduced incrementally according to the roadmap.

## Documentation

- [Methodology](docs/methodology.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Signal definitions](docs/signal-definitions.md)
- [Limitations](docs/limitations.md)
- [Ethical crawling](docs/ethical-crawling.md)

## Methodology background

The project builds on the evidence-based backlink evaluation ideas discussed in:

**[Backlink Quality Beyond DA & DR](https://alokblog.com/backlink-quality-beyond-da-dr/)**

The article explains the conceptual motivation. This repository is intended to turn that methodology into transparent, testable software.

## Local-first and API-optional

The core project is intended to work without requiring paid SEO or AI APIs.

Optional integrations may be added later for users who already have access to services such as SEO data providers or language-model APIs, but they should enrich rather than gate the core workflow.

## Security and crawl safety

Because the project accepts arbitrary URLs, URL safety is a first-class engineering requirement. Future network-enabled releases will include protections for private-network targets, redirect validation, response-size limits, timeouts, rate limiting, and other controls.

See [SECURITY.md](SECURITY.md) and [Ethical Crawling](docs/ethical-crawling.md).

## Contributing

Contributions, test cases, documentation improvements, and evidence-based methodology discussions are welcome.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

Released under the [MIT License](LICENSE).

## Disclaimer

Backlink Intelligence is an independent open-source SEO research and workflow tool. It is not affiliated with Google, Ahrefs, Semrush, Moz, Majestic, or any other search engine or SEO platform. Outputs should be treated as evidence for professional review, not as guarantees of ranking impact, penalties, or search-engine behavior.
