# Changelog

All notable changes to Backlink Intelligence are documented here.

## 1.0.0 - 2026-08-30

### Added

- Existing backlink evidence auditing.
- Safe bounded HTTP/HTTPS fetcher with private-network protections.
- HTML metadata, paragraph, heading, and link extraction.
- Contextual placement classification for main/editorial content, navigation, sidebar, footer, and unknown locations.
- Deterministic page and context relevance analysis.
- Outbound-link density and external-domain evidence.
- Bulk prospect qualification from CSV.
- Contextual link placement ranking.
- Before/After placement recommendations with editorial-preservation indicators.
- Backlink monitoring with persisted JSON baselines and change detection.
- Backlink portfolio analysis for anchors, destinations, and placements.
- Human-readable and JSON audit reporting.
- CLI commands: `audit`, `qualify`, `place`, `monitor`, `portfolio`, and `status`.
- Offline unit-test suite and GitHub Actions CI.

### Design principles

- No paid SEO API required.
- No paid AI/model API required.
- Evidence-first output instead of an unexplained universal backlink score.
- Human review required for placement drafts and workflow recommendations.

## 0.0.1 - 2026-08-30

- Initial repository foundation, methodology, roadmap, contribution guidance, and CLI scaffold.
