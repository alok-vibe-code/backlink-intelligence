"""Command-line entry point for the Backlink Intelligence foundation."""

from __future__ import annotations

import argparse

from backlink_intelligence import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backlink-intelligence",
        description=(
            "Evidence-first backlink intelligence for auditing, qualification, "
            "contextual placement, and monitoring."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "status",
        help="Show the current implementation status and next planned release.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        print("Backlink Intelligence foundation is installed.")
        print("Current version: 0.0.1 (pre-alpha foundation)")
        print("Next milestone: v0.1.0 Backlink Evidence Auditor")
        print("Planned workflow: Discover -> Qualify -> Place -> Monitor")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
