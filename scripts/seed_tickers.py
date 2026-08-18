#!/usr/bin/env python3
"""Seed PSX ticker universe into the database."""

import sys

from scrapers.psx.tickers import run_scrape_tickers


def main() -> int:
    result = run_scrape_tickers()
    print(f"Seeded {result['ingested']} tickers ({result['total_symbols']} equity symbols)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
