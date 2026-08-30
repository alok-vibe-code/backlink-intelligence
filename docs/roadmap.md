# Development Roadmap

The project is intentionally incremental. Each milestone should be useful, tested, and documented before broader functionality is added.

## Foundation: `v0.0.1`

**Status: Current foundation**

- repository structure
- methodology
- architecture
- security guidance
- crawl-safety principles
- contribution guidance
- minimal installable CLI
- CI for deterministic foundation tests

## `v0.1.0` — Backlink Evidence Auditor

Input:

- source URL
- target URL

Planned output:

- source HTTP status and final URL
- title and H1
- canonical and robots directives
- backlink found/not found
- anchor text
- link attributes
- surrounding sentence
- surrounding paragraph
- basic placement classification
- terminal and JSON output

Engineering priorities:

- URL validation
- SSRF-aware network boundaries
- bounded redirects/timeouts/response size
- deterministic HTML fixtures
- clean evidence models

## `v0.2.0` — Context and Placement Classification

- main-content detection
- editorial context
- resource list
- author bio
- navigation
- sidebar
- footer
- comments/UGC
- sponsored areas
- unknown with confidence

## `v0.3.0` — Relevance Engine

- title/H1/heading alignment
- important-term overlap
- TF-IDF
- cosine similarity
- page ↔ target relevance
- context ↔ target relevance
- explainable relevance evidence

## `v0.4.0` — Source Quality and Outbound-Link Evidence

- external-link counts
- unique external domains
- link density
- follow/nofollow distribution
- outbound neighborhood
- thin-content indicators
- indexability evidence
- review flags

## `v0.5.0` — Bulk Prospect Qualification

- CSV input
- controlled crawl queue
- prospect prioritization
- destination fit
- evidence summaries
- manual-review reasons
- CSV and JSON reports

## `v0.6.0` — Contextual Placement Recommender

Input:

- source article
- target page
- preferred anchor

Capabilities:

- paragraph ranking
- top placement opportunities
- anchor fit
- reject unsuitable paragraphs
- explain why each candidate was selected

## `v0.7.0` — Before/After Placement Recommendations

- minimal insertion strategy
- contextual sentence strategy
- paragraph refinement strategy
- requested vs suggested anchor
- Before paragraph
- After paragraph
- editorial intervention level
- original-text preservation
- placement brief export

This milestone is the minimum target before beginning the public website integration in parallel.

## `v0.8.0` — Backlink Monitoring

- baseline snapshots
- backlink removal
- anchor changes
- follow/nofollow changes
- sponsored/UGC changes
- destination changes
- redirects
- 404/410
- noindex/canonical changes
- historical change records

## `v0.9.0` — Portfolio and History

- anchor-category distribution
- destination distribution
- placement distribution
- retention metrics
- historical comparisons
- manual-review queues

## `v1.0.0` — Stable Toolkit

Target qualities:

- stable CLI
- documented Python API
- CSV/JSON/HTML reporting
- clean install path
- comprehensive deterministic tests
- production-quality URL safety
- Docker packaging if useful
- complete methodology and limitations

## Phase 2 — Public Website

Once audit, relevance, placement, and Before/After recommendations are stable, build a public-facing version at a path such as:

`https://alokblog.com/tools/backlink-intelligence/`

Initial public scope should favor:

- single backlink audit
- single placement analysis
- top placement recommendations
- Before/After output

Bulk analysis and continuous monitoring should remain local-first initially to control cost and abuse.
