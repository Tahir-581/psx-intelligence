from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class SentimentScore(Base):
    __tablename__ = "sentiment_scores"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    symbol: Mapped[str] = mapped_column(
        String(20), ForeignKey("tickers.symbol"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(20), primary_key=True)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    positive_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    negative_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    neutral_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    post_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
