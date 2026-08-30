from __future__ import annotations

import re

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
    # Preserve the user's keyword when it reads naturally. When it is mechanically
    # awkward, offer the target title as a safer editorial alternative.
    if warnings and target_title.strip():
        return target_title.strip(), warnings + ["suggested_anchor_differs_from_requested"]
    return preferred, warnings


def _find_complete_phrase(text: str, phrase: str) -> re.Match[str] | None:
    """Find a phrase only when it is not embedded inside a larger word form."""
    phrase = phrase.strip()
    if not phrase:
        return None
    pattern = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)
    return pattern.search(text)


def _simple_anchor_variants(anchor: str) -> list[str]:
    """Return conservative singular/plural variants for the final anchor word."""
    anchor = anchor.strip()
    if not anchor or " " not in anchor:
        return []
    prefix, last = anchor.rsplit(" ", 1)
    if not last.isalpha():
        return []

    lower = last.lower()
    variants: list[str] = []
    # Singular -> simple plural. This intentionally avoids guessing irregular forms.
    if not lower.endswith("s"):
        variants.append(f"{prefix} {last}s")
    # Plural -> simple singular, excluding common singular words that end in s.
    elif len(last) > 3 and not lower.endswith(("ss", "us", "is")):
        variants.append(f"{prefix} {last[:-1]}")
    return variants


def _compose_after(
    paragraph: str,
    anchor: str,
    target_url: str,
    target_title: str,
) -> tuple[str, str, str, list[str]]:
    """Compose the draft while preserving source grammar/capitalization when possible."""
    exact = _find_complete_phrase(paragraph, anchor)
    if exact is not None:
        placed_anchor = exact.group(0)
        linked = f"[{placed_anchor}]({target_url})"
        after = paragraph[: exact.start()] + linked + paragraph[exact.end() :]
        notes: list[str] = []
        if placed_anchor != anchor:
            notes.append("source_anchor_capitalization_preserved")
        return "minimal_insertion", after, placed_anchor, notes

    # If the exact requested form is not present, prefer a complete natural word-form
    # already in the publisher copy instead of creating artifacts such as [AI Agent]s.
    for variant in _simple_anchor_variants(anchor):
        match = _find_complete_phrase(paragraph, variant)
        if match is not None:
            placed_anchor = match.group(0)
            linked = f"[{placed_anchor}]({target_url})"
            after = paragraph[: match.start()] + linked + paragraph[match.end() :]
            return (
                "minimal_insertion",
                after,
                placed_anchor,
                ["anchor_adapted_to_source_grammar", "requested_anchor_not_used_verbatim"],
            )

    linked = f"[{anchor}]({target_url})"
    topic = target_title.strip()
    if topic and topic.lower() != anchor.lower():
        sentence = f"For a more detailed resource on {topic}, see {linked}."
    else:
        sentence = f"For a more detailed resource on this topic, see {linked}."
    return "contextual_sentence", paragraph.rstrip() + " " + sentence, anchor, []


def _stem(term: str) -> str:
    """Small deterministic normalizer used only for destination-intent comparison."""
    term = term.lower().strip(".-")
    if len(term) > 5 and term.endswith("ies"):
        return term[:-3] + "y"
    if len(term) > 5 and term.endswith("ing"):
        return term[:-3]
    if len(term) > 4 and term.endswith("es") and not term.endswith("ses"):
        return term[:-2]
    if len(term) > 4 and term.endswith("s") and not term.endswith(("ss", "us", "is")):
        return term[:-1]
    return term


def _stems(text: str) -> set[str]:
    return {_stem(term) for term in tokens(text)}


def _destination_intent_score(paragraph: str, target: PageEvidence, anchor: str) -> float:
    """Measure fit to destination-specific intent, not just the requested anchor."""
    core_profile = " ".join([target.title, target.h1]).strip()
    if not core_profile:
        core_profile = " ".join(target.headings[:8]).strip()
    if not core_profile:
        return similarity(paragraph, target.text[:4000])

    paragraph_terms = _stems(paragraph)
    core_terms = _stems(core_profile)
    anchor_terms = _stems(anchor)

    # Prefer terms that describe what makes the destination distinct from the anchor.
    intent_terms = core_terms - anchor_terms
    if len(intent_terms) < 2:
        intent_terms = core_terms
    intent_overlap = len(paragraph_terms & intent_terms) / max(len(intent_terms), 1)
    semantic = similarity(paragraph, core_profile)
    return round((0.35 * semantic) + (0.65 * intent_overlap), 4)


