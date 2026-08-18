import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber
from dateutil import parser as date_parser

from parsers.confidence import score_insider_parse
from parsers.schemas import ParsedInsiderTrade

TXN_TYPE_MAP = {
    "buy": "buy",
    "purchase": "buy",
    "acquir": "buy",
    "sell": "sell",
    "sale": "sell",
    "dispos": "sell",
    "pledge": "pledge",
    "unpledge": "unpledge",
}


def _parse_int(raw: str) -> int | None:
    cleaned = re.sub(r"[^\d-]", "", raw or "")
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_decimal(raw: str) -> Decimal | None:
    cleaned = (raw or "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _detect_txn_type(text: str) -> str:
    lower = text.lower()
    for key, txn in TXN_TYPE_MAP.items():
        if key in lower:
            return txn
    return "buy"


def parse_insider_pdf(path: Path) -> list[ParsedInsiderTrade]:
    """Extract insider trade rows from disclosure PDF."""
    trades: list[ParsedInsiderTrade] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:10]:
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                header = " ".join(str(c or "") for c in table[0]).lower()
                if not any(k in header for k in ("name", "director", "shares", "date")):
                    continue
                for row in table[1:]:
                    if not row or len(row) < 3:
                        continue
                    name = str(row[0] or "").strip()
                    if not name or name.lower() in {"name", "director", "total"}:
                        continue
                    date_val = None
                    shares = None
                    price = None
                    designation = None
                    post_holding = None
                    for i, cell in enumerate(row[1:], start=1):
                        cell_s = str(cell or "").strip()
                        if not cell_s:
                            continue
                        try:
                            date_val = date_parser.parse(cell_s).date()
                            continue
                        except (ValueError, TypeError):
                            pass
                        if shares is None and re.search(r"\d{3,}", cell_s):
                            shares = _parse_int(cell_s)
                        elif price is None and re.search(r"\d+\.\d{2}", cell_s):
                            price = _parse_decimal(cell_s)
                        elif designation is None and len(cell_s) > 3 and not cell_s[0].isdigit():
                            designation = cell_s
                    row_text = " ".join(str(c or "") for c in row)
                    txn_type = _detect_txn_type(row_text)
                    if name and date_val and shares:
                        trades.append(
                            ParsedInsiderTrade(
                                director_name=name,
                                designation=designation,
                                transaction_date=date_val,
                                transaction_type=txn_type,
                                shares=shares,
                                price_per_share=price,
                                post_holding_shares=post_holding,
                            )
                        )

    if not trades:
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:5]:
                text += page.extract_text() or ""
        if not text.strip():
            return []
        for match in re.finditer(
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+).{0,80}?(buy|sell|purchase|pledge).{0,40}?(\d{1,2}\s+\w+\s+\d{4}).{0,40}?(\d[\d,]*)",
            text,
            re.I | re.S,
        ):
            name, action, date_str, share_str = match.groups()
            try:
                date_val = date_parser.parse(date_str).date()
            except (ValueError, TypeError):
                continue
            shares = _parse_int(share_str)
            if shares:
                trades.append(
                    ParsedInsiderTrade(
                        director_name=name.strip(),
                        transaction_date=date_val,
                        transaction_type=_detect_txn_type(action),
                        shares=shares,
                    )
                )

    _ = score_insider_parse(trades)
    return trades
