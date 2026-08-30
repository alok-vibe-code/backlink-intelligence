# Backlink Intelligence

**Open-source backlink intelligence based on evidence, context, and editorial fit.**

Backlink Intelligence is a local-first Python toolkit for SEO professionals who want to evaluate backlink opportunities beyond a single domain-level authority metric.

It covers the complete working cycle:

**Qualify → Audit → Place → Monitor → Analyze**

The core tool works without paid SEO APIs or paid AI APIs.

## What it does

| Command | Purpose | Status |
| --- | --- | --- |
| `audit` | Inspect an existing backlink and its page-level evidence | ✅ Available |
| `qualify` | Evaluate backlink prospects from CSV | ✅ Available |
| `place` | Find contextual placement opportunities and produce Before/After suggestions | ✅ Available |
| `monitor` | Detect changes to acquired backlinks over time | ✅ Available |
| `portfolio` | Review anchor, destination, and placement distributions | ✅ Available |

## Why this project exists

DA, DR, and similar third-party metrics can be useful inputs, but they do not describe the full quality of an individual link placement.

A backlink also has:

- a source page and destination page,
- topical and contextual alignment,
- an anchor,
- a surrounding paragraph,
- a placement type,
- link attributes,
- crawl/indexability evidence,
- and an outbound-link neighborhood.

Backlink Intelligence surfaces those observable signals so an SEO can make a more informed decision.

It does **not** claim to reproduce Google's ranking systems, predict penalties, or provide a universal "Google backlink score."

## Installation

Python 3.11+ is required.

```bash
python -m pip install .
```

For development:

```bash
git clone https://github.com/alok-vibe-code/backlink-intelligence.git
cd backlink-intelligence
python -m pip install -e .
```

Verify the installation:

```bash
backlink-intelligence --version
backlink-intelligence status
```

## 1. Audit an existing backlink

```bash
backlink-intelligence audit \
  "https://publisher.example/article" \
  "https://brand.example/target-page"
```

Typical evidence includes:

- source/target HTTP status,
- backlink found/not found,
- anchor text,
- `nofollow`, `sponsored`, and `ugc` attributes,
- placement classification,
- source indexability,
- page/context relevance,
- external-link counts,
- review flags,
- recommendation,
- and analysis confidence.

JSON output:

```bash
backlink-intelligence audit SOURCE_URL TARGET_URL --json
```

Save JSON:

```bash
backlink-intelligence audit SOURCE_URL TARGET_URL --output audit.json
```

## 2. Qualify prospects in bulk

Create a CSV:

```csv
source_url,target_url,preferred_anchor
https://publisher.example/post,https://brand.example/page,agentic ai course
```

Run:

```bash
backlink-intelligence qualify prospects.csv --output qualification-report.csv
```

The report includes evidence such as relevance, placement potential, outbound-link density, review flags, confidence, and a workflow recommendation:

- `prioritize`
- `manual_review`
- `low_priority`

## 3. Find contextual link placements

This is the signature workflow.

```bash
backlink-intelligence place \
  "https://publisher.example/article" \
  "https://brand.example/target" \
  --anchor "agentic ai course" \
  --top 3
```

For each recommended paragraph the tool returns:

- paragraph number,
- context-fit level,
- destination-fit level and score,
- requested anchor,
- actual placed anchor (preserving source capitalization/grammar where possible),
- placement strategy,
- editorial intervention level,
- original-text preservation,
- **Before paragraph**,
- **After paragraph**,
- reasons,
- and review flags.

The deterministic rewrite engine deliberately favors minimal editorial change. Exact phrase matching uses complete word boundaries, preserves the publisher's existing capitalization, and can conservatively adapt a singular/plural anchor to the grammatical form already present in source copy. Destination-intent scoring also helps distinguish a paragraph that matches the target's specific topic from one that merely repeats the requested anchor. Its output is a placement draft for human review, not an instruction to publish automatically.

## 4. Monitor acquired backlinks

Create a CSV:

```csv
source_url,target_url,expected_anchor
https://publisher.example/article,https://brand.example/page,AI guide
```

First check creates the baseline:

```bash
backlink-intelligence monitor links.csv \
  --state backlink-state.json \
  --output monitor-report.csv
```

Run the same command later to detect:

- removed links,
- anchor changes,
- `rel` attribute changes,
- placement changes,
- source/target status changes,
- canonical changes,
- and robots changes.

## 5. Analyze a backlink portfolio

Input CSV should contain `target_url` and can optionally include `anchor` and `placement`.

```bash
backlink-intelligence portfolio backlinks.csv --output portfolio.json
```

The report summarizes:

- anchor-category distribution,
- destination distribution,
- placement distribution.

## Evidence model

Backlink Intelligence intentionally avoids an unexplained universal 0–100 backlink score.

