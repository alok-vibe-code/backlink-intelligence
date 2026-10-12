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

## Unicode and Vietnamese text

Relevance terms use Unicode letters, numbers and attached combining marks. Text is casefolded and normalized to NFC for comparison, so equivalent composed and decomposed Vietnamese produce the same terms. Tone marks are preserved: `ma`, `má`, `mã` and `mạ` remain different terms. Meaningful non-ASCII single-character syllables such as `ổ` are retained; the existing exclusion of single ASCII letters remains.

Technical identifiers such as `C++`, `C#`, `Node.js` and `KV-48-NC` retain their existing handling. A conservative Vietnamese stopword list is combined with the existing English list; negation such as `không` and `chưa` remains part of the evidence. This shared list can still exclude ambiguous ASCII words such as `an` or `to` in non-English contexts.

Anchor matching accepts NFC/NFD-equivalent phrases while preserving the source substring, spelling and offsets. English plural variants and stemming do not modify words with non-ASCII letters or product identifiers.

These changes improve lexical evidence, not semantic understanding. Vietnamese compound-word segmentation is not provided, similarity remains token-based, and generated fallback placement copy still uses the existing English templates.

The deterministic Unicode regression tests use synthetic local fixtures and make no live requests:

```bash
python -m unittest discover -s tests -p "test_unicode_vietnamese.py" -v
```
