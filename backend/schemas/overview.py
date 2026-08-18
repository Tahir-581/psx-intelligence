from datetime import date, datetime

from pydantic import BaseModel, Field

from backend.schemas.fundamentals import (
    AnnouncementItem,
    RatioValue,
)
from backend.schemas.intelligence import AiSummaryResponse


class OverviewNewsItem(BaseModel):
    id: int
    headline: str
    source: str
    published_at: datetime


class OverviewResponse(BaseModel):
    symbol: str
    ai_summary: AiSummaryResponse | None = None
    key_ratios: list[RatioValue] = Field(default_factory=list)
    next_dividend_ex_date: date | None = None
    upcoming_actions: list[dict] = Field(default_factory=list)
    recent_announcements: list[AnnouncementItem] = Field(default_factory=list)
    recent_news: list[OverviewNewsItem] = Field(default_factory=list)
    board_change_30d: bool = False
    delisting_detected: bool = False
    delisting_title: str | None = None
