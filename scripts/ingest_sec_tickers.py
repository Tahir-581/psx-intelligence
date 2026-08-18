"""CLI: python -m scripts.ingest_sec_tickers"""

import logging
import sys

from scrapers.sec.ingest_tickers import run_ingest_tickers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting SEC ticker map ingest...")
    result = run_ingest_tickers()
    logger.info("Ticker map complete: %s", result)
