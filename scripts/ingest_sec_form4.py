"""CLI: python -m scripts.ingest_sec_form4"""

import logging
import sys

from scrapers.sec.ingest_form4 import run_ingest_form4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting SEC Form 4 ingest...")
    result = run_ingest_form4()
    logger.info("Form 4 ingest complete: %s", result)
