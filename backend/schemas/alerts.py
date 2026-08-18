"""Alert schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AlertType = Literal[
    "price_above",
    "price_below",
    "pct_change_day",
    "new_52w_high",
    "new_52w_low",
    "volume_spike",
    "dividend_announced",
    "insider_trade",
    "material_event",
    "credit_rating_change",
    "sentiment_below",
    "sentiment_divergence",
]


class AlertCreate(BaseModel):
    symbol: str | None = None
    alert_type: AlertType
    params_json: dict[str, Any] = Field(default_factory=dict)
    one_shot: bool = False


class AlertUpdate(BaseModel):
    params_json: dict[str, Any] | None = None
    is_active: bool | None = None
    one_shot: bool | None = None


class AlertItem(BaseModel):
    id: int
    symbol: str | None
    alert_type: str
    params_json: dict[str, Any]
    is_active: bool
    one_shot: bool
    last_triggered_at: datetime | None
    created_at: datetime


class AlertListResponse(BaseModel):
    items: list[AlertItem]


class AlertEventItem(BaseModel):
    id: int
    alert_id: int
    symbol: str | None
    triggered_at: datetime
    payload_json: dict[str, Any] | None
    delivered_email: bool
    delivered_in_app: bool


class AlertEventListResponse(BaseModel):
    items: list[AlertEventItem]
    total: int
    page: int
    page_size: int
