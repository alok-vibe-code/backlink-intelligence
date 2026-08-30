from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .fetcher import FetchConfig, fetch_page
from .link_analysis import find_backlink
from .models import MonitorSnapshot, PageEvidence


def _snapshot_from_pages(source_url: str, target_url: str, source: PageEvidence, target: PageEvidence) -> MonitorSnapshot:
    backlink = find_backlink(source, target_url)
    return MonitorSnapshot(source_url=source_url, target_url=target_url, source_status=source.status_code, target_status=target.status_code, link_found=backlink.found, anchor=backlink.anchor, rel=backlink.rel, placement=backlink.placement, source_canonical=source.canonical, source_robots=source.robots, checked_at=datetime.now(timezone.utc).isoformat())


def snapshot_link(source_url: str, target_url: str, config: FetchConfig | None = None) -> MonitorSnapshot:
    return _snapshot_from_pages(source_url, target_url, fetch_page(source_url, config), fetch_page(target_url, config))


def compare_snapshots(old: dict | None, new: MonitorSnapshot, expected_anchor: str = "") -> list[str]:
    if old is None:
        return ["baseline_created"]
    changes: list[str] = []
    if bool(old.get("link_found")) and not new.link_found: changes.append("link_removed")
    if old.get("anchor", "") != new.anchor: changes.append("anchor_changed")
    if set(old.get("rel", [])) != set(new.rel): changes.append("rel_attributes_changed")
    if old.get("placement", "") != new.placement: changes.append("placement_changed")
    if old.get("source_status") != new.source_status: changes.append("source_status_changed")
    if old.get("target_status") != new.target_status: changes.append("target_status_changed")
    if old.get("source_canonical", "") != new.source_canonical: changes.append("canonical_changed")
    if set(old.get("source_robots", [])) != set(new.source_robots): changes.append("robots_changed")
    if expected_anchor and new.link_found and new.anchor != expected_anchor: changes.append("anchor_differs_from_expected")
    return changes or ["unchanged"]


def monitor_csv(input_path: str | Path, state_path: str | Path, output_path: str | Path, config: FetchConfig | None = None, *, delay_seconds: float = 0.5) -> list[dict]:
    state_file = Path(state_path)
    old_state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    results: list[dict] = []; new_state: dict[str, dict] = {}; cache: dict[str, PageEvidence] = {}
    def cached(url: str) -> PageEvidence:
        if url not in cache: cache[url] = fetch_page(url, config)
        return cache[url]
    with Path(input_path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"source_url", "target_url"}; missing = required - set(reader.fieldnames or [])
        if missing: raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")
        for row in reader:
            source_url = row.get("source_url", "").strip(); target_url = row.get("target_url", "").strip(); expected_anchor = row.get("expected_anchor", "").strip(); key = f"{source_url}|{target_url}"
            snap = _snapshot_from_pages(source_url, target_url, cached(source_url), cached(target_url)); changes = compare_snapshots(old_state.get(key), snap, expected_anchor); new_state[key] = snap.to_dict()
            results.append({"source_url": source_url, "target_url": target_url, "link_found": snap.link_found, "anchor": snap.anchor, "rel": " ".join(snap.rel), "placement": snap.placement, "source_status": snap.source_status, "target_status": snap.target_status, "changes": ";".join(changes), "checked_at": snap.checked_at})
            if delay_seconds > 0: time.sleep(delay_seconds)
    state_file.write_text(json.dumps(new_state, indent=2), encoding="utf-8")
    if results:
        with Path(output_path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(results[0].keys())); writer.writeheader(); writer.writerows(results)
    return results
