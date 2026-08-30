# Limitations

Backlink Intelligence is intended to assist SEO review, not replace professional judgment.

## Search-engine behavior

The tool cannot determine exactly how Google or another search engine values an individual backlink. It does not reproduce proprietary ranking systems.

## Third-party authority metrics

The core project does not require DA, DR, Authority Score, Trust Flow, or similar proprietary metrics. Optional integrations may expose third-party data later when users provide their own credentials.

## Rendering

Some websites depend heavily on client-side JavaScript. A lightweight HTTP crawler may not observe exactly what a browser renders. The project should report reduced confidence rather than silently treating extraction as complete.

## Crawl restrictions

Websites may block automated requests, require authentication, rate-limit clients, or expose content differently by region or user agent.

## Semantic analysis

Relevance estimates are approximations. Local statistical models, embeddings, or language models can all misunderstand context. Results should expose supporting evidence and confidence.

## Placement recommendations

A suggested Before/After paragraph is not permission to modify another publisher's content. It is a drafting aid for editorial review. The final placement should make sense to the publisher and reader.

## Historical monitoring

A missing or changed link may be temporary. Monitoring should distinguish observation from cause and preserve timestamps for later review.

## Public web deployment

The local project and a hosted public service have different privacy, abuse, security, and operating-cost considerations. Hosted functionality should be introduced only with appropriate controls.
