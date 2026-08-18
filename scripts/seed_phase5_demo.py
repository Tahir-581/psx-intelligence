"""Seed Phase 5 demo data for a Pro user."""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.models.alert import Alert
from backend.models.portfolio_holding import PortfolioHolding
from backend.models.screener_preset import ScreenerPreset
from backend.models.user import User

DEMO_USER_ID = os.environ.get("DEMO_PRO_USER_ID", "user_demo_pro")


def get_session() -> Session:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


def seed_phase5_demo(session: Session, user_id: str) -> None:
    user = session.get(User, user_id)
    if not user:
        user = User(id=user_id, email="demo-pro@example.com", plan_tier="pro")
        session.add(user)
        session.flush()

    existing_alerts = session.scalar(
        select(Alert.id).where(Alert.user_id == user_id).limit(1)
    )
    if not existing_alerts:
        session.add_all(
            [
                Alert(
                    user_id=user_id,
                    symbol="ENGRO",
                    alert_type="price_above",
                    params_json={"threshold": 300},
                ),
                Alert(
                    user_id=user_id,
                    symbol="LUCK",
                    alert_type="dividend_announced",
                    params_json={},
                ),
                Alert(
                    user_id=user_id,
                    symbol="HBL",
                    alert_type="insider_trade",
                    params_json={},
                ),
            ]
        )

    existing_holdings = session.scalar(
        select(PortfolioHolding.id).where(PortfolioHolding.user_id == user_id).limit(1)
    )
    if not existing_holdings:
        session.add_all(
            [
                PortfolioHolding(
                    user_id=user_id,
                    symbol="ENGRO",
                    quantity=Decimal("100"),
                    avg_buy_price=Decimal("280"),
                    purchase_date=date(2025, 1, 15),
                ),
                PortfolioHolding(
                    user_id=user_id,
                    symbol="LUCK",
                    quantity=Decimal("50"),
                    avg_buy_price=Decimal("850"),
                    purchase_date=date(2025, 3, 1),
                ),
                PortfolioHolding(
                    user_id=user_id,
                    symbol="HBL",
                    quantity=Decimal("200"),
                    avg_buy_price=Decimal("120"),
                    purchase_date=date(2024, 11, 10),
                ),
            ]
        )

    existing_preset = session.scalar(
        select(ScreenerPreset.id).where(ScreenerPreset.user_id == user_id).limit(1)
    )
    if not existing_preset:
        session.add(
            ScreenerPreset(
                user_id=user_id,
                name="High ROE Banks",
                filters_json={
                    "sectors": ["Commercial Banks"],
                    "roe_min": 15,
                    "debt_to_equity_max": 2,
                },
            )
        )

    session.commit()
    print(f"Phase 5 demo seeded for user {user_id}")


def main() -> None:
    session = get_session()
    try:
        seed_phase5_demo(session, DEMO_USER_ID)
    finally:
        session.close()


if __name__ == "__main__":
    main()
