from __future__ import annotations

from .fetcher import FetchConfig, fetch_page
from .models import PageEvidence, PlacementSuggestion
from .relevance import similarity, tokens


def _intervention(preservation: float, added_words: int) -> str:
    if preservation >= 95 and added_words <= 24:
        return "low"
    if preservation >= 85 and added_words <= 40:
        return "medium"
    return "high"


def _anchor_naturalness(anchor: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    words = anchor.split()
    if not anchor.strip():
        return "weak", ["empty_anchor"]
    if len(words) > 7:
        warnings.append("long_anchor")
    if anchor.isupper() and len(anchor) > 5:
        warnings.append("all_caps_anchor")
    if any(ch in anchor for ch in ["|", "[", "]", "{"]):
        warnings.append("awkward_anchor_characters")
    return ("strong" if not warnings else "medium"), warnings


def _select_anchor(preferred: str, target_title: str) -> tuple[str, list[str]]:
    preferred = preferred.strip()
    if not preferred:
        return (target_title.strip() or "this related resource"), []
    _, warnings = _anchor_naturalness(preferred)
    if warnings and target_title.strip():
        return target_title.strip(), warnings + ["suggested_anchor_differs_from_requested"]
    return preferred, warnings


def _compose_after(paragraph: str, anchor: str, target_url: str, target_title: str) -> tuple[str, str]:
    linked = f"[{anchor}]({target_url})"
    idx = paragraph.lower().find(anchor.lower())
    if idx >= 0:
        return "minimal_insertion", paragraph[:idx] + linked + paragraph[idx + len(anchor):]
    topic = target_title.strip()
    sentence = f"For a more detailed resource on {topic}, see {linked}." if topic and topic.lower() != anchor.lower() else f"For a more detailed resource on this topic, see {linked}."
    return "contextual_sentence", paragraph.rstrip() + " " + sentence


def rank_placements(source: PageEvidence, target: PageEvidence, preferred_anchor: str, target_url: str, *, top_n: int = 3) -> list[PlacementSuggestion]:
    if source.status_code != 200 or target.status_code != 200:
        return []
    anchor, anchor_warnings = _select_anchor(preferred_anchor, target.title)
    target_profile = " ".join([target.title, target.h1, *target.headings, target.text[:12000]])
    candidates: list[tuple[float, int, str]] = []
    for i, paragraph in enumerate(source.paragraphs, start=1):
        wc = len(paragraph.split())
        if wc < 18 or wc > 260:
            continue
        score = similarity(paragraph, target_profile)
        anchor_terms = set(tokens(anchor))
        anchor_overlap = len(anchor_terms & set(tokens(paragraph))) / max(len(anchor_terms), 1)
        candidates.append((round((0.84 * score) + (0.16 * anchor_overlap), 4), i, paragraph))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    suggestions: list[PlacementSuggestion] = []
    for rank, (score, index, paragraph) in enumerate(candidates[:max(top_n, 1)], start=1):
        strategy, after = _compose_after(paragraph, anchor, target_url, target.title)
        original_words = max(len(paragraph.split()), 1)
        added = max(len(after.split()) - original_words, 0)
        preservation = 100.0
        warnings = list(anchor_warnings)
        reasons = ["paragraph_has_strong_target_similarity"] if score >= 0.25 else ["best_available_context_match"]
        reasons.append("anchor_already_present_in_original_copy" if strategy == "minimal_insertion" else "publisher_copy_preserved")
        if score < 0.12:
            warnings.append("weak_context_match_manual_review_required")
        context_level = "very_high" if score >= 0.48 else "high" if score >= 0.30 else "medium" if score >= 0.15 else "low"
        suggestions.append(PlacementSuggestion(rank=rank, paragraph_index=index, score=score, context_level=context_level, requested_anchor=preferred_anchor, suggested_anchor=anchor, strategy=strategy, before=paragraph, after=after, added_words=added, preservation_percent=preservation, intervention=_intervention(preservation, added), reasons=reasons, warnings=warnings))
    return suggestions


def suggest_placements(source_url: str, target_url: str, preferred_anchor: str, *, top_n: int = 3, config: FetchConfig | None = None) -> list[PlacementSuggestion]:
    source = fetch_page(source_url, config)
    target = fetch_page(target_url, config)
    return rank_placements(source, target, preferred_anchor, target_url, top_n=top_n)
