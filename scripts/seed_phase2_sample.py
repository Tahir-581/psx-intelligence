#!/usr/bin/env python3
"""Bootstrap Phase 2 sample data for local development."""

import sys

SAMPLE_SYMBOLS = ["ENGRO", "HBL", "OGDC", "LUCK", "PSO", "MCB", "FFC", "HUBC", "SYS", "MARI"]


def main() -> int:
    print("Phase 2 bootstrap: announcements backfill for sample tickers...")
    for symbol in SAMPLE_SYMBOLS:
        try:
            from scrapers.psx.announcements import run_backfill_symbol_announcements

            count = run_backfill_symbol_announcements(symbol)
            print(f"  {symbol}: {count} announcements ingested")
        except Exception as exc:
            print(f"  {symbol}: FAILED - {exc}")

    print("Parsing pending PDFs...")
    try:
        from scrapers.psx.parse_pdfs import run_parse_pending_pdfs

        result = run_parse_pending_pdfs(limit=30)
        print(f"  PDF parse: {result}")
    except Exception as exc:
        print(f"  PDF parse FAILED - {exc}")

    print("Recomputing ratios...")
    try:
        from backend.services.ratios import run_recompute_ratios

        result = run_recompute_ratios()
        print(f"  Ratios: {result}")
    except Exception as exc:
        print(f"  Ratios FAILED - {exc}")

    print("Done. Verify with: curl http://localhost:8000/ticker/ENGRO/announcements")
    return 0


if __name__ == "__main__":
    sys.exit(main())
