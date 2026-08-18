"""Unit tests for significance scoring."""

from decimal import Decimal

from nlp.significance import score_event


def test_regulatory_high_significance():
    score = score_event(
        "regulatory",
        "SECP approval granted for new product line",
        Decimal("2000000000"),
    )
    assert score >= 4


def test_small_contract_low_score():
    score = score_event("contract", "Minor supply agreement", Decimal("50000000"))
    assert 1 <= score <= 3


def test_clamped_to_five():
    score = score_event(
        "litigation",
        "SECP investigation SECP SBP NEPRA " + "x" * 600,
        Decimal("15000000000"),
    )
    assert score == 5
