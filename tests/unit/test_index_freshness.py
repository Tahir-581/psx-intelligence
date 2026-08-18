from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.market import get_stale_index_symbols
from scrapers.psx.eod_prices import INDEX_SYMBOLS


@pytest.mark.asyncio
async def test_get_stale_index_symbols_flags_old_data() -> None:
    db = MagicMock()
    stale_time = datetime.now(UTC) - timedelta(days=10)

    async def scalar(query):
        return stale_time

    db.scalar = AsyncMock(side_effect=scalar)
    stale = await get_stale_index_symbols(db)
    assert stale == INDEX_SYMBOLS


@pytest.mark.asyncio
async def test_get_stale_index_symbols_empty_when_fresh() -> None:
    db = MagicMock()
    fresh_time = datetime.now(UTC) - timedelta(days=1)

    db.scalar = AsyncMock(return_value=fresh_time)
    stale = await get_stale_index_symbols(db)
    assert stale == []
