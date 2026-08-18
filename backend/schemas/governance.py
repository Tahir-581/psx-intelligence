from datetime import date, datetime

from pydantic import BaseModel


class BoardMemberItem(BaseModel):
    name: str
    role: str
    appointment_date: date | None = None
    resignation_date: date | None = None


class SecpFilingItem(BaseModel):
    form_type: str
    filed_at: date
    raw_url: str | None = None


class CcgChecklistItem(BaseModel):
    item: str
    filed: bool


class GovernanceResponse(BaseModel):
    symbol: str
    board: list[BoardMemberItem]
    director_changes: list[BoardMemberItem]
    board_change_30d: bool
    filings: list[SecpFilingItem]
    ccg_checklist: list[dict]


class CreditRatingItem(BaseModel):
    agency: str
    rating: str
    outlook: str | None = None
    effective_date: date
    source_url: str | None = None


class CreditRatingsResponse(BaseModel):
    symbol: str
    ratings: list[CreditRatingItem]
