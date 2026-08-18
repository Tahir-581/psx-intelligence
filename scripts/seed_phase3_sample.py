#!/usr/bin/env python3
"""Bootstrap Phase 3 sample data: extractors, news backfill, macro seed, sector stats."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Phase 3 context layer sample data")
    parser.add_argument("--skip-news", action="store_true")
    args = parser.parse_args()

    from scrapers.macro.run import run_scrape_macro
    from scrapers.psx.extract_corporate_actions import run_extract_corporate_actions
    from scrapers.psx.extract_material_events import run_extract_material_events
    from backend.services.sector import run_refresh_sector_stats

    print("Extracting corporate actions...")
    print(run_extract_corporate_actions(limit=5000))

    print("Extracting material events...")
    print(run_extract_material_events(limit=5000))

    if not args.skip_news:
        from scrapers.news.run import run_backfill_news

        print("Backfilling news...")
        print(run_backfill_news(days=30, sources=["business_recorder", "dawn"]))

    print("Seeding macro...")
    print(run_scrape_macro())

    print("Refreshing sector stats...")
    print(run_refresh_sector_stats())


if __name__ == "__main__":
    main()
