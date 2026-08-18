from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class InsiderTrade(Base):
    __tablename__ = "insider_trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), ForeignKey("tickers.symbol"), index=True)
    director_name: Mapped[str] = mapped_column(String(200), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    shares: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price_per_share: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    post_holding_shares: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("announcements.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
