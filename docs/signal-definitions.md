# Signal Definitions

This document defines terminology used by Backlink Intelligence. Exact algorithms may evolve, but public output should retain clear definitions.

## Page relevance

How strongly the source page's subject matter aligns with the target page.

Planned labels:

- Very Low
- Low
- Medium
- High
- Very High

## Context relevance

How strongly the local paragraph/sentence around a link or proposed placement aligns with the target page.

## Destination fit

Whether the target URL is a contextually appropriate destination for the source discussion.

This is an editorial/semantic observation, not a ranking prediction.

## Placement type

Planned categories:

- Editorial Context
- Resource List
- Author Bio
- Navigation
- Sidebar
- Footer
- Comment / UGC
- Sponsored Block
- Unknown

## Anchor fit

A review of whether the anchor text is grammatically natural, contextually useful, and semantically aligned with the destination.

## Editorial intervention

How much a suggested placement alters the publisher's existing paragraph.

Planned labels:

- Minimal
- Low
- Medium
- High

The project may also expose supporting counts such as original words, words added, and original words modified.

## Review signals

Observable evidence that deserves human attention. Examples may include:

- unusually high external-link density
- several unrelated commercial outbound categories
- ambiguous placement
- weak destination fit
- requested anchor with poor grammatical fit
- crawl/indexability uncertainty

A review signal is not automatically a spam or penalty determination.

## Analysis confidence

How confident the software is that it successfully extracted and interpreted the relevant evidence.

Confidence can be reduced by factors such as:

- blocked fetching
- JavaScript-dependent rendering
- ambiguous main-content extraction
- missing target content
- unusual HTML structure
- conflicting metadata
