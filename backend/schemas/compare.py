"""Compare and peers response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class NormalizedSeriesPoint(BaseModel):
    date: date
    value: float


class NormalizedSeries(BaseModel):
    symbol: str
    name: str
    sector: str | None
    points: list[NormalizedSeriesPoint]


class CompareRatioRow(BaseModel):
    ratio_code: str
    values: dict[str, float | None]


class CompareResponse(BaseModel):
    symbols: list[str]
    series: list[NormalizedSeries]
    ratios: list[CompareRatioRow]


class PeerRow(BaseModel):
    symbol: str
    name: str
    market_cap: float | None
    pe_ttm: float | None
    roe: float | None
    debt_to_equity: float | None
    dividend_yield: float | None
    return_1m: float | None


class PeersResponse(BaseModel):
    symbol: str
    sector: str
    peers: list[PeerRow]
    sector_median: PeerRow
