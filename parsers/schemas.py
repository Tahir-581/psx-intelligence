from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ParsedLineItem(BaseModel):
    line_code: str
    value: Decimal
    unit: str = "absolute"


class ParsedFinancialPeriod(BaseModel):
    symbol: str
    period_end: date
    period_type: str
    fiscal_year: int
    fiscal_quarter: int | None = None
    currency: str = "PKR"
    line_items: list[ParsedLineItem] = Field(default_factory=list)
    confidence: float = 0.0


class ParsedInsiderTrade(BaseModel):
    director_name: str
    designation: str | None = None
    transaction_date: date
    transaction_type: str
    shares: int
    price_per_share: Decimal | None = None
    post_holding_shares: int | None = None


class ParsedOwnershipRow(BaseModel):
    holder_category: str
    shares: int
    pct_outstanding: Decimal
    as_of_date: date | None = None


class ParsedOwnershipSnapshot(BaseModel):
    symbol: str
    as_of_date: date
    rows: list[ParsedOwnershipRow] = Field(default_factory=list)
    confidence: float = 0.0


class ParsedCorporateAction(BaseModel):
    symbol: str
    action_type: str
    announced_at: datetime
    ex_date: date | None = None
    record_date: date | None = None
    payment_date: date | None = None
    amount_per_share: Decimal | None = None
    ratio: str | None = None
    currency: str = "PKR"
    source_announcement_id: int | None = None
    details_json: dict = Field(default_factory=dict)


class ParsedMaterialEvent(BaseModel):
    symbol: str
    event_type: str
    headline: str
    event_date: date
    counterparty: str | None = None
    amount_pkr: Decimal | None = None
    significance_score: int = 1
    summary: str | None = None
    source_announcement_id: int | None = None
