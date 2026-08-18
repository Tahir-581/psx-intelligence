"""Tests for portfolio P&L calculations."""

from datetime import date

from backend.schemas.portfolio import HoldingItem, PortfolioSummary


def test_unrealized_pnl_pct():
    cost = 100 * 280.0
    cur = 100 * 300.0
    pnl = cur - cost
    pnl_pct = pnl / cost * 100
    assert round(pnl_pct, 2) == 7.14


def test_sector_weight():
    holdings = [
        ("Banks", 500_000),
        ("Cement", 300_000),
        ("Chemical", 200_000),
    ]
    total = sum(v for _, v in holdings)
    weights = [(s, v / total * 100) for s, v in holdings]
    assert round(weights[0][1], 1) == 50.0
    assert any(w > 30 for _, w in weights)


def test_portfolio_summary_schema():
    summary = PortfolioSummary(
        total_value=1_000_000,
        total_cost=900_000,
        unrealized_pnl=100_000,
        unrealized_pnl_pct=11.11,
        dividend_income_ytd=5000,
        portfolio_beta=1.05,
        sector_exposure=[],
        concentration_warning=False,
        vs_kse100=[],
    )
    assert summary.unrealized_pnl == 100_000


def test_holding_item_pnl():
    h = HoldingItem(
        id=1,
        symbol="ENGRO",
        quantity=100,
        avg_buy_price=280,
        purchase_date=date.fromisoformat("2025-01-01"),
        ltp=300,
        current_value=30000,
        cost_basis=28000,
        unrealized_pnl=2000,
        unrealized_pnl_pct=7.14,
    )
    assert h.unrealized_pnl == 2000
