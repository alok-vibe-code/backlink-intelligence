from __future__ import annotations

import csv
import time
from pathlib import Path

from .fetcher import FetchConfig, fetch_page
from .link_analysis import outbound_evidence
from .models import PageEvidence
from .placement import rank_placements
from .relevance import analyze_relevance


def _qualify_pages(source: PageEvidence, target: PageEvidence, source_url: str, target_url: str, preferred_anchor: str) -> dict:
    relevance = analyze_relevance(source, target)
    outbound = outbound_evidence(source)
    placements = rank_placements(source, target, preferred_anchor, target_url, top_n=1)
    placement_score = placements[0].score if placements else 0.0
    flags = list(outbound.review_flags)
    if not source.is_indexable:
        flags.append("source_not_indexable")
    if source.status_code != 200:
        flags.append("source_unavailable")
    if target.status_code != 200:
        flags.append("target_unavailable")
    if source.status_code == 200 and target.status_code == 200 and relevance.level in {"high", "very_high"} and placement_score >= 0.18 and len(flags) <= 1:
        recommendation = "prioritize"
    elif source.status_code != 200 or relevance.level == "low" or "source_not_indexable" in flags:
        recommendation = "low_priority"
    else:
        recommendation = "manual_review"
    confidence = "high" if source.status_code == 200 and target.status_code == 200 else "low"
    return {"source_url": source_url, "target_url": target_url, "preferred_anchor": preferred_anchor, "source_status": source.status_code, "target_status": target.status_code, "source_indexable": source.is_indexable, "page_relevance": relevance.level, "page_similarity": relevance.page_similarity, "title_similarity": relevance.title_similarity, "placement_potential": placements[0].context_level if placements else "unknown", "placement_score": placement_score, "external_links": outbound.external_links, "unique_external_domains": outbound.unique_external_domains, "external_links_per_1000_words": outbound.external_links_per_1000_words, "review_flags": ";".join(sorted(set(flags))), "recommendation": recommendation, "confidence": confidence}


def qualify_prospect(source_url: str, target_url: str, preferred_anchor: str = "", config: FetchConfig | None = None) -> dict:
    return _qualify_pages(fetch_page(source_url, config), fetch_page(target_url, config), source_url, target_url, preferred_anchor)


def qualify_csv(input_path: str | Path, output_path: str | Path, config: FetchConfig | None = None, *, delay_seconds: float = 0.5) -> list[dict]:
    rows: list[dict] = []
    cache: dict[str, PageEvidence] = {}
    def cached(url: str) -> PageEvidence:
        if url not in cache:
            cache[url] = fetch_page(url, config)
        return cache[url]
    with Path(input_path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"source_url", "target_url"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")
        for row in reader:
            source_url = row.get("source_url", "").strip()
            target_url = row.get("target_url", "").strip()
            preferred_anchor = row.get("preferred_anchor", "").strip()
            rows.append(_qualify_pages(cached(source_url), cached(target_url), source_url, target_url, preferred_anchor))
            if delay_seconds > 0:
                time.sleep(delay_seconds)
    if rows:
        with Path(output_path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader(); writer.writerows(rows)
    return rows
