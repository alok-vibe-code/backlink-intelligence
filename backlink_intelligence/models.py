from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PageLink:
    href: str
    text: str
    rel: tuple[str, ...] = ()
    context: str = ""
    paragraph: str = ""
    placement: str = "unknown"

    @property
    def is_nofollow(self) -> bool:
        return "nofollow" in self.rel

    @property
    def is_sponsored(self) -> bool:
        return "sponsored" in self.rel

    @property
    def is_ugc(self) -> bool:
        return "ugc" in self.rel


@dataclass(slots=True)
class PageEvidence:
    requested_url: str
    final_url: str
    status_code: int
    title: str = ""
    h1: str = ""
    canonical: str = ""
    robots: tuple[str, ...] = ()
    text: str = ""
    paragraphs: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    links: list[PageLink] = field(default_factory=list)
    word_count: int = 0
    error: str = ""

    @property
    def is_indexable(self) -> bool:
        blocked = {"noindex", "none"}
        return self.status_code == 200 and not any(v in blocked for v in self.robots)


@dataclass(slots=True)
class BacklinkEvidence:
    found: bool
    source_url: str
    target_url: str
    anchor: str = ""
    rel: tuple[str, ...] = ()
    context: str = ""
    paragraph: str = ""
    placement: str = "unknown"


@dataclass(slots=True)
class RelevanceEvidence:
    page_similarity: float
    context_similarity: float
    title_similarity: float
    heading_similarity: float
    level: str
    shared_terms: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OutboundEvidence:
    total_links: int
    external_links: int
    unique_external_domains: int
    external_links_per_1000_words: float
    follow_links: int
    nofollow_links: int
    sponsored_links: int
    ugc_links: int
    review_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AuditResult:
    source: PageEvidence
    target: PageEvidence
    backlink: BacklinkEvidence
    relevance: RelevanceEvidence
    outbound: OutboundEvidence
    recommendation: str
    confidence: str
    reasons: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlacementSuggestion:
    rank: int
    paragraph_index: int
    score: float
    context_level: str
    destination_score: float
    destination_fit: str
    requested_anchor: str
    suggested_anchor: str
    strategy: str
    before: str
    after: str
    added_words: int
    preservation_percent: float
    intervention: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MonitorSnapshot:
    source_url: str
    target_url: str
    source_status: int
    target_status: int
    link_found: bool
    anchor: str
    rel: tuple[str, ...]
    placement: str
    source_canonical: str
    source_robots: tuple[str, ...]
    checked_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
