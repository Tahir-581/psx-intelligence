from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, Field


class TickerListItem(BaseModel):
    symbol: str
    name: str
    sector: str
    board: str
    ltp: float | None = None
    change_pct: float | None = None


class TickerListResponse(BaseModel):
    items: list[TickerListItem]
    total: int
    page: int
    page_size: int


class SnapshotResponse(BaseModel):
    symbol: str
    name: str
    sector: str
    board: str
    ltp: float
    change: float
    change_pct: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: int | None = None
    market_cap: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    avg_volume_30d: float | None = None
    shares_outstanding: int | None = None
    prev_close: float | None = None
    updated_at: datetime | None = None
    pe_ttm: float | None = None
    eps_ttm: float | None = None
    dividend_yield: float | None = None
    free_float_pct: float | None = None
    beta: float | None = None
    sector_return_1m: float | None = None
    next_dividend_ex_date: date | None = None
    vwap: float | None = None
    circuit_breaker: bool = False
    trading_halt: bool = False
    board_change_30d: bool = False


class PriceBar(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class PriceSeriesResponse(BaseModel):
    symbol: str
    bars: list[PriceBar]
    overlay_bars: list[PriceBar] | None = None
    indicator_series: dict[str, list[dict]] | None = None
    volume_ma: list[dict] | None = None


class ChartMarkerItem(BaseModel):
    time: datetime
    label: str
    kind: str
    significance: int = 1


class ChartMarkersResponse(BaseModel):
    symbol: str
    markers: list[ChartMarkerItem]
    delisting_detected: bool = False
    delisting_title: str | None = None


class MoverItem(BaseModel):
    symbol: str
    name: str
    sector: str
    ltp: float
    change_pct: float
    volume: int


class MarketSummaryResponse(BaseModel):
    index_symbol: str = "KSE100"
    index_level: float | None = None
    index_change_pct: float | None = None
    advances: int = 0
    declines: int = 0
    unchanged: int = 0
    top_gainers: list[MoverItem] = Field(default_factory=list)
    top_losers: list[MoverItem] = Field(default_factory=list)
    market_open: bool = False


class ScraperHealthItem(BaseModel):
    scraper_name: str
    last_success_at: datetime | None
    last_run_at: datetime | None
    records_ingested: int
    error_message: str | None


class DataHealthResponse(BaseModel):
    scrapers: list[ScraperHealthItem]
    stale_index_symbols: list[str] = Field(default_factory=list)


class WsPriceTick(BaseModel):
    symbol: str
    ltp: float
    change_pct: float
    ts: str
