# Architecture

Backlink Intelligence is intended to have one reusable analysis engine with multiple interfaces.

```text
                    Backlink Intelligence Engine
                              |
          +-------------------+-------------------+
          |                   |                   |
         CLI              Local Web UI       Python Package
          |                   |                   |
       CSV/JSON             Browser           Integrations
```

A later public web deployment should reuse the same engine rather than reimplement SEO logic in a separate codebase.

## Planned engine layers

### Fetching and safety

Responsible for:

- URL normalization and validation
- network safety controls
- timeouts and redirect limits
- response-size limits
- caching
- polite rate limiting

### Extraction

Responsible for:

- HTML parsing
- main-content extraction
- metadata extraction
- headings
- link extraction
- context extraction

### Evidence models

Typed structures representing:

- source page
- target page
- detected backlink
- surrounding context
- link attributes
- crawl/indexability observations

### Relevance

Responsible for explainable relevance signals between:

- source and target,
- context and target,
- and later sampled domain/topic evidence.

### Placement

Responsible for:

- candidate paragraph ranking
- anchor fit
- insertion strategy selection
- Before/After recommendations
- editorial intervention measurement
- rejection reasons

### Qualification

Combines evidence into transparent review dimensions such as:

- relevance
- destination fit
- editorial fit
- review signals
- confidence
- recommendation

### Monitoring

Responsible for:

- baseline snapshots
- change detection
- retention history
- status transitions

### Reporting

Intended output formats:

- terminal
- JSON
- CSV
- HTML

## Public website phase

The future public architecture should resemble:

```text
alokblog.com/tools/backlink-intelligence/
                  |
             Web front end
                  |
          Secure analysis API
                  |
       backlink_intelligence package
```

The public service requires stronger controls than the local CLI, including SSRF defenses, abuse prevention, rate limiting, request isolation, and bounded resource usage.
