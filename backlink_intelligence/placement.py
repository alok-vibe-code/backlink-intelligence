from __future__ import annotations

from collections import Counter
import re
from urllib.parse import unquote, urlsplit

from .fetcher import FetchConfig, fetch_page
from .models import PageEvidence, PlacementSuggestion, TextSegment
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


def _fallback_anchor_case(anchor: str) -> str:
    """Use conservative editorial casing for generated fallback copy.

    When a requested anchor begins with a short acronym followed by title-cased words,
    preserve the acronym but lowercase the descriptive words. This turns ``AI Agent``
    into ``AI agent`` without changing arbitrary brand or mixed-case anchors.
    """
    words = anchor.strip().split()
    if len(words) < 2:
        return anchor.strip()
    if not (words[0].isupper() and 1 < len(words[0]) <= 5):
        return anchor.strip()

    changed = False
    output = [words[0]]
    for word in words[1:]:
        if word[:1].isupper() and word[1:].islower():
            output.append(word.lower())
            changed = True
        else:
            output.append(word)
    return " ".join(output) if changed else anchor.strip()


def _anchor_with_article(anchor: str) -> str:
    """Return a generated-copy anchor with a conservative indefinite article."""
    anchor = anchor.strip()
    if not anchor:
        return anchor
    first = anchor.split()[0].casefold().strip(".()[]{}\"'")
    if first in {"a", "an", "the", "this", "these", "our", "your"}:
        return anchor
    # Common initialisms whose spoken form begins with a vowel sound.
    vowel_initialisms = {"ai", "aeo", "seo", "smb", "mba", "ml", "nlp", "llm", "api"}
    consonant_vowel_words = ("uni", "use", "user", "euro", "one")
    article = "an" if first in vowel_initialisms or first[:1] in "aeiou" else "a"
    if first.startswith(consonant_vowel_words):
        article = "a"
    return f"{article} {anchor}"


def _target_profile(target: PageEvidence) -> str:
    return " ".join([target.title, target.h1, *target.headings, target.text[:12000]])


_TARGET_TYPE_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cost", ("cost", "pricing", "price", "prices", "tco", "roi", "plans")),
    (
        "learning",
        (
            "course",
            "courses",
            "training",
            "curriculum",
            "certificate",
            "certification",
            "bootcamp",
            "class",
            "classes",
            "learning program",
            "degree program",
        ),
    ),
    (
        "service",
        ("service", "services", "consulting", "agency", "platform", "software", "product", "solution", "solutions"),
    ),
    ("implementation", ("implementation", "integration", "deployment", "development solution")),
    ("governance", ("risk", "governance", "compliance", "security", "privacy", "audit")),
    ("guide", ("guide", "article", "research", "report", "tutorial", "handbook", "resource", "roadmap")),
)


_TARGET_AUDIENCES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("finance professionals", ("finance professionals", "financial professionals")),
    ("marketing professionals", ("marketing professionals",)),
    ("SEO professionals", ("seo professionals",)),
    ("working professionals", ("working professionals",)),
    ("business leaders", ("business leaders",)),
    ("finance teams", ("finance teams",)),
    ("marketing teams", ("marketing teams",)),
    ("software developers", ("software developers",)),
    ("developers", ("developers",)),
    ("marketers", ("marketers",)),
    ("executives", ("executives",)),
    ("students", ("students",)),
    ("learners", ("learners",)),
    ("researchers", ("researchers",)),
    ("educators", ("educators",)),
    ("professionals", ("professionals",)),
)


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, flags=re.IGNORECASE) is not None


def _target_url_text(target: PageEvidence) -> str:
    url = target.final_url or target.requested_url
    path = unquote(urlsplit(url).path)
    return re.sub(r"[-_/]+", " ", path).casefold()


