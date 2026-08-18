#!/usr/bin/env python3
"""Backfill social posts from Twitter/Telegram/Reddit."""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill social posts")
    parser.add_argument("--source", choices=["twitter", "telegram", "reddit"], default="twitter")
    parser.add_argument("--days", type=int, default=7, help="Lookback days (Twitter recent search ~7d max)")
    parser.add_argument("--limit-symbols", type=int, default=20)
    args = parser.parse_args()

    if args.source == "twitter":
        from scrapers.social.run import run_twitter_scrape_standalone

        result = run_twitter_scrape_standalone(limit_symbols=args.limit_symbols)
        logger.info("Twitter backfill: %s", result)
    elif args.source == "telegram":
        from scrapers.social.run import run_telegram_scrape_standalone

        result = run_telegram_scrape_standalone()
        logger.info("Telegram backfill: %s", result)
    else:
        from scrapers.social.run import run_reddit_scrape_standalone

        result = run_reddit_scrape_standalone()
        logger.info("Reddit backfill: %s", result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
