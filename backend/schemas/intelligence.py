from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SentimentDataPoint(BaseModel):
    time: datetime
    source: str
    score: float
    positive_pct: float | None = None
    negative_pct: float | None = None
    neutral_pct: float | None = None
    post_count: int = 0


class SentimentSeriesResponse(BaseModel):
    symbol: str
    days: int
    aggregate: list[SentimentDataPoint]
    by_source: dict[str, list[SentimentDataPoint]]
    momentum_3d: float | None = None
    current_score: float | None = None
    price_divergence: bool | None = None
    divergence_note: str | None = None


class SentimentPriceOverlayPoint(BaseModel):
    time: datetime
    sentiment: float
    price_normalized: float


class SentimentPriceOverlayResponse(BaseModel):
    symbol: str
    days: int
    points: list[SentimentPriceOverlayPoint] = Field(default_factory=list)


class SocialPostItem(BaseModel):
    id: int
    source: str
    author_handle: str | None
    posted_at: datetime
    text: str
    url: str | None
    engagement_json: dict | None = None
    link_confidence: float | None = None


class SocialFeedResponse(BaseModel):
    symbol: str
    items: list[SocialPostItem]
    total: int


class AiSummaryResponse(BaseModel):
    symbol: str | None
    summary_type: str
    content: str
    generated_at: datetime
    model: str


class WatchlistItemSnapshot(BaseModel):
    symbol: str
    name: str | None = None
    ltp: float | None = None
    change_pct: float | None = None
    added_at: datetime


class WatchlistResponse(BaseModel):
    items: list[WatchlistItemSnapshot]
    limit: int | None = None
    count: int
