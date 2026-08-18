"""Stock screener query engine."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import and_, case, desc, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.entitlements import (
    FREE_SCREENER_FILTER_GROUPS,
    PRO_SCREENER_PRESET_LIMIT,
    count_active_filter_groups,
    is_pro,
    screener_filter_groups_exceeded,
    screener_uses_sentiment_filters,
)
from backend.models.computed_ratio import ComputedRatio
from backend.models.index_constituent import IndexConstituent
from backend.models.insider_trade import InsiderTrade
from backend.models.ownership import OwnershipSnapshot
from backend.models.price import Price
from backend.models.screener_preset import ScreenerPreset
from backend.models.sentiment_score import SentimentScore
from backend.models.ticker import Ticker
from backend.models.user import User
from backend.schemas.screener import (
    ScreenerFilters,
    ScreenerPresetCreate,
    ScreenerPresetItem,
    ScreenerPresetListResponse,
    ScreenerRequest,
    ScreenerResponse,
    ScreenerResultRow,
)
from backend.services.cache import cache_get_json, cache_set_json
from backend.services.ratios import batch_upsert_symbol_ratios
from backend.services.risk import get_beta

RATIO_FIELDS = ("pe_ttm", "roe", "debt_to_equity", "dividend_yield")

SORT_COLUMNS = {
    "symbol": "symbol",
    "name": "name",
    "sector": "sector",
    "ltp": "ltp",
    "change_pct": "change_pct",
    "market_cap": "market_cap",
    "pe_ttm": "pe_ttm",
    "roe": "roe",
    "debt_to_equity": "debt_to_equity",
    "dividend_yield": "dividend_yield",
    "avg_volume_30d": "avg_volume_30d",
    "beta": "beta",
}

RATIO_FILTER_MAP = {
    "pe_min": ("pe_ttm", ">="),
    "pe_max": ("pe_ttm", "<="),
    "pb_min": ("pb", ">="),
    "pb_max": ("pb", "<="),
    "dividend_yield_min": ("dividend_yield", ">="),
    "dividend_yield_max": ("dividend_yield", "<="),
    "roe_min": ("roe", ">="),
    "roa_min": ("roa", ">="),
    "net_margin_min": ("net_margin", ">="),
    "debt_to_equity_max": ("debt_to_equity", "<="),
    "current_ratio_min": ("current_ratio", ">="),
}

SCREENER_CACHE_TTL = 300


async def _fetch_betas_for_symbols(
    db: AsyncSession,
    redis: Redis,
    symbols: list[str],
) -> dict[str, float | None]:
    async def _safe_beta(symbol: str) -> tuple[str, float | None]:
        try:
            resp = await get_beta(db, redis, symbol)
            return symbol, resp.beta if resp else None
        except Exception:
            return symbol, None

    if not symbols:
        return {}
    pairs = await asyncio.gather(*[_safe_beta(symbol) for symbol in symbols])
    return dict(pairs)


async def _fetch_latest_ratios_for_symbols(
    db: AsyncSession,
    symbols: list[str],
) -> dict[str, dict[str, float]]:
    if not symbols:
        return {}
    result = await db.execute(
        select(ComputedRatio)
        .where(ComputedRatio.symbol.in_(symbols))
        .order_by(ComputedRatio.symbol, desc(ComputedRatio.period_end))
    )
    out: dict[str, dict[str, float]] = {}
    seen_period: dict[str, datetime] = {}
    for row in result.scalars().all():
        if row.symbol not in seen_period:
            seen_period[row.symbol] = row.period_end
        if row.period_end != seen_period[row.symbol]:
            continue
        if row.value is not None:
            out.setdefault(row.symbol, {})[row.ratio_code] = float(row.value)
    return out


def _row_missing_all_ratios(row: Any) -> bool:
    return all(getattr(row, field, None) is None for field in RATIO_FIELDS)


def _ratio_value(row: Any, symbol: str, field: str, overrides: dict[str, dict[str, float]]) -> float | None:
    raw = getattr(row, field, None)
    if raw is not None:
        return float(raw)
    override = overrides.get(symbol, {}).get(field)
    return float(override) if override is not None else None


def _cache_key(body: ScreenerRequest) -> str:
    payload = body.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"screener:{digest}"


def _latest_ratio_subquery(ratio_code: str):
    ranked = (
        select(
            ComputedRatio.symbol,
            ComputedRatio.value,
            func.row_number()
            .over(
                partition_by=ComputedRatio.symbol,
                order_by=desc(ComputedRatio.period_end),
            )
            .label("rn"),
        )
        .where(ComputedRatio.ratio_code == ratio_code)
        .subquery()
    )
    return (
        select(ranked.c.symbol, ranked.c.value.label(ratio_code))
        .where(ranked.c.rn == 1)
        .subquery()
    )


def _latest_price_subquery():
    latest_time = (
        select(Price.symbol, func.max(Price.time).label("max_time"))
        .group_by(Price.symbol)
        .subquery()
    )
    return (
        select(
            Price.symbol,
            Price.close.label("ltp"),
            Price.volume.label("latest_volume"),
        )
        .join(
            latest_time,
            and_(Price.symbol == latest_time.c.symbol, Price.time == latest_time.c.max_time),
        )
        .subquery()
    )


def _price_stats_subquery():
    since_1y = datetime.now(UTC) - timedelta(days=365)
    since_30d = datetime.now(UTC) - timedelta(days=30)
    since_90d = datetime.now(UTC) - timedelta(days=90)
    return (
        select(
            Price.symbol,
            func.max(Price.high).label("high_52w"),
            func.min(Price.low).label("low_52w"),
            func.avg(case((Price.time >= since_30d, Price.volume), else_=None)).label(
                "avg_volume_30d"
            ),
        )
        .where(Price.time >= since_1y)
        .group_by(Price.symbol)
        .subquery()
    )


def _return_subquery(days: int, label: str):
    cutoff = datetime.now(UTC) - timedelta(days=days)
    latest = _latest_price_subquery()
    past = (
        select(
            Price.symbol,
            Price.close.label("past_close"),
            func.row_number()
            .over(partition_by=Price.symbol, order_by=desc(Price.time))
            .label("rn"),
        )
        .where(Price.time <= cutoff)
        .subquery()
    )
    past_price = select(past.c.symbol, past.c.past_close).where(past.c.rn == 1).subquery()
    return (
        select(
            latest.c.symbol,
            (
                (latest.c.ltp - past_price.c.past_close)
                / func.nullif(past_price.c.past_close, 0)
                * 100
            ).label(label),
        )
        .outerjoin(past_price, latest.c.symbol == past_price.c.symbol)
        .subquery()
    )


def _insider_net_subquery():
    since = datetime.now(UTC).date() - timedelta(days=30)
    buy_types = ("buy", "unpledge")
    net_expr = func.sum(
        case(
            (InsiderTrade.transaction_type.in_(buy_types), InsiderTrade.shares),
            else_=-InsiderTrade.shares,
        )
    )
    return (
        select(InsiderTrade.symbol, net_expr.label("net_insider_30d"))
        .where(InsiderTrade.transaction_date >= since)
        .group_by(InsiderTrade.symbol)
        .subquery()
    )


def _ownership_latest_subquery():
    latest_date_sq = (
        select(
            OwnershipSnapshot.symbol,
            func.max(OwnershipSnapshot.as_of_date).label("max_date"),
        )
        .group_by(OwnershipSnapshot.symbol)
        .subquery()
    )
    return (
        select(
            OwnershipSnapshot.symbol,
            func.max(
                case(
                    (
                        OwnershipSnapshot.holder_category.in_(
                            ("public", "general_public")
                        ),
                        OwnershipSnapshot.pct_outstanding,
                    ),
                    else_=None,
                )
            ).label("free_float_pct"),
            func.max(
                case(
                    (
                        OwnershipSnapshot.holder_category.ilike("%foreign%"),
                        OwnershipSnapshot.pct_outstanding,
                    ),
                    else_=None,
                )
            ).label("foreign_pct"),
            func.max(OwnershipSnapshot.pledged_shares_pct).label("pledged_shares_pct"),
        )
        .join(
            latest_date_sq,
            and_(
                OwnershipSnapshot.symbol == latest_date_sq.c.symbol,
                OwnershipSnapshot.as_of_date == latest_date_sq.c.max_date,
            ),
        )
        .group_by(OwnershipSnapshot.symbol)
        .subquery()
    )


def _sentiment_latest_subquery():
    ranked = (
        select(
            SentimentScore.symbol,
            SentimentScore.score,
            func.row_number()
            .over(
                partition_by=SentimentScore.symbol,
                order_by=desc(SentimentScore.time),
            )
            .label("rn"),
        )
        .where(SentimentScore.source == "aggregate")
        .subquery()
    )
    return (
        select(ranked.c.symbol, ranked.c.score.label("sentiment_score"))
        .where(ranked.c.rn == 1)
        .subquery()
    )


def _sentiment_momentum_subquery():
    since = datetime.now(UTC) - timedelta(days=7)
    agg = (
        select(
            SentimentScore.symbol,
            SentimentScore.time,
            SentimentScore.score,
            func.row_number()
            .over(partition_by=SentimentScore.symbol, order_by=desc(SentimentScore.time))
            .label("rn"),
        )
        .where(SentimentScore.source == "aggregate", SentimentScore.time >= since)
        .subquery()
    )
    latest = select(agg.c.symbol, agg.c.score.label("s_latest")).where(agg.c.rn == 1).subquery()
    prior = select(agg.c.symbol, agg.c.score.label("s_prior")).where(agg.c.rn == 4).subquery()
    return (
        select(
            latest.c.symbol,
            (latest.c.s_latest - prior.c.s_prior).label("sentiment_momentum"),
        )
        .outerjoin(prior, latest.c.symbol == prior.c.symbol)
        .subquery()
    )


async def run_screener(
    db: AsyncSession,
    redis: Redis,
    body: ScreenerRequest,
    user: User | None,
) -> ScreenerResponse:
    filters = body.filters
    if screener_filter_groups_exceeded(user, filters):
        raise HTTPException(
            status_code=403,
            detail=f"Free plan limited to {FREE_SCREENER_FILTER_GROUPS} filter groups. Upgrade to Pro.",
        )
    if screener_uses_sentiment_filters(filters) and not is_pro(user):
        raise HTTPException(
            status_code=403,
            detail="Sentiment filters require Pro subscription.",
        )

    cache_key = _cache_key(body)
    cached = await cache_get_json(redis, cache_key)
    if cached:
        return ScreenerResponse(**cached)

    pe_sq = _latest_ratio_subquery("pe_ttm")
    roe_sq = _latest_ratio_subquery("roe")
    de_sq = _latest_ratio_subquery("debt_to_equity")
    dy_sq = _latest_ratio_subquery("dividend_yield")
    pb_sq = _latest_ratio_subquery("pb")
    roa_sq = _latest_ratio_subquery("roa")
    nm_sq = _latest_ratio_subquery("net_margin")
    cr_sq = _latest_ratio_subquery("current_ratio")
    price_sq = _latest_price_subquery()
    stats_sq = _price_stats_subquery()
    ret_1m_sq = _return_subquery(30, "return_1m")
    ret_3m_sq = _return_subquery(90, "return_3m")
    insider_sq = _insider_net_subquery()
    ownership_sq = _ownership_latest_subquery()
    sentiment_sq = _sentiment_latest_subquery()
    sentiment_mom_sq = _sentiment_momentum_subquery()

    market_cap_expr = (
        price_sq.c.ltp * Ticker.shares_outstanding / literal(1_000_000_000.0)
    ).label("market_cap")

    query = (
        select(
            Ticker.symbol,
            Ticker.name,
            Ticker.sector,
            price_sq.c.ltp,
            market_cap_expr,
            pe_sq.c.pe_ttm,
            roe_sq.c.roe,
            de_sq.c.debt_to_equity,
            dy_sq.c.dividend_yield,
            stats_sq.c.avg_volume_30d,
            stats_sq.c.high_52w,
            ret_1m_sq.c.return_1m,
            ret_3m_sq.c.return_3m,
            insider_sq.c.net_insider_30d,
            ownership_sq.c.free_float_pct,
            ownership_sq.c.foreign_pct,
            sentiment_sq.c.sentiment_score,
            sentiment_mom_sq.c.sentiment_momentum,
        )
        .select_from(Ticker)
        .outerjoin(price_sq, Ticker.symbol == price_sq.c.symbol)
        .outerjoin(pe_sq, Ticker.symbol == pe_sq.c.symbol)
        .outerjoin(roe_sq, Ticker.symbol == roe_sq.c.symbol)
        .outerjoin(de_sq, Ticker.symbol == de_sq.c.symbol)
        .outerjoin(dy_sq, Ticker.symbol == dy_sq.c.symbol)
        .outerjoin(pb_sq, Ticker.symbol == pb_sq.c.symbol)
        .outerjoin(roa_sq, Ticker.symbol == roa_sq.c.symbol)
        .outerjoin(nm_sq, Ticker.symbol == nm_sq.c.symbol)
        .outerjoin(cr_sq, Ticker.symbol == cr_sq.c.symbol)
        .outerjoin(stats_sq, Ticker.symbol == stats_sq.c.symbol)
        .outerjoin(ret_1m_sq, Ticker.symbol == ret_1m_sq.c.symbol)
        .outerjoin(ret_3m_sq, Ticker.symbol == ret_3m_sq.c.symbol)
        .outerjoin(insider_sq, Ticker.symbol == insider_sq.c.symbol)
        .outerjoin(ownership_sq, Ticker.symbol == ownership_sq.c.symbol)
        .outerjoin(sentiment_sq, Ticker.symbol == sentiment_sq.c.symbol)
        .outerjoin(sentiment_mom_sq, Ticker.symbol == sentiment_mom_sq.c.symbol)
        .where(Ticker.is_active.is_(True), Ticker.is_debt.is_(False))
    )

    if filters.sectors:
        query = query.where(Ticker.sector.in_(filters.sectors))
    if filters.boards:
        query = query.where(Ticker.board.in_(filters.boards))
    if filters.index_membership:
        idx_sq = (
            select(IndexConstituent.symbol)
            .where(IndexConstituent.index_code.in_(filters.index_membership))
            .distinct()
        )
        query = query.where(Ticker.symbol.in_(idx_sq))

    if filters.market_cap_min_bn is not None:
        query = query.where(market_cap_expr >= filters.market_cap_min_bn)
    if filters.market_cap_max_bn is not None:
        query = query.where(market_cap_expr <= filters.market_cap_max_bn)

    for field, (code, op) in RATIO_FILTER_MAP.items():
        val = getattr(filters, field, None)
        if val is None:
            continue
        col_map = {
            "pe_ttm": pe_sq.c.pe_ttm,
            "pb": pb_sq.c.pb,
            "dividend_yield": dy_sq.c.dividend_yield,
            "roe": roe_sq.c.roe,
            "roa": roa_sq.c.roa,
            "net_margin": nm_sq.c.net_margin,
            "debt_to_equity": de_sq.c.debt_to_equity,
            "current_ratio": cr_sq.c.current_ratio,
        }
        col = col_map[code]
        if op == ">=":
            query = query.where(col >= val)
        else:
            query = query.where(col <= val)

    if filters.return_1m_min is not None:
        query = query.where(ret_1m_sq.c.return_1m >= filters.return_1m_min)
    if filters.return_1m_max is not None:
        query = query.where(ret_1m_sq.c.return_1m <= filters.return_1m_max)
    if filters.return_3m_min is not None:
        query = query.where(ret_3m_sq.c.return_3m >= filters.return_3m_min)
    if filters.return_3m_max is not None:
        query = query.where(ret_3m_sq.c.return_3m <= filters.return_3m_max)

    if filters.avg_volume_30d_min is not None:
        query = query.where(stats_sq.c.avg_volume_30d >= filters.avg_volume_30d_min)
    if filters.near_52w_high_pct is not None and price_sq.c.ltp is not None:
        threshold = 1.0 - filters.near_52w_high_pct / 100.0
        query = query.where(price_sq.c.ltp >= stats_sq.c.high_52w * threshold)

    if filters.net_insider_buy_30d is True:
        query = query.where(insider_sq.c.net_insider_30d > 0)
    elif filters.net_insider_buy_30d is False:
        query = query.where(
            (insider_sq.c.net_insider_30d <= 0) | (insider_sq.c.net_insider_30d.is_(None))
        )

    if filters.free_float_min is not None:
        query = query.where(ownership_sq.c.free_float_pct >= filters.free_float_min)
    if filters.foreign_pct_min is not None:
        query = query.where(ownership_sq.c.foreign_pct >= filters.foreign_pct_min)
    if filters.pledged_shares_below_pct is not None:
        query = query.where(
            (ownership_sq.c.pledged_shares_pct <= filters.pledged_shares_below_pct)
            | (ownership_sq.c.pledged_shares_pct.is_(None))
        )

    if filters.sentiment_score_min is not None:
        query = query.where(sentiment_sq.c.sentiment_score >= filters.sentiment_score_min)
    if filters.sentiment_momentum_positive is True:
        query = query.where(sentiment_mom_sq.c.sentiment_momentum > 0)
    elif filters.sentiment_momentum_positive is False:
        query = query.where(sentiment_mom_sq.c.sentiment_momentum <= 0)

    count_q = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_q) or 0

    sort_col = SORT_COLUMNS.get(body.sort_by, "symbol")
    sort_map: dict[str, Any] = {
        "symbol": Ticker.symbol,
        "name": Ticker.name,
        "sector": Ticker.sector,
        "ltp": price_sq.c.ltp,
        "market_cap": market_cap_expr,
        "pe_ttm": pe_sq.c.pe_ttm,
        "roe": roe_sq.c.roe,
        "debt_to_equity": de_sq.c.debt_to_equity,
        "dividend_yield": dy_sq.c.dividend_yield,
        "avg_volume_30d": stats_sq.c.avg_volume_30d,
    }
    order_col = sort_map.get(sort_col, Ticker.symbol)
    order = desc(order_col) if body.sort_dir.lower() == "desc" else order_col.asc()

    result = await db.execute(
        query.order_by(order).offset((body.page - 1) * body.page_size).limit(body.page_size)
    )
    rows = result.all()

    missing_ratio_symbols = [row.symbol for row in rows if _row_missing_all_ratios(row)]
    ratio_overrides: dict[str, dict[str, float]] = {}
    if missing_ratio_symbols:
        await asyncio.to_thread(batch_upsert_symbol_ratios, missing_ratio_symbols)
        ratio_overrides = await _fetch_latest_ratios_for_symbols(db, missing_ratio_symbols)

    beta_map = await _fetch_betas_for_symbols(db, redis, [row.symbol for row in rows])

    items: list[ScreenerResultRow] = []
    for row in rows:
        ltp = float(row.ltp) if row.ltp is not None else None
        change_pct = None
        cached_snap = await redis.get(f"ticker:{row.symbol}:snapshot")
        if cached_snap:
            data = json.loads(cached_snap)
            ltp = float(data.get("ltp", ltp or 0)) or ltp
            change_pct = data.get("change_pct")

        items.append(
            ScreenerResultRow(
                symbol=row.symbol,
                name=row.name,
                sector=row.sector,
                ltp=ltp,
                change_pct=float(change_pct) if change_pct is not None else None,
                market_cap=float(row.market_cap) if row.market_cap is not None else None,
                pe_ttm=_ratio_value(row, row.symbol, "pe_ttm", ratio_overrides),
                roe=_ratio_value(row, row.symbol, "roe", ratio_overrides),
                debt_to_equity=_ratio_value(row, row.symbol, "debt_to_equity", ratio_overrides),
                dividend_yield=_ratio_value(row, row.symbol, "dividend_yield", ratio_overrides),
                avg_volume_30d=float(row.avg_volume_30d) if row.avg_volume_30d is not None else None,
                beta=beta_map.get(row.symbol),
            )
        )

    if body.sort_by == "beta":
        reverse = body.sort_dir.lower() == "desc"
        items.sort(key=lambda x: x.beta if x.beta is not None else float("-inf"), reverse=reverse)

    response = ScreenerResponse(
        items=items,
        total=total,
        page=body.page,
        page_size=body.page_size,
        filter_groups_active=count_active_filter_groups(filters),
        filter_groups_limit=FREE_SCREENER_FILTER_GROUPS if not is_pro(user) else None,
    )
    await cache_set_json(redis, cache_key, response.model_dump(mode="json"), SCREENER_CACHE_TTL)
    return response


async def list_presets(db: AsyncSession, user: User) -> ScreenerPresetListResponse:
    rows = (
        await db.execute(
            select(ScreenerPreset)
            .where(ScreenerPreset.user_id == user.id)
            .order_by(ScreenerPreset.name)
        )
    ).scalars().all()
    items = [
        ScreenerPresetItem(
            id=p.id,
            name=p.name,
            filters=ScreenerFilters.model_validate(p.filters_json),
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in rows
    ]
    return ScreenerPresetListResponse(
        items=items,
        limit=PRO_SCREENER_PRESET_LIMIT,
        count=len(items),
    )


async def create_preset(
    db: AsyncSession, user: User, body: ScreenerPresetCreate
) -> ScreenerPresetItem:
    count = await db.scalar(
        select(func.count())
        .select_from(ScreenerPreset)
        .where(ScreenerPreset.user_id == user.id)
    ) or 0
    if count >= PRO_SCREENER_PRESET_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=f"Maximum {PRO_SCREENER_PRESET_LIMIT} screener presets allowed.",
        )
    existing = await db.scalar(
        select(ScreenerPreset).where(
            ScreenerPreset.user_id == user.id, ScreenerPreset.name == body.name
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Preset name already exists.")
    preset = ScreenerPreset(
        user_id=user.id,
        name=body.name,
        filters_json=body.filters.model_dump(mode="json"),
    )
    db.add(preset)
    await db.commit()
    await db.refresh(preset)
    return ScreenerPresetItem(
        id=preset.id,
        name=preset.name,
        filters=body.filters,
        created_at=preset.created_at.isoformat(),
        updated_at=preset.updated_at.isoformat(),
    )


async def delete_preset(db: AsyncSession, user: User, preset_id: int) -> None:
    preset = await db.scalar(
        select(ScreenerPreset).where(
            ScreenerPreset.id == preset_id, ScreenerPreset.user_id == user.id
        )
    )
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found.")
    await db.delete(preset)
    await db.commit()


def screener_results_to_csv(items: list[ScreenerResultRow]) -> str:
    headers = [
        "symbol",
        "name",
        "sector",
        "ltp",
        "change_pct",
        "market_cap",
        "pe_ttm",
        "roe",
        "debt_to_equity",
        "dividend_yield",
        "avg_volume_30d",
        "beta",
    ]
    lines = [",".join(headers)]
    for item in items:
        vals = [getattr(item, h) for h in headers]
        lines.append(",".join("" if v is None else str(v) for v in vals))
    return "\n".join(lines)