def _target_intent(target: PageEvidence) -> str:
    """Classify the destination while keeping URL words as supporting evidence only."""
    primary = " ".join([target.title, target.h1, *target.headings[:12]]).casefold()
    body = target.text[:12000].casefold()
    url_text = _target_url_text(target)
    ranked: list[tuple[float, int, str]] = []
    for priority, (kind, signals) in enumerate(_TARGET_TYPE_SIGNALS):
        primary_hits = sum(_contains_term(primary, term) for term in signals)
        body_hits = sum(_contains_term(body, term) for term in signals)
        url_hits = sum(_contains_term(url_text, term) for term in signals)
        # Page copy is authoritative. A URL clue can break a close tie or classify an
        # otherwise ambiguous page, but cannot overrule clear on-page evidence.
        score = (5.0 * primary_hits) + (1.5 * body_hits) + (0.5 * url_hits)
        ranked.append((score, -priority, kind))
    score, _, kind = max(ranked)
    return kind if score > 0 else "general"


def _target_audience(target: PageEvidence) -> str | None:
    """Return an audience only when the destination explicitly identifies one."""
    primary = " ".join([target.title, target.h1])
    profile = _target_profile(target)
    cues = (
        "for",
        "designed for",
        "built for",
        "created for",
        "developed for",
        "intended for",
        "ideal for",
        "suitable for",
        "aimed at",
        "who should attend",
        "who is this for",
        "helps",
        "supports",
    )
    for audience, variants in _TARGET_AUDIENCES:
        for variant in variants:
            # An audience in a title or heading is an explicit positioning signal.
            if _contains_term(primary, variant):
                return audience
            # In body copy, require audience-directed language so a passing mention
            # does not become an unsupported claim about whom the page serves.
            cue_pattern = "|".join(re.escape(cue) for cue in cues)
            if re.search(
                rf"(?:{cue_pattern})\s+(?:aspiring\s+|experienced\s+|current\s+|future\s+)?{re.escape(variant)}(?!\w)",
                profile,
                flags=re.IGNORECASE,
            ):
                return audience
    return None


def _audience_subject(audience: str) -> str:
    """Uppercase a sentence-initial audience without damaging acronyms such as SEO."""
    return audience[:1].upper() + audience[1:]


def _context_kind(text: str) -> str:
    lower = text.casefold()
    groups = (
        ("application", ("application", "use case", "workflow", "agent", "automation", "transaction", "accounting", "operation")),
        ("skills", ("skill", "career", "professional", "learn", "training", "education", "knowledge")),
        ("implementation", ("implement", "integrat", "deploy", "build", "system", "architecture", "infrastructure")),
        ("cost", ("cost", "price", "pricing", "budget", "expense", "roi", "investment")),
        ("governance", ("risk", "governance", "compliance", "security", "privacy", "audit")),
    )
    for kind, markers in groups:
        if any(marker in lower for marker in markers):
            return kind
    return "general"


def _sentence_spans(paragraph: str) -> list[tuple[int, int, str]]:
    """Split prose conservatively while retaining exact offsets and punctuation."""
    boundaries = list(re.finditer(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\u201c\u2018])", paragraph))
    starts = [0, *(match.end() for match in boundaries)]
    ends = [*(match.start() for match in boundaries), len(paragraph)]
    return [(start, end, paragraph[start:end]) for start, end in zip(starts, ends) if paragraph[start:end].strip()]


def _meaningful_overlap(sentence: str, target: PageEvidence, anchor: str) -> int:
    sentence_terms = _stems(sentence)
    target_terms = _stems(_target_profile(target))
    anchor_terms = _stems(anchor)
    return len(sentence_terms & (target_terms - anchor_terms))