def _destination_level(score: float) -> str:
    if score >= 0.25:
        return "very_high"
    if score >= 0.14:
        return "high"
    if score >= 0.08:
        return "medium"
    return "low"


def rank_placements(
    source: PageEvidence,
    target: PageEvidence,
    preferred_anchor: str,
    target_url: str,
    *,
    top_n: int = 3,
) -> list[PlacementSuggestion]:
    if source.status_code != 200 or target.status_code != 200:
        return []

    anchor, anchor_warnings = _select_anchor(preferred_anchor, target.title)
    target_profile = " ".join([target.title, target.h1, *target.headings, target.text[:12000]])
    candidates: list[tuple[float, float, int, str]] = []

    for i, paragraph in enumerate(source.paragraphs, start=1):
        wc = len(paragraph.split())
        if wc < 18 or wc > 260:
            continue
        semantic_score = similarity(paragraph, target_profile)
        destination_score = _destination_intent_score(paragraph, target, anchor)
        anchor_terms = set(tokens(anchor))
        anchor_overlap = len(anchor_terms & set(tokens(paragraph))) / max(len(anchor_terms), 1)
        # Destination intent gets meaningful weight so a pricing/cost paragraph beats a
        # generic paragraph that merely repeats the requested anchor.
        score = round((0.62 * semantic_score) + (0.30 * destination_score) + (0.08 * anchor_overlap), 4)
        candidates.append((score, destination_score, i, paragraph))

    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    suggestions: list[PlacementSuggestion] = []
    for rank, (score, destination_score, index, paragraph) in enumerate(candidates[: max(top_n, 1)], start=1):
        strategy, after, placed_anchor, compose_notes = _compose_after(paragraph, anchor, target_url, target.title)
        original_words = max(len(paragraph.split()), 1)
        after_words = len(after.split())
        added = max(after_words - original_words, 0)
        preservation = 100.0 if strategy in {"minimal_insertion", "contextual_sentence"} else 90.0
        warnings = list(anchor_warnings)
        reasons = ["paragraph_has_strong_target_similarity"] if score >= 0.25 else ["best_available_context_match"]
        if strategy == "minimal_insertion":
            reasons.append("anchor_already_present_in_original_copy")
        else:
            reasons.append("publisher_copy_preserved")
        for note in compose_notes:
            if note == "requested_anchor_not_used_verbatim":
                warnings.append(note)
            else:
                reasons.append(note)
        if destination_score >= 0.14:
            reasons.append("strong_destination_intent_alignment")
        elif destination_score < 0.08:
            warnings.append("weak_destination_intent_alignment")
        if score < 0.12:
            warnings.append("weak_context_match_manual_review_required")
        context_level = "very_high" if score >= 0.48 else "high" if score >= 0.30 else "medium" if score >= 0.15 else "low"
        suggestions.append(
            PlacementSuggestion(
                rank=rank,
                paragraph_index=index,
                score=score,
                context_level=context_level,
                destination_score=destination_score,
                destination_fit=_destination_level(destination_score),
                requested_anchor=preferred_anchor,
                suggested_anchor=placed_anchor,
                strategy=strategy,
                before=paragraph,
                after=after,
                added_words=added,
                preservation_percent=preservation,
                intervention=_intervention(preservation, added),
                reasons=reasons,
                warnings=warnings,
            )
        )
    return suggestions


def suggest_placements(
    source_url: str,
    target_url: str,
    preferred_anchor: str,
    *,
    top_n: int = 3,
    config: FetchConfig | None = None,
) -> list[PlacementSuggestion]:
    source = fetch_page(source_url, config)
    target = fetch_page(target_url, config)
    return rank_placements(source, target, preferred_anchor, target_url, top_n=top_n)
