from __future__ import annotations

import math
import re
from collections import Counter

from .models import PageEvidence, RelevanceEvidence

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#.-]{1,}", re.I)
_STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "how", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their", "this", "to", "was", "we", "what", "when", "where", "which", "with", "you", "your", "can", "will", "more"}


def tokens(text: str) -> list[str]:
    return [t.lower().strip(".-") for t in _TOKEN.findall(text or "") if t.lower().strip(".-") not in _STOP]


def _cosine(a: str, b: str) -> float:
    ca, cb = Counter(tokens(a)), Counter(tokens(b))
    if not ca or not cb:
        return 0.0
    common = set(ca) & set(cb)
    numerator = sum(ca[t] * cb[t] for t in common)
    da = math.sqrt(sum(v * v for v in ca.values()))
    db = math.sqrt(sum(v * v for v in cb.values()))
    return numerator / (da * db) if da and db else 0.0


def _overlap(a: str, b: str) -> float:
    sa, sb = set(tokens(a)), set(tokens(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _level(score: float) -> str:
    if score >= 0.55:
        return "very_high"
    if score >= 0.35:
        return "high"
    if score >= 0.18:
        return "medium"
    return "low"


def similarity(a: str, b: str) -> float:
    return round((0.72 * _cosine(a, b)) + (0.28 * _overlap(a, b)), 4)


def analyze_relevance(source: PageEvidence, target: PageEvidence, context: str = "") -> RelevanceEvidence:
    title = similarity(" ".join([source.title, source.h1]), " ".join([target.title, target.h1]))
    headings = similarity(" ".join(source.headings), " ".join(target.headings))
    page = similarity(source.text, target.text)
    ctx = similarity(context, target.text) if context else 0.0
    combined = 0.45 * page + 0.25 * title + 0.15 * headings + 0.15 * ctx
    source_terms, target_terms = set(tokens(source.text)), set(tokens(target.text))
    shared = sorted(source_terms & target_terms, key=lambda t: (-len(t), t))[:15]
    return RelevanceEvidence(page_similarity=round(page, 4), context_similarity=round(ctx, 4), title_similarity=round(title, 4), heading_similarity=round(headings, 4), level=_level(combined), shared_terms=shared)
