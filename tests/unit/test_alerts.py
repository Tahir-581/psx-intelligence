"""Tests for alert evaluation logic."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.alert import Alert
from backend.models.user import User
from backend.services.alerts import (
    DEDUPE_HOURS,
    _dedupe_blocked,
    _validate_alert_params,
)


def test_validate_price_alert_requires_threshold():
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        _validate_alert_params("price_above", {}, "ENGRO")


def test_validate_price_alert_ok():
    _validate_alert_params("price_above", {"threshold": 200}, "ENGRO")


@pytest.mark.asyncio
async def test_dedupe_blocks_repeat_within_24h():
    alert = Alert(
        id=1,
        user_id="u1",
        symbol="ENGRO",
        alert_type="price_above",
        params_json={"threshold": 200},
        one_shot=False,
        last_triggered_at=datetime.now(UTC) - timedelta(hours=1),
    )
    assert await _dedupe_blocked(alert)


@pytest.mark.asyncio
async def test_dedupe_allows_one_shot():
    alert = Alert(
        id=1,
        user_id="u1",
        symbol="ENGRO",
        alert_type="price_above",
        params_json={"threshold": 200},
        one_shot=True,
        last_triggered_at=datetime.now(UTC) - timedelta(hours=1),
    )
    assert not await _dedupe_blocked(alert)


@pytest.mark.asyncio
async def test_evaluate_price_above_triggers():
    from backend.services.alerts import _evaluate_price_alert

    redis = AsyncMock()
    redis.get = AsyncMock(return_value='{"ltp": 250, "change_pct": 1.5}')
    db = AsyncMock()
    alert = Alert(
        id=1,
        user_id="u1",
        symbol="ENGRO",
        alert_type="price_above",
        params_json={"threshold": 200},
    )
    triggered, payload = await _evaluate_price_alert(db, redis, alert)
    assert triggered
    assert payload["ltp"] == 250


def test_dedupe_hours_constant():
    assert DEDUPE_HOURS == 24
