"""CLI: python -m scripts.ingest_sec_delta"""

import logging
import sys

from scrapers.sec.ingest_delta import run_ingest_delta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting SEC 13F delta ingest...")
    result = run_ingest_delta()
    logger.info("Delta ingest complete: %s", result)