Instead it exposes dimensions such as:

- **Relevance:** low / medium / high / very high
- **Placement:** editorial context / navigation / sidebar / footer / unknown
- **Risk signals:** explicit review flags
- **Confidence:** low / medium / high
- **Recommendation:** workflow guidance, not a ranking claim

See [Methodology](docs/methodology.md) and [Signal Definitions](docs/signal-definitions.md).

## How relevance works

The v1 engine is deterministic and local. It combines:

- normalized term overlap,
- cosine similarity over term-frequency vectors,
- title/H1 alignment,
- heading alignment,
- page-to-page similarity,
- paragraph-to-target similarity,
- and shared topical terms.

This makes the result reproducible and inspectable without requiring an LLM API.

## Link placement philosophy

The placement engine follows three principles:

1. **Editorial fit before keyword insertion.**
2. **Preserve publisher copy whenever possible.**
3. **Show the evidence and let a human approve the final wording.**

When the exact requested anchor already exists naturally, the tool uses minimal insertion. Otherwise it adds a conservative contextual sentence rather than rewriting the entire paragraph.

## Crawl and security safeguards

The fetcher is intentionally bounded:

- only HTTP/HTTPS URLs,
- embedded URL credentials blocked,
- localhost/private/link-local/reserved IPs blocked,
- DNS-resolved private addresses blocked,
- redirects revalidated,
- redirect count limited,
- request timeout,
- maximum HTML response size,
- non-HTML content rejected,
- identifiable user agent.

See [SECURITY.md](SECURITY.md) and [Ethical Crawling](docs/ethical-crawling.md).

## Current limitations

The v1 parser focuses on server-delivered HTML. Pages whose meaningful content or links are rendered only by client-side JavaScript may require browser rendering, which is intentionally not bundled into the zero-dependency core.

The Before/After engine is deterministic and conservative. It does not attempt unrestricted AI copywriting. Optional model-assisted rewriting can be added later without making it mandatory for core functionality.

See [Limitations](docs/limitations.md).

## Testing

The repository includes deterministic offline tests for:

- HTML/meta/link extraction,
- placement classification,
- URL normalization,
- outbound-link evidence,
- relevance,
- contextual placement ranking,
- Before/After generation,
- monitoring change detection,
- portfolio analysis,
- URL safety,
- CLI behavior.

Run:

```bash
python -m unittest discover -s tests -v
```

## Methodology background

This project implements ideas developed in:

**[Backlink Quality Beyond DA & DR](https://alokblog.com/backlink-quality-beyond-da-dr/)**

The article explains the conceptual framework. This repository turns that framework into transparent, testable software.

## Phase 2: public website integration

The GitHub repository is the source of truth for the analysis engine. A later phase can expose selected capabilities through a public interface on `alokblog.com`, using the same package rather than duplicating SEO logic.

The initial public web version is expected to focus on:

- single backlink audit,
- contextual placement analysis,
- Before/After placement recommendations.

Bulk crawling and continuous monitoring are better suited to the local/open-source version unless hosted infrastructure is deliberately provisioned for them.

## Project structure

```text
backlink_intelligence/
├── audit.py
├── cli.py
├── fetcher.py
├── html_utils.py
├── link_analysis.py
├── models.py
├── monitor.py
├── placement.py
├── portfolio.py
├── qualify.py
├── relevance.py
├── reporting.py
└── safety.py
```

## Contributing

Contributions, test cases, parser improvements, and evidence-based methodology discussions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## License

MIT. See [LICENSE](LICENSE).

## Disclaimer

Backlink Intelligence is an independent open-source SEO research and workflow tool. It is not affiliated with Google, Ahrefs, Semrush, Moz, Majestic, or any other search engine or SEO platform. Outputs should be treated as evidence for professional review, not as guarantees of ranking impact, penalties, or search-engine behavior.

## Public beta API

Version 1.1 adds an optional FastAPI service for the public Backlink Placement Analyzer. Install it with:

```bash
pip install ".[api]"
uvicorn backlink_intelligence.api:app --host 127.0.0.1 --port 8000
```

The public endpoint is `POST /v1/place`. It accepts a source URL, target URL, preferred anchor, and Cloudflare Turnstile token. A valid analysis returns either `completed` or `no_suitable_placement`; the latter is a successful HTTP 200 outcome, not an API error.

Generated copy is returned as plain `after_text` plus `after_segments` containing only text and link records. The API never returns executable markup. Numeric scores are internal ranking evidence and must not be presented as probabilities, authority scores, ranking potential, or percentage quality. Beta thresholds are private server configuration and are not included in responses.

Production deployment settings are documented in `render.yaml` and `.env.example`. Free hosting has capacity, cold-start, and bandwidth limits; the service does not require a database, paid SEO data, or an LLM API.
