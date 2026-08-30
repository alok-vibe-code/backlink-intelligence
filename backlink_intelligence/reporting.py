from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def jsonable(value: Any) -> Any:
    if is_dataclass(value): return asdict(value)
    if isinstance(value, tuple): return list(value)
    return value


def write_json(data: Any, path: str | Path | None = None) -> str:
    text = json.dumps(data, indent=2, ensure_ascii=False, default=jsonable)
    if path: Path(path).write_text(text + "\n", encoding="utf-8")
    return text


def audit_text(result) -> str:
    backlink = result.backlink
    lines = ["BACKLINK INTELLIGENCE AUDIT", "", f"Source status:       {result.source.status_code}", f"Target status:       {result.target.status_code}", f"Link found:          {'Yes' if backlink.found else 'No'}", f"Anchor:              {backlink.anchor or '-'}", f"Rel attributes:      {' '.join(backlink.rel) or 'follow/default'}", f"Placement:           {backlink.placement}", f"Source indexable:    {'Yes' if result.source.is_indexable else 'No'}", f"Page relevance:      {result.relevance.level}", f"Page similarity:     {result.relevance.page_similarity:.3f}", f"Context similarity:  {result.relevance.context_similarity:.3f}", f"External links:      {result.outbound.external_links}", f"External domains:    {result.outbound.unique_external_domains}", f"Recommendation:      {result.recommendation}", f"Confidence:          {result.confidence}"]
    if result.reasons: lines.extend(["", "Evidence:", *[f"  + {v}" for v in result.reasons]])
    if result.concerns: lines.extend(["", "Review flags:", *[f"  ! {v}" for v in result.concerns]])
    return "\n".join(lines)
