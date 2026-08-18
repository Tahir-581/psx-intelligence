"""Cross-validation for parsed financial statements."""

from __future__ import annotations


def validate_financials(by_code: dict[str, dict[int, tuple[float, str]]], period_ids: list[int]) -> list[str]:
    flags: list[str] = []
    for pid in period_ids:
        def val(code: str) -> float | None:
            if code in by_code and pid in by_code[code]:
                return by_code[code][pid][0]
            return None

        assets = val("total_assets")
        equity = val("total_equity")
        liabilities = val("total_liabilities")
        if assets is not None and equity is not None and liabilities is not None:
            diff = abs(assets - (equity + liabilities))
            if diff > max(assets * 0.02, 1):
                flags.append(f"Period {pid}: Assets != L+E (diff {diff:.0f})")

        revenue = val("revenue")
        cogs = val("cogs")
        gross = val("gross_profit")
        if revenue is not None and cogs is not None and gross is not None:
            expected = revenue - cogs
            if abs(expected - gross) > max(revenue * 0.02, 1):
                flags.append(f"Period {pid}: Revenue - COGS != Gross Profit")
    return flags


def compute_yoy_changes(
    period_cols: list, by_code: dict[str, dict[int, tuple[float, str]]]
) -> dict[str, dict[str, float | None]]:
    """Compute YoY % change per line code per period_end key."""
    yoy: dict[str, dict[str, float | None]] = {}
    if len(period_cols) < 5:
        return yoy
    for code in by_code:
        yoy[code] = {}
        for i, col in enumerate(period_cols):
            if i < 4:
                yoy[code][col.period_end.isoformat()] = None
                continue
            prev_col = period_cols[i - 4]
            cur = by_code[code].get(col.period_id)
            prev = by_code[code].get(prev_col.period_id)
            if cur and prev and prev[0] != 0:
                yoy[code][col.period_end.isoformat()] = ((cur[0] - prev[0]) / abs(prev[0])) * 100
            else:
                yoy[code][col.period_end.isoformat()] = None
    return yoy
