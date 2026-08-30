# Architecture

Backlink Intelligence separates analysis logic from interfaces so the same engine can power the CLI, automation, and a later website integration.

```text
CLI / CSV / future web API
          |
          v
 Backlink Intelligence engine
          |
  +-------+-----------------------------+
  |       |        |        |           |
Fetcher  Parser  Relevance Placement  Monitoring
  |       |        |        |           |
Safety  Evidence  Scoring  Before/After History
```

## Modules

- `safety.py`: validates public HTTP/HTTPS destinations and blocks private-network targets.
- `fetcher.py`: bounded fetches, redirect checks, response-size limits, HTML-only processing.
- `html_utils.py`: standard-library HTML extraction.
- `models.py`: typed dataclasses used across commands.
- `link_analysis.py`: URL normalization, backlink detection, outbound-link evidence.
- `relevance.py`: deterministic similarity and shared-term analysis.
- `audit.py`: combines page, backlink, relevance, and outbound evidence.
- `qualify.py`: batch prospect decision workflow.
- `placement.py`: paragraph ranking and Before/After drafts.
- `monitor.py`: persisted baselines and change detection.
- `portfolio.py`: anchor, destination, and placement distributions.
- `reporting.py`: terminal/JSON presentation helpers.
- `cli.py`: command-line interface.

## Interface rule

Business logic must not be embedded in the CLI. The future alokblog.com backend should import these modules directly, preserving one source of truth.
