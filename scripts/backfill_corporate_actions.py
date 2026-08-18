#!/usr/bin/env python3
"""Backfill corporate actions from existing announcements."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill corporate actions from announcements")
    parser.add_argument("--limit", type=int, default=None, help="Max announcements to process")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols")
    args = parser.parse_args()

    from scrapers.psx.extract_corporate_actions import run_extract_corporate_actions

    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else None
    result = run_extract_corporate_actions(symbols=symbols, limit=args.limit)
    print(result)


if __name__ == "__main__":
    main()
