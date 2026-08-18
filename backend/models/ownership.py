from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class OwnershipSnapshot(Base):
    __tablename__ = "ownership_snapshots"
    __table_args__ = (
        UniqueConstraint("symbol", "as_of_date", "holder_category", name="uq_ownership_snap"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), ForeignKey("tickers.symbol"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    holder_category: Mapped[str] = mapped_column(String(50), nullable=False)
    shares: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pct_outstanding: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    pledged_shares_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    holder_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
