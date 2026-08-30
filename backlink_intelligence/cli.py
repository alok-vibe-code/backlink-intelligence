"""Command-line interface for Backlink Intelligence."""

from __future__ import annotations

import argparse
import sys

from backlink_intelligence import __version__
from .audit import audit_backlink
from .monitor import monitor_csv
from .placement import suggest_placements
from .portfolio import analyze_portfolio
from .qualify import qualify_csv
from .reporting import audit_text, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backlink-intelligence",
        description=(
            "Evidence-first backlink intelligence for auditing, qualification, "
            "contextual placement, monitoring, and portfolio review."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show implementation status.")

    audit = sub.add_parser("audit", help="Audit an existing backlink.")
    audit.add_argument("source_url")
    audit.add_argument("target_url")
    audit.add_argument("--json", action="store_true", dest="as_json")
    audit.add_argument("--output", help="Optional JSON output file.")

    qualify = sub.add_parser("qualify", help="Qualify backlink prospects from CSV.")
    qualify.add_argument("input_csv")
    qualify.add_argument("--output", default="qualification-report.csv")
    qualify.add_argument("--delay", type=float, default=0.5, help="Delay between bulk rows in seconds.")

    place = sub.add_parser("place", help="Find contextual link placement opportunities.")
    place.add_argument("source_url")
    place.add_argument("target_url")
    place.add_argument("--anchor", required=True, help="Preferred anchor / keyword.")
    place.add_argument("--top", type=int, default=3)
    place.add_argument("--json", action="store_true", dest="as_json")
    place.add_argument("--output", help="Optional JSON output file.")

    monitor = sub.add_parser("monitor", help="Monitor backlinks listed in a CSV file.")
    monitor.add_argument("input_csv")
    monitor.add_argument("--state", default="backlink-state.json")
    monitor.add_argument("--output", default="monitor-report.csv")
    monitor.add_argument("--delay", type=float, default=0.5, help="Delay between monitoring rows in seconds.")

    portfolio = sub.add_parser("portfolio", help="Analyze anchor/destination/placement distributions.")
    portfolio.add_argument("input_csv")
    portfolio.add_argument("--output", help="Optional JSON output file.")

    return parser


def _placement_text(items) -> str:
    if not items:
        return "No suitable placement opportunities could be generated."
    chunks: list[str] = []
    for item in items:
        chunks.extend(
            [
                f"PLACEMENT OPPORTUNITY #{item.rank}",
                f"Paragraph:             {item.paragraph_index}",
                f"Context fit:           {item.context_level}",
                f"Similarity score:      {item.score:.3f}",
                f"Destination fit:       {item.destination_fit} ({item.destination_score:.3f})",
                f"Requested anchor:      {item.requested_anchor}",
                f"Placed anchor:         {item.suggested_anchor}",
                f"Strategy:              {item.strategy}",
                f"Editorial intervention:{item.intervention}",
                f"Text preservation:     {item.preservation_percent:.1f}%",
                "",
                "BEFORE",
                item.before,
                "",
                "AFTER",
                item.after,
            ]
        )
        if item.reasons:
            chunks.extend(["", "Why this placement:", *[f"  + {v}" for v in item.reasons]])
        if item.warnings:
            chunks.extend(["", "Review flags:", *[f"  ! {v}" for v in item.warnings]])
        chunks.extend(["", "-" * 72, ""])
    return "\n".join(chunks).rstrip()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "status":
            print("Backlink Intelligence is installed and functional.")
            print(f"Version: {__version__}")
            print("Available: audit, qualify, place, monitor, portfolio")
            print("Workflow: Discover -> Qualify -> Place -> Monitor -> Analyze")
            return 0

        if args.command == "audit":
            result = audit_backlink(args.source_url, args.target_url)
            if args.output:
                write_json(result.to_dict(), args.output)
            print(write_json(result.to_dict()) if args.as_json else audit_text(result))
            return 0 if result.source.status_code else 2

        if args.command == "qualify":
            rows = qualify_csv(args.input_csv, args.output, delay_seconds=args.delay)
            print(f"Qualified {len(rows)} prospect(s). Report: {args.output}")
            return 0

        if args.command == "place":
            items = suggest_placements(args.source_url, args.target_url, args.anchor, top_n=args.top)
            payload = [item.to_dict() for item in items]
            if args.output:
                write_json(payload, args.output)
            print(write_json(payload) if args.as_json else _placement_text(items))
            return 0 if items else 3

        if args.command == "monitor":
            rows = monitor_csv(args.input_csv, args.state, args.output, delay_seconds=args.delay)
            changed = sum("unchanged" not in row["changes"] and "baseline_created" not in row["changes"] for row in rows)
            print(f"Checked {len(rows)} link(s). Changed: {changed}. Report: {args.output}")
            return 0

        if args.command == "portfolio":
            result = analyze_portfolio(args.input_csv)
            text = write_json(result, args.output)
            print(text)
            return 0

        parser.print_help()
        return 0
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
