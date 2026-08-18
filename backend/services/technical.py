"""Technical indicator computations for price series."""

from __future__ import annotations

from backend.schemas.market import PriceBar


def sma(bars: list[PriceBar], period: int) -> list[tuple]:
    """Return (time, value) pairs for simple moving average."""
    if len(bars) < period:
        return []
    result: list[tuple] = []
    window_sum = sum(b.close for b in bars[:period])
    result.append((bars[period - 1].time, window_sum / period))
    for i in range(period, len(bars)):
        window_sum += bars[i].close - bars[i - period].close
        result.append((bars[i].time, window_sum / period))
    return result


def ema(bars: list[PriceBar], period: int) -> list[tuple]:
    """Return (time, value) pairs for exponential moving average."""
    if len(bars) < period:
        return []
    k = 2 / (period + 1)
    ema_val = sum(b.close for b in bars[:period]) / period
    result: list[tuple] = [(bars[period - 1].time, ema_val)]
    for i in range(period, len(bars)):
        ema_val = bars[i].close * k + ema_val * (1 - k)
        result.append((bars[i].time, ema_val))
    return result


def bollinger_bands(
    bars: list[PriceBar], period: int = 20, std_dev: float = 2.0
) -> dict[str, list[tuple]]:
    """Return upper, middle, lower Bollinger bands as (time, value) lists."""
    if len(bars) < period:
        return {"upper": [], "middle": [], "lower": []}
    upper: list[tuple] = []
    middle: list[tuple] = []
    lower: list[tuple] = []
    for i in range(period - 1, len(bars)):
        window = bars[i - period + 1 : i + 1]
        closes = [b.close for b in window]
        mean = sum(closes) / period
        variance = sum((c - mean) ** 2 for c in closes) / period
        std = variance**0.5
        t = bars[i].time
        middle.append((t, mean))
        upper.append((t, mean + std_dev * std))
        lower.append((t, mean - std_dev * std))
    return {"upper": upper, "middle": middle, "lower": lower}


def volume_ma(bars: list[PriceBar], period: int = 20) -> list[tuple]:
    """Return (time, value) pairs for volume moving average."""
    if len(bars) < period:
        return []
    result: list[tuple] = []
    window_sum = sum(b.volume for b in bars[:period])
    result.append((bars[period - 1].time, window_sum / period))
    for i in range(period, len(bars)):
        window_sum += bars[i].volume - bars[i - period].volume
        result.append((bars[i].time, window_sum / period))
    return result


def compute_indicators(
    bars: list[PriceBar], overlays: list[str]
) -> dict[str, list[dict]]:
    """Compute requested indicator series from price bars."""
    result: dict[str, list[dict]] = {}
    for name in overlays:
        key = name.upper()
        if key == "SMA20":
            series = sma(bars, 20)
        elif key == "SMA50":
            series = sma(bars, 50)
        elif key == "SMA200":
            series = sma(bars, 200)
        elif key == "EMA12":
            series = ema(bars, 12)
        elif key == "EMA26":
            series = ema(bars, 26)
        elif key == "BB20":
            bb = bollinger_bands(bars, 20, 2.0)
            for band_name, band_series in bb.items():
                result[f"BB20_{band_name}"] = [
                    {"time": t.isoformat(), "value": v} for t, v in band_series
                ]
            continue
        elif key == "VOLMA20":
            series = volume_ma(bars, 20)
        else:
            continue
        result[key] = [{"time": t.isoformat(), "value": v} for t, v in series]
    return result
