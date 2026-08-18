"""Screener request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScreenerFilters(BaseModel):
    sectors: list[str] | None = None
    boards: list[str] | None = None
    index_membership: list[str] | None = None
    market_cap_min_bn: float | None = None
    market_cap_max_bn: float | None = None
    pe_min: float | None = None
    pe_max: float | None = None
    pb_min: float | None = None
    pb_max: float | None = None
    dividend_yield_min: float | None = None
    dividend_yield_max: float | None = None
    roe_min: float | None = None
    roa_min: float | None = None
    net_margin_min: float | None = None
    debt_to_equity_max: float | None = None
    current_ratio_min: float | None = None
    return_1m_min: float | None = None
    return_1m_max: float | None = None
    return_3m_min: float | None = None
    return_3m_max: float | None = None
    beta_min: float | None = None
    beta_max: float | None = None
    avg_volume_30d_min: float | None = None
    near_52w_high_pct: float | None = None
    net_insider_buy_30d: bool | None = None
    pledged_shares_below_pct: float | None = None
    free_float_min: float | None = None
    foreign_pct_min: float | None = None
    sentiment_score_min: float | None = None
    sentiment_momentum_positive: bool | None = None


class ScreenerRequest(BaseModel):
    filters: ScreenerFilters = Field(default_factory=ScreenerFilters)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
    sort_by: str = "symbol"
    sort_dir: str = "asc"
    columns: list[str] | None = None


class ScreenerResultRow(BaseModel):
    symbol: str
    name: str
    sector: str
    ltp: float | None = None
    change_pct: float | None = None
    market_cap: float | None = None
    pe_ttm: float | None = None
    roe: float | None = None
    debt_to_equity: float | None = None
    dividend_yield: float | None = None
    avg_volume_30d: float | None = None
    beta: float | None = None


class ScreenerResponse(BaseModel):
    items: list[ScreenerResultRow]
    total: int
    page: int
    page_size: int
    filter_groups_active: int
    filter_groups_limit: int | None = None


class ScreenerPresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    filters: ScreenerFilters


class ScreenerPresetItem(BaseModel):
    id: int
    name: str
    filters: ScreenerFilters
    created_at: str
    updated_at: str


class ScreenerPresetListResponse(BaseModel):
    items: list[ScreenerPresetItem]
    limit: int
    count: int
