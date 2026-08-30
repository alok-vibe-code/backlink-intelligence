from __future__ import annotations

import os
from dataclasses import dataclass, field

from .fetcher import FetchConfig, fetch_page
from .models import PageEvidence, PlacementSuggestion
from .placement import rank_placements
from .safety import validate_public_url


def _float_setting(
    name: str, default: float, minimum: float = 0.0, maximum: float = 1.0
) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if minimum <= value <= maximum else default


def _int_setting(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


@dataclass(slots=True)
class AnalysisConfig:
    min_context_score: float = 0.15
    min_destination_score: float = 0.08
    max_opportunities: int = 3
    fetch: FetchConfig = field(default_factory=FetchConfig)

    @classmethod
    def from_environment(cls) -> "AnalysisConfig":
        fetch = FetchConfig(
            connect_timeout=_float_setting("BI_CONNECT_TIMEOUT", 5.0, 1.0, 15.0),
            read_timeout=_float_setting("BI_READ_TIMEOUT", 12.0, 2.0, 30.0),
            max_compressed_bytes=_int_setting(
                "BI_MAX_COMPRESSED_BYTES", 1_000_000, 64_000, 2_000_000
            ),
            max_decompressed_bytes=_int_setting(
                "BI_MAX_DECOMPRESSED_BYTES", 2_000_000, 128_000, 4_000_000
            ),
            max_redirects=_int_setting("BI_MAX_REDIRECTS", 3, 0, 3),
        )
        return cls(
            min_context_score=_float_setting("BI_MIN_CONTEXT_SCORE", 0.15),
            min_destination_score=_float_setting("BI_MIN_DESTINATION_SCORE", 0.08),
            max_opportunities=_int_setting("BI_MAX_OPPORTUNITIES", 3, 1, 3),
            fetch=fetch,
        )


@dataclass(slots=True)
class PlacementAnalysis:
    status: str
    source: PageEvidence
    target: PageEvidence
    opportunities: list[PlacementSuggestion]
    analysis_warnings: list[str] = field(default_factory=list)


class PlacementAnalyzer:
    """One analysis service shared by the API and command-line interface."""

    def __init__(self, config: AnalysisConfig | None = None) -> None:
        self.config = config or AnalysisConfig.from_environment()

    def analyze(
        self,
        source_url: str,
        target_url: str,
        preferred_anchor: str,
        *,
        max_opportunities: int | None = None,
    ) -> PlacementAnalysis:
        source_url = validate_public_url(source_url, resolve_dns=False)
        target_url = validate_public_url(target_url, resolve_dns=False)
        source = fetch_page(source_url, self.config.fetch)
        target = fetch_page(target_url, self.config.fetch)
        if source.status_code != 200 or target.status_code != 200:
            return PlacementAnalysis(
                status="failed",
                source=source,
                target=target,
                opportunities=[],
            )

        top_n = self.config.max_opportunities
        if max_opportunities is not None:
            top_n = min(max(max_opportunities, 1), self.config.max_opportunities)
        opportunities = rank_placements(
            source,
            target,
            preferred_anchor,
            target_url,
            top_n=top_n,
            min_context_score=self.config.min_context_score,
            min_destination_score=self.config.min_destination_score,
        )
        warnings: list[str] = []
        if not source.is_indexable:
            warnings.append("source_page_is_not_indexable")
        if not target.is_indexable:
            warnings.append("target_page_is_not_indexable")
        return PlacementAnalysis(
            status="completed" if opportunities else "no_suitable_placement",
            source=source,
            target=target,
            opportunities=opportunities,
            analysis_warnings=warnings,
        )


def analyze_placement(
    source_url: str,
    target_url: str,
    preferred_anchor: str,
    *,
    config: AnalysisConfig | None = None,
) -> PlacementAnalysis:
    return PlacementAnalyzer(config).analyze(source_url, target_url, preferred_anchor)
