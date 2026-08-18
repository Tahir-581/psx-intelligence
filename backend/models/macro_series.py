from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class MacroSeries(Base):
    __tablename__ = "macro_series"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    series_code: Mapped[str] = mapped_column(String(30), primary_key=True)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
