from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class IndexConstituent(Base):
    __tablename__ = "index_constituents"

    symbol: Mapped[str] = mapped_column(
        String(20), ForeignKey("tickers.symbol"), primary_key=True
    )
    index_code: Mapped[str] = mapped_column(String(20), primary_key=True, index=True)
