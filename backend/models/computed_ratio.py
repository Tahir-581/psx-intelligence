from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ComputedRatio(Base):
    __tablename__ = "computed_ratios"
    __table_args__ = (
        UniqueConstraint("symbol", "period_end", "ratio_code", name="uq_computed_ratios"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), ForeignKey("tickers.symbol"), index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    ratio_code: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
