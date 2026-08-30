from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


def classify_anchor(anchor: str, target_url: str = "") -> str:
    anchor = (anchor or "").strip()
    if not anchor: return "empty"
    lower = anchor.lower()
    if lower.startswith("http://") or lower.startswith("https://") or lower.startswith("www."): return "naked_url"
    if lower in {"click here", "here", "website", "this page", "learn more", "read more", "source"}: return "generic"
    host = (urlparse(target_url).hostname or "").lower().removeprefix("www."); brand = host.split(".")[0].replace("-", " ") if host else ""
    if brand and brand in lower: return "branded"
    return "exact_or_commercial" if len(lower.split()) <= 5 else "descriptive"


def analyze_portfolio(input_path: str | Path) -> dict:
    anchors: Counter[str] = Counter(); destinations: Counter[str] = Counter(); placements: Counter[str] = Counter(); total = 0
    with Path(input_path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if "target_url" not in (reader.fieldnames or []): raise ValueError("CSV must contain target_url.")
        for row in reader:
            total += 1; target = row.get("target_url", "").strip(); anchor = row.get("anchor", row.get("expected_anchor", "")).strip(); placement = row.get("placement", "unknown").strip() or "unknown"
            anchors[classify_anchor(anchor, target)] += 1; destinations[target or "unknown"] += 1; placements[placement] += 1
    return {"total_links": total, "anchor_distribution": dict(anchors.most_common()), "destination_distribution": dict(destinations.most_common()), "placement_distribution": dict(placements.most_common())}
