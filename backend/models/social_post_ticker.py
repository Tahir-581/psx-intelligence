from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class SocialPostTicker(Base):
    __tablename__ = "social_post_tickers"

    post_id: Mapped[int] = mapped_column(
        ForeignKey("social_posts.id", ondelete="CASCADE"), primary_key=True
    )
    symbol: Mapped[str] = mapped_column(
        String(20), ForeignKey("tickers.symbol"), primary_key=True, index=True
    )
    link_confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
