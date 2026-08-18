#!/usr/bin/env python3
"""Full 5Y × all tickers backfill with checkpoint — wraps backfill_prices logic."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).resolve().parent / "backfill_prices.py"
    args = ["python", str(script), "--years", "5"] + sys.argv[1:]
    sys.exit(subprocess.call(args))
