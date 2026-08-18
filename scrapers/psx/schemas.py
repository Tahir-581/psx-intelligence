import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from scrapers.psx.client import SYMBOL_PATTERN


class TickerRecord(BaseModel):
    symbol: str
    name: str
    sector: str = "Unknown"
    board: str = "Main"
    isin: str | None = None
    shares_outstanding: int | None = None
    is_debt: bool = False
    is_etf: bool = False

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not SYMBOL_PATTERN.match(symbol):
            raise ValueError(f"Invalid symbol: {value}")
        return symbol

    @field_validator("shares_outstanding")
    @classmethod
    def validate_shares(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("shares_outstanding must be positive")
        return value


class EodPriceRecord(BaseModel):
    symbol: str
    time_unix: int
    open: float
    high: float
    low: float
    close: float
    volume: int
    value_traded: float | None = None

    @field_validator("close", "open", "high", "low")
    @classmethod
    def validate_price(cls, value: float) -> float:
        if value < 0.01 or value > 500_000:
            raise ValueError(f"Price out of plausible range: {value}")
        return value

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Volume cannot be negative")
        return value


class LtpRecord(BaseModel):
    symbol: str
    ltp: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    volume: int
    ldcp: float
    board: str = "Main"


class PsxSymbolApiItem(BaseModel):
    symbol: str
    name: str
    sectorName: str = Field(default="Unknown")
    isETF: bool = False
    isDebt: bool = False

    def to_ticker_record(self) -> TickerRecord:
        return TickerRecord(
            symbol=self.symbol,
            name=self.name,
            sector=self.sectorName or "Unknown",
            is_debt=self.isDebt,
            is_etf=self.isETF,
        )


def parse_eod_rows(symbol: str, payload: dict) -> list[EodPriceRecord]:
    if payload.get("status") != 1:
        return []
    records: list[EodPriceRecord] = []
    for row in payload.get("data", []):
        if not isinstance(row, list) or len(row) < 4:
            continue
        ts, close, volume, open_price = row[0], float(row[1]), int(row[2]), float(row[3])
        high = max(close, open_price)
        low = min(close, open_price)
        try:
            records.append(
                EodPriceRecord(
                    symbol=symbol,
                    time_unix=int(ts),
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                )
            )
        except Exception:
            continue
    return records


def parse_symbols_json(raw: list) -> list[TickerRecord]:
    records: list[TickerRecord] = []
    for item in raw:
        try:
            records.append(PsxSymbolApiItem.model_validate(item).to_ticker_record())
        except Exception:
            continue
    return records


SHARES_PATTERN = re.compile(
    r'<div class="stats_label">Shares</div>\s*<div class="stats_value">([\d,]+)</div>'
)


class AnnouncementRecord(BaseModel):
    symbol: str
    published_at: datetime
    title: str
    category: str = "other"
    pdf_url: str | None = None
    source_url: str | None = None
    body_text: str | None = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not SYMBOL_PATTERN.match(symbol):
            raise ValueError(f"Invalid symbol: {value}")
        return symbol


def parse_announcements_from_company_html(
    html: str, symbol: str, base_url: str
) -> list[AnnouncementRecord]:
    from scrapers.psx.client import parse_company_announcements

    raw_rows = parse_company_announcements(html, symbol, base_url)
    records: list[AnnouncementRecord] = []
    for row in raw_rows:
        try:
            records.append(AnnouncementRecord.model_validate(row))
        except Exception:
            continue
    return records

