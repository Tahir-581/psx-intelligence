#!/usr/bin/env python3
"""Re-parse financial-result PDFs, including ones previously ingested with empty line items."""

import argparse

from scrapers.psx.parse_pdfs import run_reparse_financial_pdfs


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-parse PSX financial PDFs with improved parser")
    parser.add_argument("--symbols", nargs="*", help="Limit to specific symbols (e.g. FFC ENGRO)")
    parser.add_argument("--limit", type=int, default=None, help="Max announcements to scan")
    parser.add_argument("--force", action="store_true", help="Re-parse even when line items exist")
    args = parser.parse_args()

    result = run_reparse_financial_pdfs(
        symbols=args.symbols,
        limit=args.limit,
        force=args.force,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
