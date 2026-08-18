from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.services.ratios import _safe_div, compute_symbol_ratios


def test_safe_div() -> None:
    assert _safe_div(Decimal("10"), Decimal("2")) == Decimal("5")
    assert _safe_div(Decimal("10"), Decimal("0")) is None
    assert _safe_div(None, Decimal("2")) is None


def test_compute_symbol_ratios_empty() -> None:
    session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    session.scalar.return_value = None
    ratios, period_end = compute_symbol_ratios(session, "ENGRO")
    assert period_end is None
    assert ratios["pe_ttm"] is None
