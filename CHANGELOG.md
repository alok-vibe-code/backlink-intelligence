# Changelog

## 1.1.4 - 2026-09-26

- Replace the repeated learning-placement clause with sentence-function-aware copy.
- Use distinct deterministic wording for definitions, requirements, workflows, benefits, skills, and general context.
- Introduce target audiences only when the source paragraph addresses the same audience.
- Avoid unsafe rewrites of long, definitional, or evaluation-focused sentences.
- Diversify ranked opportunities while preserving deterministic output and API compatibility.

## 1.1.3 - 2026-09-26

- Removed navigation, sidebar, footer, and repeated promotional copy from page evidence.
- Added anchor-aware target profiles built from topical headings and substantive body copy.
- Separated broad topic alignment from specialized destination-purpose evidence.
- Allowed strong course-topic matches to return editorial-review opportunities without lowering beta thresholds.
- Prevented table and list introductions from becoming malformed contextual rewrites.
- Added regression coverage for the DelightChat and Great Learning AI-agent course case.

## 1.1.2 - 2026-09-26

- Classify destination pages using on-page evidence with the final URL as a supporting signal.
- Use audience-specific wording only when the destination explicitly identifies that audience.
- Use neutral contextual wording when the destination audience is not established.
- Separate courses and training from guides, articles, services, pricing, implementation, and governance resources.
- Preserve the existing v1 API contract, WordPress integration, thresholds, and rate limits.

## 1.1.1 - 2026-09-26

- Add deterministic one-sentence anchor integration when a supported exact anchor is absent.
- Generate context-specific fallback sentences instead of repeating a generic resource phrase.
- Calculate original-text preservation from retained source words and require editorial review for generated copy.
- Preserve the existing v1 API contract, strategy values, thresholds, and rate limits.

## 1.1.0 - 2026-08-30

- Add the shared placement analysis service and FastAPI v1 interface.
- Add genuine no-match and editorial-review outcomes.
- Return Unicode-safe structured text and link segments instead of browser offsets.
- Pin outbound connections to validated public IP addresses across redirects and robots requests.
- Add compressed and decompressed response limits, strict API validation, Turnstile verification, rate limits, concurrency controls, and production Host/origin enforcement.
- Add Render Free deployment configuration and v1 contract tests.

All notable changes to Backlink Intelligence are documented here.

## 1.0.1 - 2026-08-30

### Fixed

- Prevented partial anchor insertion inside larger word forms such as rendering `AI agents` as `[AI Agent]s`.
- Preserved the publisher's existing anchor capitalization when the requested keyword differs only by case.
- Added conservative singular/plural anchor adaptation when the natural grammatical form already exists in source copy.
- Added destination-intent scoring so context specific to the destination topic receives more weight than generic anchor repetition.
- Added destination-fit and actual placed-anchor details to placement CLI output.
- Replaced mechanical target-title fallback sentences with concise destination-intent-aware editorial copy.

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
