#!/usr/bin/env python3
"""Seed macro series from curated CSV-style data."""

from scrapers.macro.run import seed_macro_data
from scrapers.psx.announcements import get_sync_session


def main() -> None:
    session = get_sync_session()
    try:
        count = seed_macro_data(session)
        print({"seeded": count})
    finally:
        session.close()


if __name__ == "__main__":
    main()
