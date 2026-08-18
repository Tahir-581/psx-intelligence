#!/usr/bin/env python3
"""Seed governance data from CSV fallback."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.ratios import get_sync_session
from scrapers.governance.from_announcements import ingest_governance_from_announcements
from scrapers.governance.seed import seed_governance_from_csv


def main() -> None:
    session = get_sync_session()
    try:
        csv_result = seed_governance_from_csv(session)
        ann_result = ingest_governance_from_announcements(session)
        print({"csv": csv_result, "announcements": ann_result})
    finally:
        session.close()


if __name__ == "__main__":
    main()
