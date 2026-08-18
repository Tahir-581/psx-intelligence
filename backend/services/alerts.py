"""Price and event alerts."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.alert import Alert
from backend.models.alert_event import AlertEvent
from backend.models.announcement import Announcement
from backend.models.corporate_action import CorporateAction
from backend.models.insider_trade import InsiderTrade
from backend.models.material_event import MaterialEvent
from backend.models.notification import Notification
from backend.models.price import Price
from backend.models.user import User
from backend.schemas.alerts import (
    AlertCreate,
    AlertEventItem,
    AlertEventListResponse,
    AlertItem,
    AlertListResponse,
    AlertUpdate,
)
from backend.services.email import send_alert_email
from backend.services.intelligence import get_ticker_sentiment

logger = logging.getLogger(__name__)

PRICE_ALERT_TYPES = {
    "price_above",
    "price_below",
    "pct_change_day",
    "new_52w_high",
    "new_52w_low",
    "volume_spike",
}
EVENT_ALERT_TYPES = {
    "dividend_announced",
    "insider_trade",
    "material_event",
    "credit_rating_change",
    "sentiment_below",
    "sentiment_divergence",
}

DEDUPE_HOURS = 24


def _validate_alert_params(alert_type: str, params: dict[str, Any], symbol: str | None) -> None:
    if alert_type in ("price_above", "price_below") and "threshold" not in params:
        raise HTTPException(status_code=422, detail="threshold required for price alerts")
    if alert_type == "pct_change_day" and "pct" not in params:
        raise HTTPException(status_code=422, detail="pct required for pct_change_day alert")
    if alert_type == "volume_spike" and "multiplier" not in params:
        raise HTTPException(status_code=422, detail="multiplier required for volume_spike alert")
    if alert_type == "sentiment_below" and "score_threshold" not in params:
        raise HTTPException(status_code=422, detail="score_threshold required for sentiment_below")
    if alert_type == "pct_change_day" and not symbol:
        raise HTTPException(status_code=422, detail="symbol required unless watchlist-wide pct alert")
    if alert_type not in ("pct_change_day",) and alert_type in PRICE_ALERT_TYPES | EVENT_ALERT_TYPES:
        if alert_type in EVENT_ALERT_TYPES and alert_type != "sentiment_divergence" and not symbol:
            raise HTTPException(status_code=422, detail="symbol required for event alerts")


def _alert_to_item(a: Alert) -> AlertItem:
    return AlertItem(
        id=a.id,
        symbol=a.symbol,
        alert_type=a.alert_type,
        params_json=a.params_json or {},
        is_active=a.is_active,
        one_shot=a.one_shot,
        last_triggered_at=a.last_triggered_at,
        created_at=a.created_at,
    )


async def list_alerts(db: AsyncSession, user: User) -> AlertListResponse:
    rows = (
        await db.execute(
            select(Alert).where(Alert.user_id == user.id).order_by(desc(Alert.created_at))
        )
    ).scalars().all()
    return AlertListResponse(items=[_alert_to_item(a) for a in rows])


async def create_alert(db: AsyncSession, user: User, body: AlertCreate) -> AlertItem:
    sym = body.symbol.upper() if body.symbol else None
    _validate_alert_params(body.alert_type, body.params_json, sym)
    alert = Alert(
        user_id=user.id,
        symbol=sym,
        alert_type=body.alert_type,
        params_json=body.params_json,
        one_shot=body.one_shot,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return _alert_to_item(alert)


async def update_alert(
    db: AsyncSession, user: User, alert_id: int, body: AlertUpdate
) -> AlertItem:
    alert = await db.scalar(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id)
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    if body.params_json is not None:
        alert.params_json = body.params_json
    if body.is_active is not None:
        alert.is_active = body.is_active
    if body.one_shot is not None:
        alert.one_shot = body.one_shot
    await db.commit()
    await db.refresh(alert)
    return _alert_to_item(alert)


async def delete_alert(db: AsyncSession, user: User, alert_id: int) -> None:
    alert = await db.scalar(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id)
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    await db.delete(alert)
    await db.commit()


async def list_alert_events(
    db: AsyncSession, user: User, *, page: int = 1, page_size: int = 20
) -> AlertEventListResponse:
    base = select(AlertEvent).where(AlertEvent.user_id == user.id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = (
        await db.execute(
            base.order_by(desc(AlertEvent.triggered_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return AlertEventListResponse(
        items=[
            AlertEventItem(
                id=e.id,
                alert_id=e.alert_id,
                symbol=e.symbol,
                triggered_at=e.triggered_at,
                payload_json=e.payload_json,
                delivered_email=e.delivered_email,
                delivered_in_app=e.delivered_in_app,
            )
            for e in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


async def _get_snapshot(redis: Redis, symbol: str) -> dict[str, Any] | None:
    raw = await redis.get(f"ticker:{symbol}:snapshot")
    if not raw:
        return None
    return json.loads(raw)


async def _dedupe_blocked(alert: Alert) -> bool:
    if alert.one_shot:
        return False
    if not alert.last_triggered_at:
        return False
    return alert.last_triggered_at > datetime.now(UTC) - timedelta(hours=DEDUPE_HOURS)


async def _fire_alert(
    db: AsyncSession,
    alert: Alert,
    user: User,
    *,
    symbol: str | None,
    payload: dict[str, Any],
    title: str,
    body: str,
    link_url: str | None = None,
) -> None:
    now = datetime.now(UTC)
    notif = Notification(
        user_id=user.id,
        title=title,
        body=body,
        link_url=link_url,
    )
    db.add(notif)
    delivered_email = await send_alert_email(to_email=user.email, subject=title, body=body)
    event = AlertEvent(
        alert_id=alert.id,
        user_id=user.id,
        symbol=symbol,
        triggered_at=now,
        payload_json=payload,
        delivered_email=delivered_email,
        delivered_in_app=True,
    )
    db.add(event)
    alert.last_triggered_at = now
    if alert.one_shot:
        alert.is_active = False


async def _evaluate_price_alert(
    db: AsyncSession, redis: Redis, alert: Alert
) -> tuple[bool, dict[str, Any] | None]:
    if not alert.symbol:
        return False, None
    snap = await _get_snapshot(redis, alert.symbol)
    if not snap:
        return False, None
    ltp = float(snap.get("ltp", 0))
    params = alert.params_json or {}
    at = alert.alert_type

    if at == "price_above":
        return ltp >= float(params["threshold"]), {"ltp": ltp, "threshold": params["threshold"]}
    if at == "price_below":
        return ltp <= float(params["threshold"]), {"ltp": ltp, "threshold": params["threshold"]}
    if at == "pct_change_day":
        change = abs(float(snap.get("change_pct", 0)))
        return change >= float(params["pct"]), {"change_pct": change, "pct": params["pct"]}

    since = datetime.now(UTC) - timedelta(days=365)
    stats = await db.execute(
        select(func.max(Price.high), func.min(Price.low), func.avg(Price.volume))
        .where(Price.symbol == alert.symbol, Price.time >= since)
    )
    high_52w, low_52w, avg_vol = stats.one()
    vol_today = snap.get("volume")

    if at == "new_52w_high" and high_52w:
        return ltp >= float(high_52w), {"ltp": ltp, "high_52w": float(high_52w)}
    if at == "new_52w_low" and low_52w:
        return ltp <= float(low_52w), {"ltp": ltp, "low_52w": float(low_52w)}
    if at == "volume_spike" and avg_vol and vol_today:
        mult = float(params.get("multiplier", 2))
        return float(vol_today) >= float(avg_vol) * mult, {
            "volume": vol_today,
            "avg_volume": float(avg_vol),
            "multiplier": mult,
        }
    return False, None


async def _evaluate_event_alert(
    db: AsyncSession, redis: Redis, alert: Alert
) -> tuple[bool, dict[str, Any] | None]:
    if not alert.symbol:
        return False, None
    sym = alert.symbol
    since = alert.last_triggered_at or alert.created_at
    at = alert.alert_type
    params = alert.params_json or {}

    if at == "dividend_announced":
        row = await db.scalar(
            select(CorporateAction)
            .where(
                CorporateAction.symbol == sym,
                CorporateAction.action_type == "cash_dividend",
                CorporateAction.announced_at > since,
            )
            .order_by(desc(CorporateAction.announced_at))
            .limit(1)
        )
        if row:
            return True, {"action_id": row.id, "amount": float(row.amount_per_share or 0)}
    elif at == "insider_trade":
        row = await db.scalar(
            select(InsiderTrade)
            .where(InsiderTrade.symbol == sym, InsiderTrade.created_at > since)
            .order_by(desc(InsiderTrade.transaction_date))
            .limit(1)
        )
        if row:
            return True, {"trade_id": row.id, "type": row.transaction_type, "shares": row.shares}
    elif at == "material_event":
        row = await db.scalar(
            select(MaterialEvent)
            .where(MaterialEvent.symbol == sym, MaterialEvent.created_at > since)
            .order_by(desc(MaterialEvent.event_date))
            .limit(1)
        )
        if row:
            return True, {"event_id": row.id, "category": row.event_category}
    elif at == "credit_rating_change":
        row = await db.scalar(
            select(Announcement)
            .where(
                Announcement.symbol == sym,
                Announcement.category.ilike("%credit%"),
                Announcement.published_at > since,
            )
            .order_by(desc(Announcement.published_at))
            .limit(1)
        )
        if row:
            return True, {"announcement_id": row.id, "title": row.title}
    elif at == "sentiment_below":
        sent = await get_ticker_sentiment(db, sym, days=7)
        score = sent.current_score
        if score is not None and score < float(params["score_threshold"]):
            return True, {"score": score, "threshold": params["score_threshold"]}
    elif at == "sentiment_divergence":
        sent = await get_ticker_sentiment(db, sym, days=30)
        snap = await _get_snapshot(redis, sym)
        change_1m = float(snap.get("change_pct", 0)) if snap else 0
        mom = sent.momentum_3d
        if mom is not None and change_1m > 0 and mom < -0.1:
            return True, {"change_pct": change_1m, "momentum_3d": mom}

    return False, None


async def evaluate_single_alert(
    db: AsyncSession, redis: Redis, alert: Alert, user: User
) -> bool:
    if not alert.is_active:
        return False
    if await _dedupe_blocked(alert):
        return False

    triggered = False
    payload: dict[str, Any] | None = None
    if alert.alert_type in PRICE_ALERT_TYPES:
        triggered, payload = await _evaluate_price_alert(db, redis, alert)
    elif alert.alert_type in EVENT_ALERT_TYPES:
        triggered, payload = await _evaluate_event_alert(db, redis, alert)

    if triggered and payload is not None:
        sym = alert.symbol or "WATCHLIST"
        title = f"Alert: {alert.alert_type.replace('_', ' ')} — {sym}"
        body = json.dumps(payload, default=str)
        link = f"/ticker/{alert.symbol}" if alert.symbol else None
        await _fire_alert(
            db, alert, user, symbol=alert.symbol, payload=payload, title=title, body=body, link_url=link
        )
        return True
    return False


async def evaluate_all_alerts(
    db: AsyncSession, redis: Redis, *, event_only: bool = False
) -> dict:
    alerts = (
        await db.execute(select(Alert).where(Alert.is_active.is_(True)))
    ).scalars().all()
    fired = 0
    evaluated = 0
    for alert in alerts:
        if event_only and alert.alert_type in PRICE_ALERT_TYPES:
            continue
        if not event_only and alert.alert_type in EVENT_ALERT_TYPES:
            pass  # evaluate all during market hours
        evaluated += 1
        user = await db.get(User, alert.user_id)
        if not user:
            continue
        try:
            if await evaluate_single_alert(db, redis, alert, user):
                fired += 1
        except Exception:
            logger.exception("Alert evaluation failed for alert %s", alert.id)
    await db.commit()
    return {"evaluated": evaluated, "fired": fired}


async def trigger_event_alerts_for_symbols(db: AsyncSession, redis: Redis, symbols: list[str]) -> int:
    if not symbols:
        return 0
    sym_set = {s.upper() for s in symbols}
    alerts = (
        await db.execute(
            select(Alert).where(
                Alert.is_active.is_(True),
                Alert.alert_type.in_(tuple(EVENT_ALERT_TYPES)),
                Alert.symbol.in_(sym_set),
            )
        )
    ).scalars().all()
    fired = 0
    for alert in alerts:
        user = await db.get(User, alert.user_id)
        if not user:
            continue
        try:
            if await evaluate_single_alert(db, redis, alert, user):
                fired += 1
        except Exception:
            logger.exception("Event alert hook failed for %s", alert.id)
    await db.commit()
    return fired
