from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class NewsArticleTicker(Base):
    __tablename__ = "news_article_tickers"

    article_id: Mapped[int] = mapped_column(
        ForeignKey("news_articles.id", ondelete="CASCADE"), primary_key=True
    )
    symbol: Mapped[str] = mapped_column(
        String(20), ForeignKey("tickers.symbol"), primary_key=True, index=True
    )
    link_confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
