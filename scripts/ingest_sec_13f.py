"""CLI: python -m scripts.ingest_sec_13f"""

import logging
import sys

from scrapers.sec.ingest_13f import run_ingest_13f
from scrapers.sec.ingest_tickers import run_ingest_tickers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting SEC 13F bulk ingest (this may take ~30 minutes)...")
    result = run_ingest_13f()
    logger.info("13F ingest complete: %s", result)
    logger.info("Starting ticker map backfill...")
    tickers = run_ingest_tickers()
    logger.info("Ticker map complete: %s", tickers)
