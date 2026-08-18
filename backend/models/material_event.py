from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class MaterialEvent(Base):
    __tablename__ = "material_events"
    __table_args__ = (
        UniqueConstraint("symbol", "event_type", "event_date", "headline", name="uq_material_events_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), ForeignKey("tickers.symbol"), index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    counterparty: Mapped[str | None] = mapped_column(String(200), nullable=True)
    amount_pkr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    significance_score: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_announcement_id: Mapped[int | None] = mapped_column(
        ForeignKey("announcements.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
