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


_PROFILE_BOILERPLATE_TERMS = {
    "academy",
    "certificate",
    "certification",
    "class",
    "course",
    "department",
    "degree",
    "education",
    "institute",
    "learn",
    "learning",
    "online",
    "offered",
    "program",
    "programme",
    "professional",
    "professionals",
    "school",
    "student",
    "students",
    "training",
    "university",
    "working",
}


def _unique_text(items: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = " ".join(item.split()).strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            output.append(value)
    return output


def _target_profile(target: PageEvidence) -> str:
    """Return the full cleaned page profile used by composition classifiers."""
    return " ".join(
        _unique_text([target.title, target.h1, *target.headings, *target.paragraphs])
    )[:12000]


def _target_topic_evidence(target: PageEvidence, anchor: str) -> tuple[str, list[str]]:
    """Build a compact topical profile without navigation or destination wrappers."""
    url_text = _target_url_text(target)
    boilerplate_terms = {_stem(term) for term in _PROFILE_BOILERPLATE_TERMS}
    anchor_subject_terms = _stems(anchor) - boilerplate_terms
    fallback_seed = " ".join([target.title, target.h1, url_text]).strip()
    subject_terms = anchor_subject_terms or (_stems(fallback_seed) - boilerplate_terms)
    if not subject_terms:
        subject_terms = _stems(anchor)
    seed = " ".join(sorted(subject_terms))

    headings = _unique_text(target.headings)
    paragraphs = _unique_text(target.paragraphs)

    def is_topical(value: str) -> bool:
        return bool(_stems(value) & subject_terms)

    ranked_headings = sorted(
        (
            (similarity(value, seed), index, value)
            for index, value in enumerate(headings)
            if len(value.split()) >= 3 and is_topical(value)
        ),
        key=lambda item: (-item[0], item[1]),
    )
    ranked_paragraphs = sorted(
        (
            (similarity(value, seed), index, value)
            for index, value in enumerate(paragraphs)
            if len(value.split()) >= 8 and is_topical(value)
        ),
        key=lambda item: (-item[0], item[1]),
    )

    selected_headings = [value for _, _, value in ranked_headings[:8]]
    selected_paragraphs = [value for _, _, value in ranked_paragraphs[:12]]
    topic_blocks = selected_paragraphs or selected_headings

    primary = [target.title]
    if is_topical(target.h1):
        primary.append(target.h1)
    profile_parts = _unique_text([*primary, url_text, *selected_headings, *selected_paragraphs])
    return " ".join(profile_parts), topic_blocks


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


def _sentence_function(text: str) -> str:
    """Classify what the publisher's sentence is doing, not merely its topic.

    This deliberately runs before broad topical markers such as ``agent``.  The old
    composer treated nearly every AI-agent sentence as an application and attached
    the same ``a practical application ...`` clause, even to definitions and
    evaluation criteria.
    """
    lower = " ".join(text.casefold().split())
    groups = (
        (
            "requirement",
            (
                " should ",
                " must ",
                " requires ",
                " require ",
                " needs ",
                " need ",
                "choosing ",
                "evaluating ",
                "consider ",
                "criteria",
                "right ",
            ),
        ),
        (
            "definition",
            (
                " is an ",
                " is a ",
                " are an ",
                " are a ",
                "refers to",
                "means ",
                "defined as",
            ),
        ),
        (
            "workflow",
            (
                "workflow",
                "process",
                "step",
                "retrieve",
                "monitor",
                "coordinate",
                "route",
                "interpret",
            ),
        ),
        (
            "benefit",
            ("benefit", "outcome", "improve", "reduce", "increase", "enable", "support"),
        ),
        (
            "application",
            ("application", "use case", "in practice", "perform", "automate", "apply"),
        ),
    )
    padded = f" {lower} "
    for function, markers in groups:
        if any(marker in padded for marker in markers):
            return function
    return "general"


def _audience_fits_source(audience: str | None, paragraph: str) -> bool:
    """Do not introduce an audience label that the publisher did not address."""
    return bool(audience and _contains_term(paragraph, audience))


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
    variant: int = 0,
) -> tuple[str, str, list[TextSegment], str, list[str]] | None:
    """Integrate an anchor into one supported sentence without replacing source words."""
    intent = _target_intent(target)
    if intent not in {"learning", "service", "implementation", "guide", "governance"}:
        return None

    ranked: list[tuple[int, float, int, int, str]] = []
    for start, end, sentence in _sentence_spans(paragraph):
        overlap = _meaningful_overlap(sentence, target, anchor)
        kind = _context_kind(sentence)
        function = _sentence_function(sentence)
        if (
            overlap < 2
            or start != 0
            or len(sentence.split()) > 18
            or kind not in {"application", "skills", "implementation"}
            or function in {"definition", "requirement"}
        ):
            continue
        ranked.append((overlap, similarity(sentence, _target_profile(target)), start, end, function))
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
        descriptor, active, passive = "an application", "examine in greater depth", "examined in greater depth"
    elif intent == "learning" and kind == "skills":
        descriptor, active, passive = "a topic", "study more deeply", "studied more deeply"
    elif intent in {"service", "implementation"}:
        descriptor, active, passive = "an approach", "explore further", "explored further"
    elif intent == "governance":
        descriptor, active, passive = "a consideration", "examine further", "examined further"
    else:
        descriptor, active, passive = "a topic", "explore further", "explored further"
    # Audience labels are not grammatical decorations.  They are used only when the
    # publisher already addresses the same audience; otherwise neutral copy is safer.
    use_audience = _audience_fits_source(audience, paragraph)
    neutral_clauses = (
        f", {descriptor} {passive} through ",
        f", an example explored in greater depth through ",
        f", a related concept covered in ",
    )
    if use_audience:
        clause = f", {descriptor} that {audience} can {active} through "
    else:
        clause = neutral_clauses[variant % len(neutral_clauses)]

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
        if use_audience
        else "neutral_audience_wording_used"
    )
    if placed_anchor != anchor:
        notes.append("anchor_casing_adapted_for_generated_sentence")
    return after, after_text, _segments(prefix, placed_anchor, target_url, suffix), placed_anchor, notes


