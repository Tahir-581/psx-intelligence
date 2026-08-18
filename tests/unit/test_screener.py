"""Tests for screener filter logic and cache keys."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.auth.entitlements import (
    FREE_SCREENER_FILTER_GROUPS,
    count_active_filter_groups,
    screener_filter_groups_exceeded,
)
from backend.models.user import User
from backend.schemas.context import BetaResponse
from backend.schemas.screener import ScreenerFilters, ScreenerRequest
from backend.services.screener import (
    SORT_COLUMNS,
    _cache_key,
    _fetch_betas_for_symbols,
    screener_results_to_csv,
)


def _user(tier: str) -> User:
    return User(id="user_1", email="test@example.com", plan_tier=tier)


def test_count_active_filter_groups_empty():
    assert count_active_filter_groups(ScreenerFilters()) == 0


def test_count_active_filter_groups_valuation_and_profitability():
    filters = ScreenerFilters(roe_min=15, debt_to_equity_max=2)
    assert count_active_filter_groups(filters) == 2


def test_filter_groups_unlimited():
    filters = ScreenerFilters(
        sectors=["Commercial Banks"],
        roe_min=15,
        pe_max=20,
        return_1m_min=5,
    )
    assert count_active_filter_groups(filters) == 4
    assert not screener_filter_groups_exceeded(_user("free"), filters)
    assert not screener_filter_groups_exceeded(_user("pro"), filters)


def test_cache_key_stability():
    a = ScreenerRequest(filters=ScreenerFilters(roe_min=15), page=1, sort_by="symbol")
    b = ScreenerRequest(filters=ScreenerFilters(roe_min=15), page=1, sort_by="symbol")
    c = ScreenerRequest(filters=ScreenerFilters(roe_min=20), page=1, sort_by="symbol")
    assert _cache_key(a) == _cache_key(b)
    assert _cache_key(a) != _cache_key(c)


def test_sort_columns_whitelist():
    assert "symbol" in SORT_COLUMNS
    assert "roe" in SORT_COLUMNS
    assert "invalid" not in SORT_COLUMNS


def test_csv_export():
    from backend.schemas.screener import ScreenerResultRow

    rows = [
        ScreenerResultRow(symbol="ENGRO", name="Engro", sector="Chemical", roe=18.5),
    ]
    csv_text = screener_results_to_csv(rows)
    assert "ENGRO" in csv_text
    assert "18.5" in csv_text


def test_free_filter_groups_constant():
    assert FREE_SCREENER_FILTER_GROUPS == 3


@pytest.mark.asyncio
async def test_fetch_betas_for_symbols():
    db = AsyncMock()
    redis = AsyncMock()

    with patch("backend.services.screener.get_beta", new_callable=AsyncMock) as mock_get_beta:
        mock_get_beta.side_effect = [
            BetaResponse(symbol="ENGRO", beta=1.2, sector="Chemical"),
            BetaResponse(symbol="LUCK", beta=0.9, sector="Cement"),
        ]
        result = await _fetch_betas_for_symbols(db, redis, ["ENGRO", "LUCK"])

    assert result == {"ENGRO": 1.2, "LUCK": 0.9}
    assert mock_get_beta.await_count == 2
