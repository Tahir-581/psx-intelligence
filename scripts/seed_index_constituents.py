"""Seed index constituents for KSE100/KSE30/KMI30 screener filters."""

from __future__ import annotations

import argparse

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models.index_constituent import IndexConstituent
from backend.models.ticker import Ticker

# Fallback: top liquid symbols per index when PSX constituent API unavailable
INDEX_FALLBACK: dict[str, list[str]] = {
    "KSE100": [
        "ENGRO", "LUCK", "HBL", "UBL", "MCB", "OGDC", "PSO", "FFC", "EFERT", "MARI",
        "HUBC", "SYS", "TRG", "BAHL", "BAFL", "POL", "ATRL", "DGKC", "MLCF", "NBP",
    ],
    "KSE30": [
        "ENGRO", "LUCK", "HBL", "UBL", "MCB", "OGDC", "PSO", "FFC", "EFERT", "MARI",
        "HUBC", "SYS", "TRG", "BAHL", "BAFL",
    ],
    "KMI30": [
        "ENGRO", "LUCK", "OGDC", "MARI", "PSO", "FFC", "EFERT", "ATRL", "POL", "DGKC",
    ],
}


def get_session() -> Session:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


def seed_index_constituents(session: Session) -> int:
    active = set(
        session.scalars(select(Ticker.symbol).where(Ticker.is_active.is_(True))).all()
    )
    count = 0
    for index_code, symbols in INDEX_FALLBACK.items():
        for sym in symbols:
            if sym not in active:
                continue
            stmt = insert(IndexConstituent).values(symbol=sym, index_code=index_code)
            stmt = stmt.on_conflict_do_nothing(index_elements=["symbol", "index_code"])
            session.execute(stmt)
            count += 1
    session.commit()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed index constituents")
    parser.parse_args()
    session = get_session()
    try:
        n = seed_index_constituents(session)
        print(f"Seeded {n} index constituent rows")
    finally:
        session.close()


if __name__ == "__main__":
    main()
