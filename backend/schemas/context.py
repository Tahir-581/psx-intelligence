from datetime import date, datetime

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    id: int
    source: str
    headline: str
    published_at: datetime
    author: str | None = None
    source_url: str
    excerpt: str | None = None
    topic_tag: str | None = None
    link_confidence: float | None = None
    ai_summary: str | None = None
    sentiment_badge: str | None = None


class NewsListResponse(BaseModel):
    items: list[NewsItem]
    total: int
    page: int
    page_size: int


class CorporateActionItem(BaseModel):
    id: int
    symbol: str
    action_type: str
    announced_at: datetime
    ex_date: date | None = None
    record_date: date | None = None
    payment_date: date | None = None
    amount_per_share: float | None = None
    ratio: str | None = None
    currency: str = "PKR"
    source_announcement_id: int | None = None


class CorporateActionListResponse(BaseModel):
    items: list[CorporateActionItem]


class MaterialEventItem(BaseModel):
    id: int
    symbol: str
    event_type: str
    headline: str
    event_date: date
    counterparty: str | None = None
    amount_pkr: float | None = None
    significance_score: int
    summary: str | None = None
    source_announcement_id: int | None = None
    linked_symbol: str | None = None


class MaterialEventListResponse(BaseModel):
    items: list[MaterialEventItem]


class BetaResponse(BaseModel):
    symbol: str
    beta: float | None = None
    sector: str | None = None
    sector_return_1m: float | None = None
    ticker_return_1m: float | None = None


class MacroPoint(BaseModel):
    time: datetime
    value: float
    unit: str | None = None


class MacroSeriesResponse(BaseModel):
    series_code: str
    points: list[MacroPoint] = Field(default_factory=list)


class SectorStatsItem(BaseModel):
    sector: str
    company_count: int
    total_market_cap: float | None = None
    median_pe: float | None = None
    median_dividend_yield: float | None = None
    return_1d: float | None = None
    return_1w: float | None = None
    return_1m: float | None = None
    return_ytd: float | None = None
    top_gainer_symbol: str | None = None
    top_loser_symbol: str | None = None


class SectorStatsResponse(BaseModel):
    trade_date: date | None = None
    range: str
    sectors: list[SectorStatsItem] = Field(default_factory=list)


class SectorCompanyFinancials(BaseModel):
    revenue: float | None = None
    gross_profit: float | None = None
    ebitda: float | None = None
    pat: float | None = None
    total_assets: float | None = None
    total_equity: float | None = None
    total_debt: float | None = None
    ocf: float | None = None
    capex: float | None = None
    period_end: date | None = None


class SectorCompanyRow(BaseModel):
    symbol: str
    name: str
    ltp: float | None = None
    change_pct: float | None = None
    market_cap: float | None = None
    volume: int | None = None
    avg_volume_30d: float | None = None
    pe_ttm: float | None = None
    eps_ttm: float | None = None
    dividend_yield: float | None = None
    roe: float | None = None
    roa: float | None = None
    gross_margin: float | None = None
    ebitda_margin: float | None = None
    net_margin: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    beta: float | None = None
    return_range: float | None = None
    financials: SectorCompanyFinancials = Field(default_factory=SectorCompanyFinancials)


class SectorDetailResponse(BaseModel):
    sector: str
    range: str
    trade_date: date | None = None
    stats: SectorStatsItem | None = None
    companies: list[SectorCompanyRow] = Field(default_factory=list)


class CorporateCalendarItem(BaseModel):
    symbol: str
    action_type: str
    announced_at: datetime
    ex_date: date | None = None
    record_date: date | None = None
    amount_per_share: float | None = None
    ratio: str | None = None


class CorporateCalendarResponse(BaseModel):
    items: list[CorporateCalendarItem] = Field(default_factory=list)


class DpsDataPoint(BaseModel):
    year: int
    ex_date: date
    dps: float
    payout_ratio: float | None = None


class TerpCalculation(BaseModel):
    rights_ratio: str
    market_price: float
    rights_price: float
    terp: float


class CorpActionAnalyticsResponse(BaseModel):
    symbol: str
    dps_series: list[DpsDataPoint] = Field(default_factory=list)
    terp: TerpCalculation | None = None


class NewsVolumePoint(BaseModel):
    date: date
    count: int


class NewsVolumeResponse(BaseModel):
    symbol: str
    days: int
    points: list[NewsVolumePoint] = Field(default_factory=list)


class NewsKeywordsResponse(BaseModel):
    symbol: str
    keywords: list[dict] = Field(default_factory=list)
