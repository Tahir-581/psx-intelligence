import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber
from dateutil import parser as date_parser

from parsers.confidence import score_ownership_parse
from parsers.schemas import ParsedOwnershipRow, ParsedOwnershipSnapshot

CATEGORY_PATTERNS: list[tuple[str, str]] = [
    (r"sponsor|promoter", "sponsors"),
    (r"director|executive|management", "directors"),
    (r"institution|mutual fund|nbfc|bank|dfi|insurance", "institutions"),
    (r"foreign|fpi|overseas", "foreign"),
    (r"public|general public|retail", "public"),
    (r"nif|national investment", "nifs"),
    (r"associated|affiliate", "associated_companies"),
]


def _parse_pct(raw: str) -> Decimal | None:
    cleaned = (raw or "").replace("%", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_shares(raw: str) -> int | None:
    cleaned = re.sub(r"[^\d]", "", raw or "")
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _map_category(label: str) -> str:
    lower = label.lower()
    for pattern, category in CATEGORY_PATTERNS:
        if re.search(pattern, lower):
            return category
    return re.sub(r"\s+", "_", lower.strip())[:50] or "other"


def _extract_as_of_date(text: str) -> date | None:
    for pattern in [
        r"as at\s+(\w+\s+\d{1,2},?\s+\d{4})",
        r"as on\s+(\w+\s+\d{1,2},?\s+\d{4})",
        r"(\d{1,2}\s+\w+\s+\d{4})",
    ]:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                return date_parser.parse(match.group(1)).date()
            except (ValueError, TypeError):
                continue
    return None


def parse_ownership_pdf(path: Path, symbol: str, title: str = "") -> ParsedOwnershipSnapshot | None:
    """Extract pattern-of-shareholding table from PDF."""
    full_text = ""
    tables: list[list[list[str | None]]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:12]:
            text = page.extract_text() or ""
            full_text += "\n" + text
            for table in page.extract_tables() or []:
                tables.append(table)

    if not full_text.strip():
        return None

    as_of_date = _extract_as_of_date(f"{title}\n{full_text[:2000]}") or date.today()
    rows: list[ParsedOwnershipRow] = []

    for table in tables:
        for row in table:
            if not row or len(row) < 2:
                continue
            label = str(row[0] or "").strip()
            if not label or label.lower() in {"category", "particulars", "description"}:
                continue
            shares = None
            pct = None
            for cell in row[1:]:
                cell_s = str(cell or "").strip()
                if "%" in cell_s:
                    pct = _parse_pct(cell_s)
                elif re.search(r"\d{3,}", cell_s):
                    shares = _parse_shares(cell_s)
            if shares and pct is not None:
                rows.append(
                    ParsedOwnershipRow(
                        holder_category=_map_category(label),
                        shares=shares,
                        pct_outstanding=pct,
                        as_of_date=as_of_date,
                    )
                )

    if not rows:
        return None

    result = ParsedOwnershipSnapshot(symbol=symbol.upper(), as_of_date=as_of_date, rows=rows)
    result.confidence = score_ownership_parse(result)
    return result
