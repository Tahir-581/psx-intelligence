"""Portfolio tracker schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    symbol: str
    quantity: Decimal = Field(gt=0)
    avg_buy_price: Decimal = Field(gt=0)
    purchase_date: date
    notes: str | None = None


class HoldingUpdate(BaseModel):
    quantity: Decimal | None = Field(default=None, gt=0)
    avg_buy_price: Decimal | None = Field(default=None, gt=0)
    purchase_date: date | None = None
    notes: str | None = None


class HoldingItem(BaseModel):
    id: int
    symbol: str
    name: str | None = None
    sector: str | None = None
    quantity: float
    avg_buy_price: float
    purchase_date: date
    notes: str | None = None
    ltp: float | None = None
    current_value: float | None = None
    cost_basis: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None
    weight_pct: float | None = None
    yield_on_cost: float | None = None
    dividend_yield: float | None = None


class SectorExposureItem(BaseModel):
    sector: str
    weight_pct: float
    concentrated: bool


class PortfolioSeriesPoint(BaseModel):
    date: date
    portfolio: float
    kse100: float | None


class PortfolioSummary(BaseModel):
    total_value: float
    total_cost: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    dividend_income_ytd: float
    portfolio_beta: float | None
    sector_exposure: list[SectorExposureItem]
    concentration_warning: bool
    vs_kse100: list[PortfolioSeriesPoint]


class PortfolioResponse(BaseModel):
    holdings: list[HoldingItem]
    summary: PortfolioSummary


class TransactionItem(BaseModel):
    id: int
    symbol: str
    txn_type: str
    quantity: float
    price: float
    txn_date: date
    created_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionItem]
