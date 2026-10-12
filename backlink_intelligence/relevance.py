from __future__ import annotations

import math
import unicodedata
from collections import Counter

from .models import PageEvidence, RelevanceEvidence

_STOP_ENGLISH = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "how", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their", "this", "to", "was", "we", "what", "when", "where", "which", "with", "you", "your", "can", "will", "more"}
# Keep the list conservative: product nouns, negation ("không", "chưa") and
# meaningful short syllables ("ổ", "ý") must still contribute to topical evidence.
_STOP_VIETNAMESE = {
    "bởi", "các", "cho", "của", "cũng", "đã", "đang", "đây", "để", "đó",
    "được", "khi", "là", "mà", "một", "này", "những", "rằng", "sẽ", "tại",
    "thì", "trong", "từ", "và", "vẫn", "về", "với",
}
_STOP = _STOP_ENGLISH | _STOP_VIETNAMESE


def normalize_text(text: str) -> str:
    """Normalize spelling/case for comparison without removing Vietnamese tones."""
    return unicodedata.normalize("NFC", (text or "").casefold())


def tokens(text: str) -> list[str]:
    """Extract Unicode terms, retaining technical identifiers such as C++/KV-48.

    NFC makes composed and decomposed Vietnamese equivalent. Combining marks
    remain attached to their word even when a Unicode script has no NFC form.
    Single ASCII letters retain the upstream exclusion; a Vietnamese syllable
    such as "ổ" is a complete word and is kept. Underscores remain separators.
    """
    result: list[str] = []
    current: list[str] = []

    def finish() -> None:
        if not current:
            return
        raw = "".join(current)
        token = raw.strip(".-")
        if token and (len(raw) > 1 or not raw.isascii()) and token not in _STOP:
            result.append(token)
        current.clear()

    for character in normalize_text(text):
        if character.isalnum():
            current.append(character)
        elif current and (unicodedata.category(character).startswith("M") or character in "+#.-"):
            current.append(character)
        else:
            finish()
    finish()
    return result


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
