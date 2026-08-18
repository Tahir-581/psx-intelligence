from datetime import date, datetime

from pydantic import BaseModel, Field


class AnnouncementItem(BaseModel):
    id: int
    symbol: str
    published_at: datetime
    title: str
    category: str
    pdf_url: str | None = None
    source_url: str | None = None
    body_text: str | None = None


class AnnouncementListResponse(BaseModel):
    items: list[AnnouncementItem]
    total: int
    page: int
    page_size: int


class FinancialPeriodColumn(BaseModel):
    period_id: int
    period_end: date
    fiscal_year: int
    fiscal_quarter: int | None = None
    parser_confidence: float | None = None
    is_verified: bool = False
    source_pdf_url: str | None = None


class FinancialLineRow(BaseModel):
    line_code: str
    unit: str
    values: dict[str, float]
    yoy_change_pct: dict[str, float | None] = Field(default_factory=dict)


class FinancialsResponse(BaseModel):
    symbol: str
    period_type: str
    periods: list[FinancialPeriodColumn]
    rows: list[FinancialLineRow]
    low_confidence: bool = False
    validation_flags: list[str] = Field(default_factory=list)


class RatioValue(BaseModel):
    code: str
    value: float | None = None


class RatioHistoryPoint(BaseModel):
    period_end: date
    ratios: dict[str, float | None]


class RatiosResponse(BaseModel):
    symbol: str
    sector: str
    latest: list[RatioValue] = Field(default_factory=list)
    history: list[RatioHistoryPoint] = Field(default_factory=list)
    sector_medians: dict[str, float] = Field(default_factory=dict)


class InsiderTradeItem(BaseModel):
    id: int
    director_name: str
    designation: str | None = None
    transaction_date: date
    transaction_type: str
    shares: int
    price_per_share: float | None = None
    post_holding_shares: int | None = None


class InsiderTradesResponse(BaseModel):
    symbol: str
    trades: list[InsiderTradeItem]
    net_30d: int = 0
    net_90d: int = 0
    cluster_buy_14d: bool = False


class OwnershipSnapshotItem(BaseModel):
    holder_category: str
    shares: int
    pct_outstanding: float
    pledged_shares_pct: float | None = None
    holder_name: str | None = None


class OwnershipHistoryPoint(BaseModel):
    as_of_date: date
    snapshots: list[OwnershipSnapshotItem]


class OwnershipResponse(BaseModel):
    symbol: str
    latest_snapshot: list[OwnershipSnapshotItem]
    history: list[OwnershipHistoryPoint] = Field(default_factory=list)
    pledged_shares_pct: float | None = None
    pledged_warning: bool = False
    named_holders: list[OwnershipSnapshotItem] = Field(default_factory=list)
    free_float_pct: float | None = None
