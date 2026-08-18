"""CSV seed fallback for governance data when SECP scraping is blocked."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from backend.models.governance import BoardMember, CreditRating

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "governance_seed.csv"


def seed_governance_from_csv(session: Session, csv_path: Path | None = None) -> dict:
    path = csv_path or DEFAULT_CSV
    if not path.exists():
        return {"seeded": 0, "skipped": "no_csv"}
    board = 0
    ratings = 0
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            kind = row.get("type", "").strip()
            symbol = row.get("symbol", "").strip().upper()
            if not symbol:
                continue
            if kind == "board":
                session.add(
                    BoardMember(
                        symbol=symbol,
                        name=row["name"],
                        role=row.get("role", "Director"),
                        appointment_date=datetime.strptime(row["date"], "%Y-%m-%d").date()
                        if row.get("date")
                        else None,
                    )
                )
                board += 1
            elif kind == "rating":
                session.add(
                    CreditRating(
                        symbol=symbol,
                        agency=row.get("agency", "PACRA"),
                        rating=row["rating"],
                        outlook=row.get("outlook"),
                        effective_date=datetime.strptime(row["date"], "%Y-%m-%d").date(),
                    )
                )
                ratings += 1
    session.commit()
    return {"board": board, "ratings": ratings}
