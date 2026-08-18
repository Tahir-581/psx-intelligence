from datetime import date
from decimal import Decimal

from parsers.confidence import (
    needs_review,
    score_financial_parse,
    score_insider_parse,
    score_ownership_parse,
)
from parsers.schemas import (
    ParsedFinancialPeriod,
    ParsedInsiderTrade,
    ParsedLineItem,
    ParsedOwnershipRow,
    ParsedOwnershipSnapshot,
)


def test_score_financial_parse() -> None:
    result = ParsedFinancialPeriod(
        symbol="ENGRO",
        period_end=date(2024, 9, 30),
        period_type="quarterly",
        fiscal_year=2024,
        fiscal_quarter=3,
        line_items=[
            ParsedLineItem(line_code="revenue", value=Decimal("1000"), unit="millions"),
            ParsedLineItem(line_code="pat", value=Decimal("100"), unit="millions"),
            ParsedLineItem(line_code="eps_basic", value=Decimal("5"), unit="absolute"),
        ],
    )
    score = score_financial_parse(result)
    assert score >= 0.5
    assert not needs_review(0.85)
    assert needs_review(0.5)


def test_score_insider_parse() -> None:
    trades = [
        ParsedInsiderTrade(
            director_name="John Doe",
            transaction_date=date(2024, 1, 15),
            transaction_type="buy",
            shares=1000,
        )
    ]
    assert score_insider_parse(trades) == 1.0


def test_score_ownership_parse() -> None:
    result = ParsedOwnershipSnapshot(
        symbol="ENGRO",
        as_of_date=date(2024, 6, 30),
        rows=[
            ParsedOwnershipRow(
                holder_category="sponsors", shares=1000000, pct_outstanding=Decimal("40")
            ),
            ParsedOwnershipRow(
                holder_category="public", shares=800000, pct_outstanding=Decimal("35")
            ),
            ParsedOwnershipRow(
                holder_category="institutions", shares=500000, pct_outstanding=Decimal("25")
            ),
        ],
    )
    score = score_ownership_parse(result)
    assert score >= 0.7