def _rewrite_candidate(
    paragraph: str,
    anchor: str,
    target_url: str,
    target: PageEvidence,
) -> tuple[str, str, list[TextSegment], str, list[str]] | None:
    """Integrate an anchor into one supported sentence without replacing source words."""
    intent = _target_intent(target)
    if intent not in {"learning", "service", "implementation", "guide", "governance"}:
        return None

    ranked: list[tuple[int, float, int, int, str]] = []
    for start, end, sentence in _sentence_spans(paragraph):
        overlap = _meaningful_overlap(sentence, target, anchor)
        kind = _context_kind(sentence)
        if overlap < 2 or kind not in {"application", "skills", "implementation"}:
            continue
        ranked.append((overlap, similarity(sentence, _target_profile(target)), start, end, kind))
    if not ranked:
        return None

    _, _, start, end, kind = max(ranked, key=lambda item: (item[0], item[1], -item[2]))
    sentence = paragraph[start:end]
    stripped = sentence.rstrip()
    terminal = stripped[-1] if stripped and stripped[-1] in ".!?" else "."
    sentence_body = stripped[:-1] if stripped and stripped[-1] in ".!?" else stripped
    sentence_body = sentence_body.rstrip()

    placed_anchor = _fallback_anchor_case(anchor)
    linked_phrase = _anchor_with_article(placed_anchor)
    anchor_offset = linked_phrase.rfind(placed_anchor)
    article_prefix = linked_phrase[:anchor_offset]
    audience = _target_audience(target)
    if intent == "learning" and kind == "application":
        descriptor, active, passive = "a practical application", "examine more deeply", "examined more deeply"
    elif intent == "learning" and kind == "skills":
        descriptor, active, passive = "a topic", "study more deeply", "studied more deeply"
    elif intent in {"service", "implementation"}:
        descriptor, active, passive = "an approach", "explore further", "explored further"
    elif intent == "governance":
        descriptor, active, passive = "a consideration", "examine further", "examined further"
    else:
        descriptor, active, passive = "a topic", "explore further", "explored further"
    if audience:
        clause = f", {descriptor} {audience} can {active} through "
    else:
        clause = f", {descriptor} that can be {passive} through "

    prefix = paragraph[:start] + sentence_body + clause + article_prefix
    suffix = terminal + sentence[len(stripped) :] + paragraph[end:]
    after_text = prefix + placed_anchor + suffix
    after = prefix + f"[{placed_anchor}]({target_url})" + suffix
    notes = [
        "source_sentence_lightly_rewritten",
        "publisher_meaning_preserved",
        "target_title_not_injected_into_source_copy",
        "destination_intent_used_for_contextual_sentence",
    ]
    notes.append(
        "target_audience_used_for_contextual_sentence"
        if audience
        else "neutral_audience_wording_used"
    )
    if placed_anchor != anchor:
        notes.append("anchor_casing_adapted_for_generated_sentence")
    return after, after_text, _segments(prefix, placed_anchor, target_url, suffix), placed_anchor, notes


