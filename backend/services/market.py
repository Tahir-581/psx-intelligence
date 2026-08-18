import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.index_constituent import IndexConstituent
from backend.models.price import Price
from backend.models.scraper_run import ScraperRun
from backend.models.ticker import Ticker
from backend.schemas.market import (
    DataHealthResponse,
    MarketSummaryResponse,
    MoverItem,
    PriceBar,
    PriceSeriesResponse,
    ScraperHealthItem,
    SnapshotResponse,
    TickerListItem,
    TickerListResponse,
)
from backend.services.corporate_actions import get_next_dividend_ex_date
from backend.services.fundamentals import get_free_float_pct, get_latest_ratio_map
from backend.services.governance import has_board_change_30d
from backend.services.price_adjustments import apply_adjustments, get_adjustment_factors
from backend.services.risk import compute_beta
from backend.services.technical import compute_indicators, volume_ma


async def symbol_exists(redis: Redis, symbol: str) -> bool:
    cached = await redis.sismember("symbols:whitelist", symbol.upper())
    if cached:
        return True
    return False


async def get_tickers(
    db: AsyncSession,
    redis: Redis,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> TickerListResponse:
    query = select(Ticker).where(Ticker.is_active.is_(True), Ticker.is_debt.is_(False))
    if search:
        pattern = f"%{search.upper()}%"
        query = query.where(
            (Ticker.symbol.ilike(pattern)) | (Ticker.name.ilike(pattern))
        )
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    result = await db.execute(
        query.order_by(Ticker.symbol).offset((page - 1) * page_size).limit(page_size)
    )
    tickers = result.scalars().all()
    items: list[TickerListItem] = []
    for ticker in tickers:
        ltp = None
        change_pct = None
        cached = await redis.get(f"ticker:{ticker.symbol}:snapshot")
        if cached:
            data = json.loads(cached)
            ltp = data.get("ltp")
            change_pct = data.get("change_pct")
        items.append(
            TickerListItem(
                symbol=ticker.symbol,
                name=ticker.name,
                sector=ticker.sector,
                board=ticker.board,
                ltp=ltp,
                change_pct=change_pct,
            )
        )
    return TickerListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_snapshot(db: AsyncSession, redis: Redis, symbol: str) -> SnapshotResponse | None:
    ticker = await db.get(Ticker, symbol.upper())
    if not ticker:
        return None

    ltp = change = change_pct = 0.0
    open_price = high = low = None
    volume = None
    updated_at = None
    cached = await redis.get(f"ticker:{symbol.upper()}:snapshot")
    if cached:
        data = json.loads(cached)
        ltp = float(data.get("ltp", 0))
        change = float(data.get("change", 0))
        change_pct = float(data.get("change_pct", 0))
        open_price = data.get("open")
        high = data.get("high")
        low = data.get("low")
        volume = data.get("volume")
        if data.get("ts"):
            updated_at = datetime.fromisoformat(data["ts"])
    else:
        latest = await db.execute(
            select(Price)
            .where(Price.symbol == symbol.upper())
            .order_by(desc(Price.time))
            .limit(2)
        )
        rows = latest.scalars().all()
        if rows:
            ltp = float(rows[0].close)
            volume = rows[0].volume
            updated_at = rows[0].time
            if len(rows) > 1 and rows[1].close:
                prev = float(rows[1].close)
                change = ltp - prev
                change_pct = (change / prev) * 100 if prev else 0

    year_ago = datetime.now(UTC) - timedelta(days=365)
    stats = await db.execute(
        select(
            func.max(Price.high),
            func.min(Price.low),
            func.avg(Price.volume),
        ).where(Price.symbol == symbol.upper(), Price.time >= year_ago)
    )
    max_high, min_low, avg_vol = stats.one()
    market_cap = None
    if ticker.shares_outstanding and ltp:
        market_cap = ltp * ticker.shares_outstanding

    prev_close = ltp - change if ltp else None

    ratio_map = await get_latest_ratio_map(db, symbol.upper())
    free_float = await get_free_float_pct(db, symbol.upper())
    beta = await compute_beta(db, symbol.upper())
    next_ex = await get_next_dividend_ex_date(db, symbol.upper())
    sector_return_1m = None
    from backend.models.sector_daily_stats import SectorDailyStats

    stats = await db.execute(
        select(SectorDailyStats)
        .where(SectorDailyStats.sector == ticker.sector)
        .order_by(desc(SectorDailyStats.trade_date))
        .limit(1)
    )
    sector_row = stats.scalar_one_or_none()
    if sector_row and sector_row.return_1m is not None:
        sector_return_1m = float(sector_row.return_1m)

    vwap = None
    if cached and open_price and high and low and ltp:
        vwap = (float(open_price) + float(high) + float(low) + ltp) / 4
    circuit_breaker = False
    trading_halt = False
    if cached:
        circuit_breaker = bool(data.get("circuit_breaker"))
        trading_halt = bool(data.get("trading_halt"))
    elif volume == 0 and ltp:
        trading_halt = True

    board_change = await has_board_change_30d(db, symbol.upper())

    return SnapshotResponse(
        symbol=ticker.symbol,
        name=ticker.name,
        sector=ticker.sector,
        board=ticker.board,
        ltp=ltp,
        change=change,
        change_pct=change_pct,
        open=open_price,
        high=high,
        low=low,
        volume=volume,
        market_cap=market_cap,
        fifty_two_week_high=float(max_high) if max_high else None,
        fifty_two_week_low=float(min_low) if min_low else None,
        avg_volume_30d=float(avg_vol) if avg_vol else None,
        shares_outstanding=ticker.shares_outstanding,
        prev_close=prev_close,
        updated_at=updated_at,
        pe_ttm=ratio_map.get("pe_ttm"),
        eps_ttm=ratio_map.get("eps_ttm"),
        dividend_yield=ratio_map.get("dividend_yield"),
        free_float_pct=free_float,
        beta=beta,
        sector_return_1m=sector_return_1m,
        next_dividend_ex_date=next_ex,
        vwap=vwap,
        circuit_breaker=circuit_breaker,
        trading_halt=trading_halt,
        board_change_30d=board_change,
    )


async def get_prices(
    db: AsyncSession,
    symbol: str,
    *,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    overlay: str | None = None,
    adjusted: bool = False,
    overlays: str | None = None,
) -> PriceSeriesResponse:
    query = select(Price).where(Price.symbol == symbol.upper())
    if from_dt:
        query = query.where(Price.time >= from_dt)
    if to_dt:
        query = query.where(Price.time <= to_dt)
    result = await db.execute(query.order_by(Price.time.asc()))
    bars = [
        PriceBar(
            time=row.time,
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=row.volume,
        )
        for row in result.scalars().all()
    ]

    if adjusted and bars:
        factors = await get_adjustment_factors(db, symbol.upper())
        bars = apply_adjustments(bars, factors)

    overlay_bars: list[PriceBar] | None = None
    overlay_sym = (overlay or "").upper()
    if overlay_sym in ("KSE100", "SECTOR") and bars:
        o_sym = "KSE100"
        if overlay_sym == "SECTOR":
            ticker = await db.get(Ticker, symbol.upper())
            if ticker and ticker.sector:
                sector_idx = await db.scalar(
                    select(IndexConstituent.index_code)
                    .join(Ticker, Ticker.symbol == IndexConstituent.symbol)
                    .where(Ticker.sector == ticker.sector)
                    .limit(1)
                )
                if sector_idx:
                    o_sym = sector_idx
        oquery = select(Price).where(Price.symbol == o_sym)
        if from_dt:
            oquery = oquery.where(Price.time >= from_dt)
        if to_dt:
            oquery = oquery.where(Price.time <= to_dt)
        oresult = await db.execute(oquery.order_by(Price.time.asc()))
        raw_overlay = [
            PriceBar(
                time=row.time,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=row.volume,
            )
            for row in oresult.scalars().all()
        ]
        if raw_overlay:
            base = raw_overlay[0].close
            overlay_bars = [
                PriceBar(
                    time=b.time,
                    open=(b.open / base) * 100,
                    high=(b.high / base) * 100,
                    low=(b.low / base) * 100,
                    close=(b.close / base) * 100,
                    volume=b.volume,
                )
                for b in raw_overlay
            ]

    indicator_series = None
    vol_ma = None
    if overlays and bars:
        overlay_list = [o.strip() for o in overlays.split(",") if o.strip()]
        indicator_series = compute_indicators(bars, overlay_list)
        vol_ma = [{"time": t.isoformat(), "value": v} for t, v in volume_ma(bars, 20)]

    return PriceSeriesResponse(
        symbol=symbol.upper(),
        bars=bars,
        overlay_bars=overlay_bars,
        indicator_series=indicator_series,
        volume_ma=vol_ma,
    )


from scrapers.psx.eod_prices import INDEX_SYMBOLS


async def get_stale_index_symbols(db: AsyncSession) -> list[str]:
    """Index symbols whose latest EOD bar is older than expected (weekend-aware)."""
    now = datetime.now(UTC)
    # Allow up to 4 calendar days to cover weekends and holidays.
    cutoff = now - timedelta(days=4)
    stale: list[str] = []
    for sym in INDEX_SYMBOLS:
        latest = await db.scalar(select(func.max(Price.time)).where(Price.symbol == sym))
        if latest is None or latest < cutoff:
            stale.append(sym)
    return stale


async def get_data_health(db: AsyncSession) -> DataHealthResponse:
    subq = (
        select(
            ScraperRun.scraper_name,
            func.max(ScraperRun.id).label("max_id"),
        )
        .group_by(ScraperRun.scraper_name)
        .subquery()
    )
    result = await db.execute(
        select(ScraperRun).join(subq, ScraperRun.id == subq.c.max_id)
    )
    scrapers = [
        ScraperHealthItem(
            scraper_name=row.scraper_name,
            last_success_at=row.last_success_at,
            last_run_at=row.last_run_at,
            records_ingested=row.records_ingested,
            error_message=row.error_message,
        )
        for row in result.scalars().all()
    ]
    stale_indices = await get_stale_index_symbols(db)
    return DataHealthResponse(scrapers=scrapers, stale_index_symbols=stale_indices)


async def get_market_summary(db: AsyncSession, redis: Redis) -> MarketSummaryResponse:
    from scrapers.psx.client import is_market_open

    index_row = await db.execute(
        select(Price).where(Price.symbol == "KSE100").order_by(desc(Price.time)).limit(2)
    )
    index_prices = index_row.scalars().all()
    index_level = float(index_prices[0].close) if index_prices else None
    index_change_pct = None
    if len(index_prices) == 2 and index_prices[1].close:
        prev = float(index_prices[1].close)
        index_change_pct = ((index_level - prev) / prev) * 100 if prev and index_level else None

    latest_day = await db.scalar(select(func.max(Price.time)))
    movers: list[MoverItem] = []
    advances = declines = unchanged = 0
    if latest_day:
        day_start = latest_day.replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(Ticker, Price)
            .join(Price, Price.symbol == Ticker.symbol)
            .where(
                Price.time >= day_start,
                Ticker.is_debt.is_(False),
                Ticker.is_active.is_(True),
            )
            .order_by(desc(Price.time))
        )
        seen: set[str] = set()
        for ticker, price in result.all():
            if ticker.symbol in seen:
                continue
            seen.add(ticker.symbol)
            prev_result = await db.execute(
                select(Price.close)
                .where(Price.symbol == ticker.symbol, Price.time < price.time)
                .order_by(desc(Price.time))
                .limit(1)
            )
            prev_close = prev_result.scalar_one_or_none()
            ltp = float(price.close)
            change_pct = 0.0
            if prev_close and float(prev_close) > 0:
                change_pct = ((ltp - float(prev_close)) / float(prev_close)) * 100
            if change_pct > 0.01:
                advances += 1
            elif change_pct < -0.01:
                declines += 1
            else:
                unchanged += 1
            movers.append(
                MoverItem(
                    symbol=ticker.symbol,
                    name=ticker.name,
                    sector=ticker.sector,
                    ltp=ltp,
                    change_pct=change_pct,
                    volume=price.volume,
                )
            )
    gainers = sorted(movers, key=lambda m: m.change_pct, reverse=True)[:10]
    losers = sorted(movers, key=lambda m: m.change_pct)[:10]
    return MarketSummaryResponse(
        index_level=index_level,
        index_change_pct=index_change_pct,
        advances=advances,
        declines=declines,
        unchanged=unchanged,
        top_gainers=gainers,
        top_losers=losers,
        market_open=is_market_open(),
    )
