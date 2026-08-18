"""Free vs Pro feature entitlements."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from backend.models.user import User

if TYPE_CHECKING:
    from backend.schemas.screener import ScreenerFilters

FREE_NEWS_DAYS = 30
FREE_FINANCIAL_QUARTERS = 4
FREE_WATCHLIST_LIMIT = 5
FREE_RATE_LIMIT = 60
PRO_RATE_LIMIT = 300
FREE_SCREENER_FILTER_GROUPS = 3
PRO_SCREENER_PRESET_LIMIT = 10
FREE_COMPARE_SYMBOLS = 2
PRO_COMPARE_SYMBOLS = 4


def is_pro(user: User | None) -> bool:
    return True


def news_cutoff(user: User | None) -> datetime | None:
    if is_pro(user):
        return None
    return datetime.now(UTC) - timedelta(days=FREE_NEWS_DAYS)


def financial_period_limit(user: User | None) -> int | None:
    if is_pro(user):
        return None
    return FREE_FINANCIAL_QUARTERS


def watchlist_limit(user: User | None) -> int | None:
    if is_pro(user):
        return None
    return FREE_WATCHLIST_LIMIT


def rate_limit_for(
    *,
    user_id: str | None = None,
    plan_tier: str | None = None,
) -> tuple[int, str]:
    if user_id:
        return PRO_RATE_LIMIT, f"user:{user_id}"
    return FREE_RATE_LIMIT, "ip"


def compare_symbol_limit(user: User | None) -> int:
    return PRO_COMPARE_SYMBOLS if is_pro(user) else FREE_COMPARE_SYMBOLS


def _group_active(filters: ScreenerFilters, group: str) -> bool:
    if group == "classification":
        return bool(filters.sectors or filters.boards or filters.index_membership)
    if group == "market_cap":
        return filters.market_cap_min_bn is not None or filters.market_cap_max_bn is not None
    if group == "valuation":
        return any(
            v is not None
            for v in (
                filters.pe_min,
                filters.pe_max,
                filters.pb_min,
                filters.pb_max,
                filters.dividend_yield_min,
                filters.dividend_yield_max,
            )
        )
    if group == "profitability":
        return any(
            v is not None
            for v in (filters.roe_min, filters.roa_min, filters.net_margin_min)
        )
    if group == "leverage":
        return filters.debt_to_equity_max is not None or filters.current_ratio_min is not None
    if group == "momentum":
        return any(
            v is not None
            for v in (
                filters.return_1m_min,
                filters.return_1m_max,
                filters.return_3m_min,
                filters.return_3m_max,
                filters.beta_min,
                filters.beta_max,
            )
        )
    if group == "volume_price":
        return (
            filters.avg_volume_30d_min is not None
            or filters.near_52w_high_pct is not None
        )
    if group == "insider":
        return filters.net_insider_buy_30d is not None or filters.pledged_shares_below_pct is not None
    if group == "ownership":
        return filters.free_float_min is not None or filters.foreign_pct_min is not None
    if group == "sentiment":
        return (
            filters.sentiment_score_min is not None
            or filters.sentiment_momentum_positive is not None
        )
    return False


FILTER_GROUPS = (
    "classification",
    "market_cap",
    "valuation",
    "profitability",
    "leverage",
    "momentum",
    "volume_price",
    "insider",
    "ownership",
    "sentiment",
)


def count_active_filter_groups(filters: ScreenerFilters) -> int:
    return sum(1 for g in FILTER_GROUPS if _group_active(filters, g))


def screener_uses_sentiment_filters(filters: ScreenerFilters) -> bool:
    return _group_active(filters, "sentiment")


def screener_filter_groups_exceeded(user: User | None, filters: ScreenerFilters) -> bool:
    if is_pro(user):
        return False
    return count_active_filter_groups(filters) > FREE_SCREENER_FILTER_GROUPS
