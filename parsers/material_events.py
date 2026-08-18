"""Rule-based material event extraction from PSX announcements."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from nlp.significance import score_event
from parsers.corporate_actions import _parse_date_fragment
from parsers.schemas import ParsedMaterialEvent

EVENT_RULES: list[tuple[str, str]] = [
    (r"off[- ]?take|supply agreement|contract|purchase order", "contract"),
    (r"joint venture|\bjv\b|mou|memorandum of understanding|partnership", "jv"),
    (r"secp|sbp|nepra|ogra|pta.*approv|regulatory approv", "regulatory"),
    (r"litigation|court|arbitration|lawsuit|legal proceeding", "litigation"),
    (r"capacity|expansion|capex|plant|commissioning|greenfield|brownfield", "capex"),
    (r"pacra|vis rating|credit rating", "credit_rating"),
    (r"force majeure|shutdown|curtailment|outage|fire incident", "force_majeure"),
    (r"loan|facility|financing|credit line|term finance", "loan"),
]

AMOUNT_PATTERN = re.compile(
    r"(?:rs\.?|pkr)\s*([\d,]+(?:\.\d+)?)\s*(million|billion|mn|bn|m|b)?",
    re.IGNORECASE,
)
COUNTERPARTY_PATTERN = re.compile(
    r"(?:with|between|from|to)\s+([A-Z][A-Za-z0-9\s&.-]{2,60}?)(?:\s+(?:for|to|on|dated))",
    re.IGNORECASE,
)


def _extract_amount_pkr(text: str) -> Decimal | None:
    m = AMOUNT_PATTERN.search(text)
    if not m:
        return None
    try:
        value = Decimal(m.group(1).replace(",", ""))
    except InvalidOperation:
        return None
    multiplier = (m.group(2) or "").lower()
    if multiplier in ("million", "mn", "m"):
        value *= Decimal("1000000")
    elif multiplier in ("billion", "bn", "b"):
        value *= Decimal("1000000000")
    return value


def _detect_event_type(text: str, category: str) -> str | None:
    lower = text.lower()
    category_map = {
        "litigation": "litigation",
        "credit_rating": "credit_rating",
    }
    if category in category_map:
        return category_map[category]
    for pattern, event_type in EVENT_RULES:
        if re.search(pattern, lower):
            return event_type
    if re.search(r"material information|disclosure of material", lower):
        return "other"
    return None


def _extract_counterparty(text: str) -> str | None:
    m = COUNTERPARTY_PATTERN.search(text)
    if m:
        return m.group(1).strip()[:200]
    return None


def _event_date_from_text(text: str, published_at: datetime) -> date:
    for pattern in (
        re.compile(r"\b(\d{1,2}[-/]\w+[-/]\d{4})\b", re.IGNORECASE),
        re.compile(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b"),
    ):
        m = pattern.search(text)
        if m:
            parsed = _parse_date_fragment(m.group(1))
            if parsed:
                return parsed
    return published_at.date()


def parse_material_events(
    *,
    symbol: str,
    title: str,
    body_text: str | None,
    category: str,
    published_at: datetime,
    source_announcement_id: int | None = None,
) -> list[ParsedMaterialEvent]:
    text = f"{title}\n{body_text or ''}"
    event_type = _detect_event_type(text, category)
    if not event_type:
        return []

    amount = _extract_amount_pkr(text)
    summary = (body_text or title)[:300]
    significance = score_event(event_type, text, amount)

    return [
        ParsedMaterialEvent(
            symbol=symbol,
            event_type=event_type,
            headline=title[:500],
            event_date=_event_date_from_text(text, published_at),
            counterparty=_extract_counterparty(text),
            amount_pkr=amount,
            significance_score=significance,
            summary=summary,
            source_announcement_id=source_announcement_id,
        )
    ]
