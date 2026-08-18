"""Pydantic schemas for social post ingestion."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SocialPostRecord(BaseModel):
    source: str = Field(..., pattern="^(twitter|telegram|reddit|news)$")
    external_id: str
    text: str
    posted_at: datetime
    author_handle: str | None = None
    author_followers: int | None = None
    symbol: str | None = None
    engagement_json: dict[str, Any] | None = None
    url: str | None = None

    @field_validator("text")
    @classmethod
    def truncate_text(cls, v: str) -> str:
        return v[:2000] if len(v) > 2000 else v

    @field_validator("symbol")
    @classmethod
    def upper_symbol(cls, v: str | None) -> str | None:
        return v.upper() if v else None
