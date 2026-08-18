"""Unit tests for corporate action parser."""

from datetime import UTC, datetime

from parsers.corporate_actions import parse_corporate_actions


def test_cash_dividend_extraction():
    published = datetime(2024, 3, 15, tzinfo=UTC)
    results = parse_corporate_actions(
        symbol="ENGRO",
        title="Cash Dividend - Final dividend of Rs. 45 per share",
        body_text="Ex-dividend date: 25-Mar-2024. Book closure from 27-Mar-2024.",
        category="dividend",
        published_at=published,
        source_announcement_id=1,
    )
    assert len(results) >= 1
    div = next(r for r in results if r.action_type == "cash_dividend")
    assert div.amount_per_share == 45
    assert div.ex_date is not None


def test_bonus_shares_ratio():
    published = datetime(2023, 6, 1, tzinfo=UTC)
    results = parse_corporate_actions(
        symbol="LUCK",
        title="Bonus Shares - 20% bonus shares",
        body_text="Book closure date 15-06-2023",
        category="bonus_shares",
        published_at=published,
    )
    assert any(r.action_type == "bonus_shares" for r in results)
    bonus = next(r for r in results if r.action_type == "bonus_shares")
    assert bonus.ratio == "20%"


def test_agm_extraction():
    published = datetime(2024, 1, 10, tzinfo=UTC)
    results = parse_corporate_actions(
        symbol="MCB",
        title="Notice of Annual General Meeting",
        body_text="AGM will be held on 28-Mar-2024 at Karachi.",
        category="agm_egm",
        published_at=published,
    )
    assert any(r.action_type == "agm" for r in results)
