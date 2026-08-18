"""API key schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=100)


class ApiKeyItem(BaseModel):
    id: int
    key_prefix: str
    label: str
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreateResponse(ApiKeyItem):
    key: str


class ApiKeyListResponse(BaseModel):
    items: list[ApiKeyItem]
