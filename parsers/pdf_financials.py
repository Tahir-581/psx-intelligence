import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber
from dateutil import parser as date_parser

from parsers.confidence import score_financial_parse
from parsers.schemas import ParsedFinancialPeriod, ParsedLineItem

LINE_START_PATTERNS: dict[str, str] = {
    "revenue": r"^(?:turnover|sales|revenue)\b",
    "gross_profit": r"^gross profit\b",
    "ebitda": r"^ebitda\b",
    "pat": r"^profit (?:after tax|for the period)\b",
    "eps_basic": r"^(?:eps|earnings per share)\b",
    "total_assets": r"^total assets\b",
    "total_equity": r"^total equity\b",
    "total_debt": r"^(?:total debt|borrowings)\b",
    "current_assets": r"^current assets\b",
    "current_liabilities": r"^current liabilities\b",
    "ocf": r"^(?:operating cash|cash from operations)\b",
    "capex": r"^(?:capital expenditure|capex)\b",
}

LINE_PATTERNS: list[tuple[str, str]] = [
    (r"(?<!cost of )(?:sales|revenue|turnover\s*-?\s*net|turnover\b)", "revenue"),
    (r"gross profit", "gross_profit"),
    (r"ebitda", "ebitda"),
    (r"profit after tax|profit for the period|net profit|pat\b", "pat"),
    (r"eps|earnings per share", "eps_basic"),
    (r"total assets", "total_assets"),
    (r"total equity|shareholders.? equity", "total_equity"),
    (r"total debt|borrowings", "total_debt"),
    (r"operating cash|cash from operations|ocf", "ocf"),
    (r"capital expenditure|capex", "capex"),
    (r"current assets", "current_assets"),
    (r"current liabilities", "current_liabilities"),
]

PERIOD_PATTERNS = [
    r"quarter ended\s+(\w+\s+\d{1,2},?\s+\d{4})",
    r"year ended\s+(\w+\s+\d{1,2},?\s+\d{4})",
    r"period ended\s+(\w+\s+\d{1,2},?\s+\d{4})",
    r"(\d{1,2}\s+\w+\s+\d{4})",
]


def _parse_number(raw: str) -> Decimal | None:
    cleaned = raw.replace(",", "").replace("(", "-").replace(")", "").strip()
    if not cleaned or cleaned in {"-", "—", "nil", "n/a"}:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _fix_spaced_numbers(text: str) -> str:
    """Repair PDF text extraction that splits digits: '9 5,293,909' -> '95,293,909'."""
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"(\d)\s+(\d)", r"\1\2", text)
    return text


def _numbers_from_line(line: str) -> list[Decimal]:
    values: list[Decimal] = []
    for match in re.finditer(r"\(?(?:\d\s+)*\d{1,3}(?:,\d{3})+\)?", line):
        raw = re.sub(r"\s+", "", match.group(0))
        value = _parse_number(raw)
        if value is not None and abs(value) >= 1:
            values.append(value)
    return values


def _line_matches_label(label: str, pattern: str, code: str) -> bool:
    portion = label[:55]
    start_pattern = LINE_START_PATTERNS.get(code)
    if start_pattern:
        if not re.match(start_pattern, portion, re.I):
            return False
    elif not re.search(pattern, portion, re.I):
        return False
    if code == "revenue" and re.search(r"revenue\s+reserves?|cost of sales", portion, re.I):
        return False
    if code == "total_equity" and "liabilities" in portion:
        return False
    if code == "pat" and portion.count("-") > 4:
        return False
    return True


def _extract_from_text(full_text: str) -> dict[str, ParsedLineItem]:
    """Fallback for PSX filings where income statement lines are plain text, not tables."""
    unit = _detect_unit(full_text)
    line_items: dict[str, ParsedLineItem] = {}
    for raw_line in full_text.splitlines():
        line = raw_line.strip()
        if not line or len(line) < 4:
            continue
        label = line.lower()
        for pattern, code in LINE_PATTERNS:
            if code in line_items:
                continue
            if not _line_matches_label(label, pattern, code):
                continue
            numbers = _numbers_from_line(line)
            if not numbers:
                continue
            if code in {"revenue", "gross_profit", "ebitda", "pat", "eps_basic"} and len(numbers) > 6:
                continue
            line_items[code] = ParsedLineItem(line_code=code, value=numbers[0], unit=unit)
            break
    return line_items


def _detect_unit(text: str) -> str:
    lower = text.lower()
    if "million" in lower:
        return "millions"
    if "thousand" in lower or "'000" in lower:
        return "thousands"
    return "absolute"


def _extract_period_end(text: str) -> tuple[date | None, str]:
    for pattern in PERIOD_PATTERNS:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                dt = date_parser.parse(match.group(1)).date()
                period_type = "annual" if "year ended" in text.lower() else "quarterly"
                return dt, period_type
            except (ValueError, TypeError):
                continue
    return None, "quarterly"


def _fiscal_fields(period_end: date, period_type: str) -> tuple[int, int | None]:
    fiscal_year = period_end.year
    fiscal_quarter = None
    if period_type == "quarterly":
        fiscal_quarter = (period_end.month - 1) // 3 + 1
    return fiscal_year, fiscal_quarter


def parse_financial_pdf(path: Path, symbol: str, title: str = "") -> ParsedFinancialPeriod | None:
    """Extract financial line items from a PSX result PDF."""
    full_text = ""
    tables: list[list[list[str | None]]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:15]:
            text = page.extract_text() or ""
            full_text += "\n" + text
            for table in page.extract_tables() or []:
                tables.append(table)

    if not full_text.strip():
        # TODO: OCR with pytesseract for scanned PDFs
        return None

    context = f"{title}\n{full_text[:3000]}"
    period_end, period_type = _extract_period_end(context)
    if not period_end:
        return None

    unit = _detect_unit(full_text)
    line_items: dict[str, ParsedLineItem] = {}

    for table in tables:
        for row in table:
            if not row or len(row) < 2:
                continue
            label = (row[0] or "").strip()
            if not label:
                continue
            for pattern, code in LINE_PATTERNS:
                if code in line_items:
                    continue
                if re.search(pattern, label, re.I):
                    for cell in reversed(row[1:]):
                        if cell is None:
                            continue
                        value = _parse_number(str(cell))
                        if value is not None:
                            line_items[code] = ParsedLineItem(
                                line_code=code, value=value, unit=unit
                            )
                            break
                    break

    if len(line_items) < 4:
        for code, item in _extract_from_text(full_text).items():
            line_items.setdefault(code, item)

    fiscal_year, fiscal_quarter = _fiscal_fields(period_end, period_type)
    result = ParsedFinancialPeriod(
        symbol=symbol.upper(),
        period_end=period_end,
        period_type=period_type,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        line_items=list(line_items.values()),
    )
    result.confidence = score_financial_parse(result)
    return result
