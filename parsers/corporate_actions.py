"""Rule-based corporate action extraction from PSX announcements."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from parsers.schemas import ParsedCorporateAction

MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

DATE_PATTERNS = [
    re.compile(
        r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d{1,2})[-\s](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s,]*(\d{4})\b",
        re.IGNORECASE,
    ),
]

AMOUNT_PATTERN = re.compile(
    r"(?:rs\.?|pkr)\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)
RATIO_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*%|(\d+)\s*:\s*(\d+)|every\s+(\d+)\s+shares?",
    re.IGNORECASE,
)

EX_DATE_PATTERN = re.compile(r"ex[-\s]?dividend[^.]{0,80}?(\d{1,2}[-/]\w+[-/]\d{4})", re.IGNORECASE)
RECORD_DATE_PATTERN = re.compile(
    r"(?:record|book\s+closure)[^.]{0,80}?(\d{1,2}[-/]\w+[-/]\d{4})",
    re.IGNORECASE,
)
PAYMENT_DATE_PATTERN = re.compile(
    r"payment[^.]{0,80}?(\d{1,2}[-/]\w+[-/]\d{4})",
    re.IGNORECASE,
)
AGM_DATE_PATTERN = re.compile(
    r"(?:agm|egm|annual general|extraordinary general)[^.]{0,120}?(\d{1,2}[-/]\w+[-/]\d{4})",
    re.IGNORECASE,
)
SPLIT_PATTERN = re.compile(r"stock\s+split|share\s+split|sub-?division", re.IGNORECASE)


def _parse_date_fragment(fragment: str) -> date | None:
    fragment = fragment.strip()
    for pattern in DATE_PATTERNS:
        m = pattern.search(fragment)
        if not m:
            continue
        groups = m.groups()
        try:
            if len(groups) == 3 and (groups[1].isalpha() or not groups[1].isdigit()):
                day, month, year = (
                    int(groups[0]),
                    MONTH_MAP[groups[1][:3].lower()],
                    int(groups[2]),
                )
            else:
                day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
            return date(year, month, day)
        except (ValueError, KeyError):
            continue
    return None


def _extract_date_near(text: str, pattern: re.Pattern[str]) -> date | None:
    m = pattern.search(text)
    if not m:
        return None
    return _parse_date_fragment(m.group(1))


def _extract_amount(text: str) -> Decimal | None:
    m = AMOUNT_PATTERN.search(text)
    if not m:
        return None
    try:
        return Decimal(m.group(1).replace(",", ""))
    except InvalidOperation:
        return None


def _extract_ratio(text: str) -> str | None:
    m = RATIO_PATTERN.search(text)
    if not m:
        return None
    if m.group(1):
        return f"{m.group(1)}%"
    if m.group(2) and m.group(3):
        return f"{m.group(2)}:{m.group(3)}"
    if m.group(4):
        return f"1:{m.group(4)}"
    return None


def _dividend_subtype(text: str) -> str:
    lower = text.lower()
    if "interim" in lower:
        return "interim"
    if "special" in lower:
        return "special"
    if "final" in lower:
        return "final"
    return "cash"


def parse_corporate_actions(
    *,
    symbol: str,
    title: str,
    body_text: str | None,
    category: str,
    published_at: datetime,
    source_announcement_id: int | None = None,
) -> list[ParsedCorporateAction]:
    """Extract zero or more corporate actions from an announcement."""
    text = f"{title}\n{body_text or ''}"
    lower = text.lower()
    results: list[ParsedCorporateAction] = []

    if category in ("dividend",) or re.search(r"cash dividend|dividend", lower):
        amount = _extract_amount(text)
        results.append(
            ParsedCorporateAction(
                symbol=symbol,
                action_type="cash_dividend",
                announced_at=published_at,
                ex_date=_extract_date_near(text, EX_DATE_PATTERN),
                record_date=_extract_date_near(text, RECORD_DATE_PATTERN),
                payment_date=_extract_date_near(text, PAYMENT_DATE_PATTERN),
                amount_per_share=amount,
                ratio=None,
                source_announcement_id=source_announcement_id,
                details_json={"subtype": _dividend_subtype(text)},
            )
        )

    if category in ("bonus_shares",) or re.search(r"bonus share|stock dividend", lower):
        results.append(
            ParsedCorporateAction(
                symbol=symbol,
                action_type="bonus_shares",
                announced_at=published_at,
                ex_date=_extract_date_near(text, EX_DATE_PATTERN),
                record_date=_extract_date_near(text, RECORD_DATE_PATTERN),
                payment_date=None,
                amount_per_share=None,
                ratio=_extract_ratio(text),
                source_announcement_id=source_announcement_id,
                details_json={},
            )
        )

    if category in ("rights_issue",) or re.search(r"rights issue", lower):
        results.append(
            ParsedCorporateAction(
                symbol=symbol,
                action_type="rights_issue",
                announced_at=published_at,
                ex_date=_extract_date_near(text, EX_DATE_PATTERN),
                record_date=_extract_date_near(text, RECORD_DATE_PATTERN),
                payment_date=None,
                amount_per_share=_extract_amount(text),
                ratio=_extract_ratio(text),
                source_announcement_id=source_announcement_id,
                details_json={},
            )
        )

    if SPLIT_PATTERN.search(lower):
        results.append(
            ParsedCorporateAction(
                symbol=symbol,
                action_type="split",
                announced_at=published_at,
                ex_date=_extract_date_near(text, EX_DATE_PATTERN),
                record_date=_extract_date_near(text, RECORD_DATE_PATTERN),
                payment_date=None,
                amount_per_share=None,
                ratio=_extract_ratio(text),
                source_announcement_id=source_announcement_id,
                details_json={},
            )
        )

    if category in ("agm_egm",) or re.search(r"\bagm\b|\begm\b|annual general meeting|extraordinary general", lower):
        action_type = "egm" if re.search(r"\begm\b|extraordinary general", lower) else "agm"
        event_date = _extract_date_near(text, AGM_DATE_PATTERN)
        results.append(
            ParsedCorporateAction(
                symbol=symbol,
                action_type=action_type,
                announced_at=published_at,
                ex_date=event_date,
                record_date=_extract_date_near(text, RECORD_DATE_PATTERN),
                payment_date=None,
                amount_per_share=None,
                ratio=None,
                source_announcement_id=source_announcement_id,
                details_json={"venue": None},
            )
        )

    if re.search(r"book closure|closure of register", lower) and not any(
        r.action_type == "book_closure" for r in results
    ):
        results.append(
            ParsedCorporateAction(
                symbol=symbol,
                action_type="book_closure",
                announced_at=published_at,
                ex_date=None,
                record_date=_extract_date_near(text, RECORD_DATE_PATTERN),
                payment_date=None,
                amount_per_share=None,
                ratio=None,
                source_announcement_id=source_announcement_id,
                details_json={},
            )
        )

    return results
