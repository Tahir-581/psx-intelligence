#!/usr/bin/env python3
"""Backfill historical EOD prices with checkpoint resume."""

import argparse
import json
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.config import settings
from backend.models.ticker import Ticker
from scrapers.psx.eod_prices import run_backfill_symbol

CHECKPOINT_FILE = Path(__file__).parent / ".backfill_checkpoint.json"
DEFAULT_DELAY = settings.psx_request_delay_seconds


def load_checkpoint() -> set[str]:
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return set(data.get("completed", []))
    return set()


def save_checkpoint(completed: set[str]) -> None:
    CHECKPOINT_FILE.write_text(
        json.dumps({"completed": sorted(completed)}, indent=2),
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
    return ["KSE100", "KSE30", "KMI30", *symbols]


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill PSX EOD price history")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    args = parser.parse_args()

    completed = load_checkpoint()
    symbols = [s for s in get_symbols(args.limit) if s not in completed]
    print(f"Backfilling {len(symbols)} symbols ({args.years} years)...")

    for i, symbol in enumerate(symbols, 1):
        try:
            count = run_backfill_symbol(symbol, years=args.years)
            completed.add(symbol)
            save_checkpoint(completed)
            print(f"[{i}/{len(symbols)}] {symbol}: {count} bars")
        except Exception as exc:
            print(f"[{i}/{len(symbols)}] {symbol}: FAILED - {exc}")
        time.sleep(args.delay)

    print("Backfill complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