def _contextual_fallback_sentence(
    paragraph: str,
    anchor: str,
    target: PageEvidence,
    variant: int = 0,
) -> tuple[str, str, str, list[str]]:
    """Create concise deterministic fallback copy without dumping the target title."""
    placed_anchor = _fallback_anchor_case(anchor)
    intent = _target_intent(target)
    audience = _target_audience(target)
    context = _context_kind(paragraph)
    function = _sentence_function(paragraph)
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
    sentence_article_prefix = article_prefix[:1].upper() + article_prefix[1:]
    use_audience = _audience_fits_source(audience, paragraph)

    if intent == "learning":
        notes.append("destination_intent_used_for_contextual_sentence")
        if use_audience:
            notes.append("target_audience_used_for_contextual_sentence")
            return (
                f"For {audience}, {article_prefix}",
                " provides a structured way to explore this subject in greater depth.",
                placed_anchor,
                notes,
            )

        notes.append("neutral_audience_wording_used")
        if function == "definition":
            options = (
                (
                    f"{sentence_article_prefix}",
                    " can provide additional context for how this technology works in practice.",
                ),
                (
                    "The role of this technology in agent systems can be explored further through " + article_prefix,
                    ".",
                ),
                (
                    f"{sentence_article_prefix}",
                    " can help connect this definition with practical agent workflows.",
                ),
            )
        elif function == "requirement":
            options = (
                (
                    f"{sentence_article_prefix}",
                    " can provide additional context for evaluating these requirements in practice.",
                ),
                (
                    "These criteria can also be examined through " + article_prefix,
                    ".",
                ),
                (
                    f"{sentence_article_prefix}",
                    " can help explain how these considerations affect real-world agent systems.",
                ),
            )
        elif function == "workflow" or context == "implementation":
            options = (
                (
                    f"{sentence_article_prefix}",
                    " can help explain how these workflows are designed and applied.",
                ),
                (
                    "These workflows can be studied in greater depth through " + article_prefix,
                    ".",
                ),
                (
                    f"{sentence_article_prefix}",
                    " offers a structured way to explore the methods behind these workflows.",
                ),
            )
        elif function == "benefit":
            options = (
                (
                    "The methods behind these outcomes can be studied further through " + article_prefix,
                    ".",
                ),
                (
                    f"{sentence_article_prefix}",
                    " can provide additional context for understanding these outcomes.",
                ),
                (
                    "The concepts supporting these benefits can be explored through " + article_prefix,
                    ".",
                ),
            )
        elif context == "skills":
            options = (
                ("These skills can be developed further through " + article_prefix, "."),
                (f"{sentence_article_prefix}", " can provide a structured path for developing these skills."),
                ("A deeper treatment of these capabilities is available through " + article_prefix, "."),
            )
        else:
            options = (
                (
                    f"{sentence_article_prefix}",
                    " can provide a structured way to explore how these concepts work in practice.",
                ),
                ("These concepts can be examined in greater depth through " + article_prefix, "."),
                (f"{sentence_article_prefix}", " offers additional context for applying these ideas."),
            )
        sentence_prefix, sentence_suffix = options[variant % len(options)]
        return (
            sentence_prefix,
            sentence_suffix,
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
    variant: int = 0,
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
    for anchor_variant in _simple_anchor_variants(anchor):
        match = _find_complete_phrase(paragraph, anchor_variant)
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

    rewrite = _rewrite_candidate(paragraph, anchor, target_url, target, variant)
    if rewrite is not None:
        after, after_text, segments, placed_anchor, notes = rewrite
        return "contextual_sentence", after, after_text, segments, placed_anchor, notes

    sentence_prefix, sentence_suffix, placed_anchor, notes = _contextual_fallback_sentence(
        paragraph, anchor, target, variant
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


def _destination_intent_score(
    paragraph: str,
    target: PageEvidence,
    anchor: str,
    topic_profile: str,
    topic_blocks: list[str],
) -> float:
    """Measure topical fit separately from the destination page's purpose."""
    profile_score = similarity(paragraph, topic_profile) if topic_profile else 0.0
    block_score = max((similarity(paragraph, block) for block in topic_blocks), default=0.0)
    topic_score = (0.70 * block_score) + (0.30 * profile_score)

    intent = _target_intent(target)
    if intent not in {"cost", "implementation", "governance"}:
        # Learning, guide, service, and general resources can support a paragraph that
        # shares their subject even when the source does not already mention a course,
        # guide, or service. Generated copy remains subject to editorial review.
        return round(topic_score, 4)

    signals = next(
        (values for kind, values in _TARGET_TYPE_SIGNALS if kind == intent),
        (),
    )
    paragraph_terms = _stems(paragraph)
    purpose_hits = sum(bool(paragraph_terms & _stems(value)) for value in signals)
    if purpose_hits == 0:
        # Specialized destinations need evidence of their specific purpose. This keeps
        # generic topical paragraphs from outranking pricing, implementation, or
        # governance context merely because they repeat the anchor.
        return round(topic_score * 0.35, 4)
    purpose_score = min(1.0, purpose_hits / 2.0)
    return round((0.70 * topic_score) + (0.30 * purpose_score), 4)


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
    target_profile, target_topic_blocks = _target_topic_evidence(target, anchor)
    candidates: list[tuple[float, float, int, str]] = []

    for i, paragraph in enumerate(source.paragraphs, start=1):
        wc = len(paragraph.split())
        if wc < 18 or wc > 260:
            continue
        # A standalone paragraph ending in a colon or semicolon normally introduces
        # a table or list. Treating it as complete prose produces malformed rewrites
        # and weak placements immediately before structured content.
        if paragraph.rstrip().endswith((":", ";")):
            continue
        semantic_score = similarity(paragraph, target_profile)
        destination_score = _destination_intent_score(
            paragraph,
            target,
            anchor,
            target_profile,
            target_topic_blocks,
        )
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
            paragraph, anchor, target_url, target, rank - 1
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