def _contextual_fallback_sentence(
    paragraph: str,
    anchor: str,
    target: PageEvidence,
) -> tuple[str, str, str, list[str]]:
    """Create concise deterministic fallback copy without dumping the target title."""
    placed_anchor = _fallback_anchor_case(anchor)
    intent = _target_intent(target)
    audience = _target_audience(target)
    context = _context_kind(paragraph)
    paragraph_lower = paragraph.lower()

    cost_intent = intent == "cost"
    cost_context = any(term in paragraph_lower for term in ("cost", "price", "pricing", "budget", "expense", "roi", "investment", "expensive"))

    notes: list[str] = ["target_title_not_injected_into_source_copy"]
    if placed_anchor != anchor:
        notes.append("anchor_casing_adapted_for_generated_sentence")

    if cost_intent and cost_context:
        notes.extend(["destination_intent_used_for_contextual_sentence", "neutral_audience_wording_used"])
        return (
            "These factors are useful when estimating ",
            " implementation costs, ongoing operating expenses, and expected ROI.",
            placed_anchor,
            notes,
        )

    if cost_intent:
        notes.extend(["destination_intent_used_for_contextual_sentence", "neutral_audience_wording_used"])
        return (
            "Evaluating this type of automation requires accounting for ",
            " costs, including implementation, integrations, ongoing operation, and expected ROI.",
            placed_anchor,
            notes,
        )

    anchor_phrase = _anchor_with_article(placed_anchor)
    anchor_offset = anchor_phrase.rfind(placed_anchor)
    article_prefix = anchor_phrase[:anchor_offset]
    if intent == "learning" and context == "application":
        notes.append("destination_intent_used_for_contextual_sentence")
        if audience:
            notes.append("target_audience_used_for_contextual_sentence")
            return (
                f"{_audience_subject(audience)} can examine these applications more deeply through {article_prefix}",
                ".",
                placed_anchor,
                notes,
            )
        notes.append("neutral_audience_wording_used")
        return (
            f"These applications can be examined more deeply through {article_prefix}",
            ".",
            placed_anchor,
            notes,
        )

    if intent == "learning" and context == "skills":
        notes.append("destination_intent_used_for_contextual_sentence")
        if audience:
            notes.append("target_audience_used_for_contextual_sentence")
            return (
                f"{_audience_subject(audience)} can develop these skills further through {article_prefix}",
                ".",
                placed_anchor,
                notes,
            )
        notes.append("neutral_audience_wording_used")
        return (
            f"These skills can be developed further through {article_prefix}",
            ".",
            placed_anchor,
            notes,
        )

    if intent == "learning":
        notes.append("destination_intent_used_for_contextual_sentence")
        if audience:
            notes.append("target_audience_used_for_contextual_sentence")
            return (
                f"{_audience_subject(audience)} can explore this subject further through {article_prefix}",
                ".",
                placed_anchor,
                notes,
            )
        notes.append("neutral_audience_wording_used")
        return (
            f"This subject can be explored further through {article_prefix}",
            ".",
            placed_anchor,
            notes,
        )

    if intent in {"service", "implementation"}:
        notes.extend(["destination_intent_used_for_contextual_sentence", "neutral_audience_wording_used"])
        return (
            f"Practical implementation guidance for similar approaches is available through {article_prefix}",
            ".",
            placed_anchor,
            notes,
        )

    if intent == "governance":
        notes.extend(["destination_intent_used_for_contextual_sentence", "neutral_audience_wording_used"])
        return (
            f"The related safeguards can be examined further through {article_prefix}",
            ".",
            placed_anchor,
            notes,
        )

    if intent == "guide":
        notes.extend(["destination_intent_used_for_contextual_sentence", "neutral_audience_wording_used"])
        return (
            f"Additional guidance on this topic is available through {article_prefix}",
            ".",
            placed_anchor,
            notes,
        )

    notes.append("neutral_audience_wording_used")
    return (
        f"An additional point of reference is available through {article_prefix}",
        ".",
        placed_anchor,
        notes,
    )


def _segments(prefix: str, anchor: str, target_url: str, suffix: str) -> list[TextSegment]:
    segments: list[TextSegment] = []
    if prefix:
        segments.append(TextSegment(type="text", text=prefix))
    segments.append(TextSegment(type="link", text=anchor, url=target_url))
    if suffix:
        segments.append(TextSegment(type="text", text=suffix))
    return segments


def _compose_after(
    paragraph: str,
    anchor: str,
    target_url: str,
    target: PageEvidence,
) -> tuple[str, str, str, list[TextSegment], str, list[str]]:
    """Compose the draft while preserving source grammar/capitalization when possible."""
    exact = _find_complete_phrase(paragraph, anchor)
    if exact is not None:
        placed_anchor = exact.group(0)
        linked = f"[{placed_anchor}]({target_url})"
        after = paragraph[: exact.start()] + linked + paragraph[exact.end() :]
        after_text = paragraph
        segments = _segments(
            paragraph[: exact.start()], placed_anchor, target_url, paragraph[exact.end() :]
        )
        notes: list[str] = []
        if placed_anchor != anchor:
            notes.append("source_anchor_capitalization_preserved")
        return "minimal_insertion", after, after_text, segments, placed_anchor, notes

    # If the exact requested form is not present, prefer a complete natural word-form
    # already in the publisher copy instead of creating artifacts such as [AI Agent]s.
    for variant in _simple_anchor_variants(anchor):
        match = _find_complete_phrase(paragraph, variant)
        if match is not None:
            placed_anchor = match.group(0)
            linked = f"[{placed_anchor}]({target_url})"
            after = paragraph[: match.start()] + linked + paragraph[match.end() :]
            after_text = paragraph
            segments = _segments(
                paragraph[: match.start()], placed_anchor, target_url, paragraph[match.end() :]
            )
            return (
                "minimal_insertion",
                after,
                after_text,
                segments,
                placed_anchor,
                ["anchor_adapted_to_source_grammar", "requested_anchor_not_used_verbatim"],
            )

    rewrite = _rewrite_candidate(paragraph, anchor, target_url, target)
    if rewrite is not None:
        after, after_text, segments, placed_anchor, notes = rewrite
        return "contextual_sentence", after, after_text, segments, placed_anchor, notes

    sentence_prefix, sentence_suffix, placed_anchor, notes = _contextual_fallback_sentence(
        paragraph, anchor, target
    )
    prefix = paragraph.rstrip() + " " + sentence_prefix
    after_text = prefix + placed_anchor + sentence_suffix
    after = prefix + f"[{placed_anchor}]({target_url})" + sentence_suffix
    return (
        "contextual_sentence",
        after,
        after_text,
        _segments(prefix, placed_anchor, target_url, sentence_suffix),
        placed_anchor,
        notes,
    )


