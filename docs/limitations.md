# Limitations

Backlink Intelligence intentionally avoids claims the available evidence cannot support.

## JavaScript-rendered content

The v1 core fetches server-delivered HTML and does not bundle a browser engine. Links or text created only after JavaScript execution may not be visible to the parser.

## Search-engine behavior

The project cannot determine how Google or another search engine values a particular backlink. Recommendations are workflow decisions derived from observable evidence.

## Relevance

The v1 relevance engine is deterministic lexical analysis. It does not fully capture semantics, multilingual nuance, irony, or deep entity relationships.

## Placement classification

Semantic HTML landmarks improve classification. Poorly structured pages may be returned as `unknown` even when a human can identify the placement visually.

## Before/After drafts

The deterministic rewrite logic is deliberately conservative. It should be reviewed by an editor before use. It is not intended to imitate unrestricted generative copywriting.

## Authority metrics and traffic

The zero-cost core does not fetch proprietary DA/DR/traffic datasets. Optional third-party enrichment can be implemented separately when users have lawful access to those services.
