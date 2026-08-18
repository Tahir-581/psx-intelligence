#!/usr/bin/env python3
"""Full-universe fundamentals backfill: announcements → PDF parse → ratio recompute."""

import argparse
import json
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from backend.config import settings
from backend.models.price import Price
from backend.models.ticker import Ticker
from backend.services.ratios import run_recompute_ratios
from scrapers.psx.announcements import run_backfill_symbol_announcements
from scrapers.psx.eod_prices import run_backfill_symbol
from scrapers.psx.parse_pdfs import run_parse_pending_pdfs, run_reparse_financial_pdfs

CHECKPOINT_FILE = Path(__file__).parent / ".backfill_fundamentals_checkpoint.json"
DEFAULT_DELAY = settings.psx_request_delay_seconds
INDEX_SYMBOLS = ["KSE100", "KSE30", "KMI30"]
MIN_INDEX_BARS = 30


def load_checkpoint() -> set[str]:
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return set(data.get("announcements_completed", []))
    return set()


def save_checkpoint(completed: set[str]) -> None:
    CHECKPOINT_FILE.write_text(
        json.dumps({"announcements_completed": sorted(completed)}, indent=2),
        encoding="utf-8",
    )


def get_symbols(limit: int | None = None) -> list[str]:
    engine = create_engine(settings.database_url_sync)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        query = (
            select(Ticker.symbol)
            .where(Ticker.is_active.is_(True), Ticker.is_debt.is_(False))
            .order_by(Ticker.symbol)
        )
        symbols = list(session.scalars(query))
    if limit:
        symbols = symbols[:limit]
    return symbols


def ensure_index_prices(years: int = 2, dry_run: bool = False) -> dict[str, dict]:
    engine = create_engine(settings.database_url_sync)
    Session = sessionmaker(bind=engine)
    results: dict[str, dict] = {}
    with Session() as session:
        for symbol in INDEX_SYMBOLS:
            count = session.scalar(
                select(func.count()).select_from(Price).where(Price.symbol == symbol)
            ) or 0
            if count >= MIN_INDEX_BARS:
                results[symbol] = {"skipped": True, "bars": count}
                continue
            if dry_run:
                results[symbol] = {"dry_run": True, "bars": count}
                continue
            bars = run_backfill_symbol(symbol, years=years)
            results[symbol] = {"backfilled": True, "bars": bars}
    return results


def backfill_announcements(
    symbols: list[str],
    *,
    delay: float,
    dry_run: bool,
    completed: set[str],
) -> None:
    pending = [symbol for symbol in symbols if symbol not in completed]
    print(f"Backfilling announcements for {len(pending)} symbols...", flush=True)
    for i, symbol in enumerate(pending, 1):
        if dry_run:
            print(f"[{i}/{len(pending)}] {symbol}: dry-run skip")
            continue
        try:
            count = run_backfill_symbol_announcements(symbol)
            completed.add(symbol)
            save_checkpoint(completed)
            print(f"[{i}/{len(pending)}] {symbol}: {count} new announcements")
        except Exception as exc:
            print(f"[{i}/{len(pending)}] {symbol}: FAILED - {exc}")
        time.sleep(delay)


def reparse_all_financials(batch_size: int, dry_run: bool) -> dict:
    total_ingested = 0
    total_processed = 0
    rounds = 0
    if dry_run:
        print("Dry-run: skipping financial reparse loop")
        return {"ingested": 0, "processed": 0, "rounds": 0}

    while True:
        result = run_reparse_financial_pdfs(limit=batch_size)
        ingested = result.get("ingested", 0)
        processed = result.get("processed", 0)
        total_ingested += ingested
        total_processed += processed
        rounds += 1
        print(
            f"Reparse round {rounds}: processed={processed}, ingested={ingested}, "
            f"skipped={result.get('skipped', 0)}"
        )
        if processed == 0:
            break
    return {"ingested": total_ingested, "processed": total_processed, "rounds": rounds}


def parse_all_pdfs(batch_size: int, dry_run: bool) -> dict:
    total_ingested = 0
    total_processed = 0
    rounds = 0
    if dry_run:
        print("Dry-run: skipping PDF parse loop")
        return {"ingested": 0, "processed": 0, "rounds": 0}

    while True:
        result = run_parse_pending_pdfs(limit=batch_size)
        ingested = result.get("ingested", 0)
        processed = result.get("processed", 0)
        total_ingested += ingested
        total_processed += processed
        rounds += 1
        print(f"Parse round {rounds}: processed={processed}, ingested={ingested}")
        if processed == 0:
            break
    return {"ingested": total_ingested, "processed": total_processed, "rounds": rounds}


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill PSX fundamentals for screener ratios")
    parser.add_argument("--limit-tickers", type=int, default=None)
    parser.add_argument("--resume", action="store_true", help="Resume announcements checkpoint")
    parser.add_argument("--skip-announcements", action="store_true")
    parser.add_argument("--parse-batch-size", type=int, default=50)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--price-years", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    symbols = get_symbols(args.limit_tickers)
    completed = load_checkpoint() if args.resume else set()

    print("Ensuring index price history for beta calculations...", flush=True)
    index_result = ensure_index_prices(years=args.price_years, dry_run=args.dry_run)
    for symbol, info in index_result.items():
        print(f"  {symbol}: {info}")

    if not args.skip_announcements:
        backfill_announcements(
            symbols,
            delay=args.delay,
            dry_run=args.dry_run,
            completed=completed,
        )
    else:
        print("Skipping announcements backfill.")

    print("Parsing pending PDFs (legacy parser pass)...")
    parse_result = parse_all_pdfs(args.parse_batch_size, args.dry_run)
    print(f"PDF parse complete: {parse_result}")

    print("Re-parsing financial PDFs with improved text extractor...")
    reparse_result = reparse_all_financials(args.parse_batch_size, args.dry_run)
    print(f"Financial reparse complete: {reparse_result}")

    if args.dry_run:
        print("Dry-run: skipping ratio recompute")
        return 0

    print("Recomputing ratios...")
    ratio_result = run_recompute_ratios()
    print(f"Ratio recompute complete: {ratio_result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
