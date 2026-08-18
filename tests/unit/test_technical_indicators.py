"""Unit tests for technical indicators and price adjustments."""

from datetime import UTC, datetime

from backend.schemas.market import PriceBar
from backend.services.price_adjustments import apply_adjustments
from backend.services.technical import bollinger_bands, ema, sma, volume_ma


def _bars(n: int, start: float = 100.0) -> list[PriceBar]:
    out = []
    for i in range(n):
        c = start + i
        out.append(
            PriceBar(
                time=datetime(2024, 1, 1 + i, tzinfo=UTC),
                open=c,
                high=c + 1,
                low=c - 1,
                close=c,
                volume=1000 + i * 10,
            )
        )
    return out


def test_sma_produces_values():
    bars = _bars(25)
    series = sma(bars, 20)
    assert len(series) == 6
    assert series[0][1] > 0


def test_ema_produces_values():
    bars = _bars(30)
    series = ema(bars, 12)
    assert len(series) == 19


def test_bollinger_bands():
    bars = _bars(25)
    bb = bollinger_bands(bars, 20)
    assert len(bb["upper"]) == 6
    assert bb["upper"][0][1] >= bb["middle"][0][1]


def test_volume_ma():
    bars = _bars(25)
    series = volume_ma(bars, 20)
    assert len(series) == 6


def test_apply_adjustments_split():
    bars = _bars(5, start=100)
    factors = [(datetime(2024, 1, 3, tzinfo=UTC), 2.0)]
    adjusted = apply_adjustments(bars, factors)
    # Only bars strictly before ex-date are backward-adjusted
    assert adjusted[0].close == 50.0  # Jan 1
    assert adjusted[1].close == 50.5  # Jan 2
    assert adjusted[2].close == 102.0  # Jan 3 (ex-date, unadjusted)
    assert adjusted[4].close == 104.0  # Jan 5 (post-split)
