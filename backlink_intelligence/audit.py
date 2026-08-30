from __future__ import annotations

from .fetcher import FetchConfig, fetch_page
from .link_analysis import find_backlink, outbound_evidence
from .models import AuditResult
from .relevance import analyze_relevance


def _confidence(source_ok: bool, target_ok: bool, found: bool) -> str:
    score = int(source_ok) + int(target_ok) + int(found)
    return "high" if score == 3 else "medium" if score >= 2 else "low"


def _recommendation(found: bool, relevance: str, placement: str, concerns: list[str]) -> str:
    if not found:
        return "not_found"
    if "source_not_indexable" in concerns or "target_unavailable" in concerns:
        return "manual_review"
    if relevance in {"high", "very_high"} and placement == "editorial_context" and len(concerns) <= 1:
        return "strong_candidate"
    if relevance == "low" or placement in {"footer", "navigation"}:
        return "low_priority"
    return "manual_review"


def audit_backlink(source_url: str, target_url: str, config: FetchConfig | None = None) -> AuditResult:
    source = fetch_page(source_url, config)
    target = fetch_page(target_url, config)
    backlink = find_backlink(source, target_url)
    relevance = analyze_relevance(source, target, backlink.context)
    outbound = outbound_evidence(source)
    reasons: list[str] = []
    concerns: list[str] = list(outbound.review_flags)
    if backlink.found:
        reasons.append("target_link_found")
        if backlink.placement == "editorial_context":
            reasons.append("editorial_context_placement")
        if "nofollow" not in backlink.rel:
            reasons.append("link_is_followed")
    if relevance.level in {"high", "very_high"}:
        reasons.append("strong_topical_alignment")
    if source.is_indexable:
        reasons.append("source_indexable")
    else:
        concerns.append("source_not_indexable")
    if target.status_code != 200:
        concerns.append("target_unavailable")
    if "sponsored" in backlink.rel:
        concerns.append("sponsored_attribute_present")
    recommendation = _recommendation(backlink.found, relevance.level, backlink.placement, concerns)
    return AuditResult(source=source, target=target, backlink=backlink, relevance=relevance, outbound=outbound, recommendation=recommendation, confidence=_confidence(source.status_code == 200, target.status_code == 200, backlink.found), reasons=reasons, concerns=sorted(set(concerns)))