def _preservation_percent(before: str, after: str) -> float:
    """Calculate how many original word tokens remain in the recommended text."""
    before_words = re.findall(r"\w+(?:[+#-]\w+)*", before.casefold(), flags=re.UNICODE)
    after_words = re.findall(r"\w+(?:[+#-]\w+)*", after.casefold(), flags=re.UNICODE)
    if not before_words:
        return 100.0
    retained = sum((Counter(before_words) & Counter(after_words)).values())
    return round(min(100.0, 100.0 * retained / len(before_words)), 1)


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
    min_context_score: float = 0.0,
    min_destination_score: float = 0.0,
) -> list[PlacementSuggestion]:
    if source.status_code != 200 or target.status_code != 200:
        return []

    anchor, anchor_warnings = _select_anchor(preferred_anchor, target.title)
    target_profile = _target_profile(target)
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
        if score >= min_context_score and destination_score >= min_destination_score:
            candidates.append((score, destination_score, i, paragraph))

    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    suggestions: list[PlacementSuggestion] = []
    for rank, (score, destination_score, index, paragraph) in enumerate(candidates[: max(top_n, 1)], start=1):
        strategy, after, after_text, after_segments, placed_anchor, compose_notes = _compose_after(
            paragraph, anchor, target_url, target
        )
        original_words = max(len(paragraph.split()), 1)
        after_words = len(after_text.split())
        added = max(after_words - original_words, 0)
        preservation = _preservation_percent(paragraph, after_text)
        warnings = list(anchor_warnings)
        reasons = ["paragraph_has_strong_target_similarity"] if score >= 0.25 else ["best_available_context_match"]
        is_rewrite = "source_sentence_lightly_rewritten" in compose_notes
        if strategy == "minimal_insertion":
            reasons.append("anchor_already_present_in_original_copy")
        elif not is_rewrite:
            reasons.append("publisher_copy_preserved")
        for note in compose_notes:
            if note == "requested_anchor_not_used_verbatim":
                warnings.append(note)
            else:
                reasons.append(note)
        if destination_score >= 0.14:
            reasons.append("strong_destination_intent_alignment")
        context_level = "very_high" if score >= 0.48 else "high" if score >= 0.30 else "medium" if score >= 0.15 else "low"
        intervention = _intervention(preservation, added)
        if is_rewrite and intervention == "low":
            intervention = "medium"
        near_threshold = (
            score < min_context_score + 0.05
            or destination_score < min_destination_score + 0.03
        )
        review_required = bool(
            strategy != "minimal_insertion"
            or warnings
            or intervention != "low"
            or near_threshold
        )
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
                after_text=after_text,
                after_segments=after_segments,
                added_words=added,
                preservation_percent=preservation,
                intervention=intervention,
                recommendation_status="manual_review" if review_required else "recommended",
                review_required=review_required,
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
