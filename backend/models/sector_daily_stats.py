from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class SectorDailyStats(Base):
    __tablename__ = "sector_daily_stats"
    __table_args__ = (UniqueConstraint("trade_date", "sector", name="uq_sector_daily_stats"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    company_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_market_cap: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    median_pe: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    median_dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    return_1d: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    return_1w: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    return_1m: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    return_ytd: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    top_gainer_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    top_loser_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
