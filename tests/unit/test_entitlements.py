"""Tests for free vs pro entitlements."""

from backend.auth.entitlements import (
    PRO_COMPARE_SYMBOLS,
    compare_symbol_limit,
    financial_period_limit,
    is_pro,
    news_cutoff,
    screener_filter_groups_exceeded,
    watchlist_limit,
)
from backend.models.user import User
from backend.schemas.screener import ScreenerFilters


def _user(tier: str) -> User:
    return User(id="user_1", email="test@example.com", plan_tier=tier)


def test_is_pro_always_true():
    assert is_pro(None)
    assert is_pro(_user("free"))
    assert is_pro(_user("pro"))


def test_news_cutoff_unlimited():
    assert news_cutoff(_user("free")) is None
    assert news_cutoff(_user("pro")) is None


def test_financial_period_limit_unlimited():
    assert financial_period_limit(_user("free")) is None
    assert financial_period_limit(_user("pro")) is None


def test_watchlist_limit_unlimited():
    assert watchlist_limit(_user("free")) is None
    assert watchlist_limit(_user("pro")) is None


def test_compare_symbol_limit():
    assert compare_symbol_limit(_user("free")) == PRO_COMPARE_SYMBOLS
    assert compare_symbol_limit(_user("pro")) == PRO_COMPARE_SYMBOLS


def test_screener_filter_groups_never_exceeded():
    filters = ScreenerFilters(
        sectors=["Commercial Banks"],
        roe_min=15,
        pe_max=20,
        return_1m_min=5,
    )
    assert not screener_filter_groups_exceeded(_user("free"), filters)
    assert not screener_filter_groups_exceeded(_user("pro"), filters)
