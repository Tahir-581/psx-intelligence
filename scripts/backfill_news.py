#!/usr/bin/env python3
"""Backfill news from RSS sources."""

import argparse

from scrapers.news.run import run_backfill_news


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit-sources", type=str, default=None)
    args = parser.parse_args()
    sources = (
        [s.strip() for s in args.limit_sources.split(",")] if args.limit_sources else None
    )
    result = run_backfill_news(days=args.days, sources=sources)
    print(result)


if __name__ == "__main__":
    main()
