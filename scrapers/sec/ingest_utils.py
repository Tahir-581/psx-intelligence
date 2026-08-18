"""SEC ingestion utilities — ported from smart-money-tracker lib/ingest-utils.ts."""

from __future__ import annotations

import re
from datetime import date, datetime

import httpx

from backend.config import settings

AVATAR_COLORS = ["blue", "teal", "purple", "amber", "green", "coral"]

MONTHS = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}


def pad_cik(cik: str) -> str:
    digits = re.sub(r"\D", "", cik)
    if not digits or set(digits) == {"0"}:
        return ""
    return digits.zfill(10)


def is_valid_cik(cik: str) -> bool:
    digits = re.sub(r"\D", "", cik)
    return bool(digits) and set(digits) != {"0"}


def parse_sec_date(raw: str) -> str:
    trimmed = raw.strip()
    if not trimmed:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", trimmed):
        return trimmed[:10]
    m = re.match(r"^(\d{1,2})-([A-Z]{3})-(\d{4})$", trimmed, re.I)
    if m:
        mon = MONTHS.get(m.group(2).upper())
        if mon:
            return f"{m.group(3)}-{mon}-{m.group(1).zfill(2)}"
    return trimmed[:10]


def parse_tsv_line(line: str) -> list[str]:
    return [cell.strip() for cell in line.split("\t")]


def parse_tsv_header(line: str) -> dict[str, int]:
    cols = parse_tsv_line(line)
    return {col.upper(): i for i, col in enumerate(cols)}


def get_field(row: list[str], header: dict[str, int], name: str) -> str:
    idx = header.get(name.upper())
    if idx is None:
        return ""
    return row[idx] if idx < len(row) else ""


def classify_investor_type(name: str) -> str:
    upper = name.upper()
    if re.search(r"BERKSHIRE|VALUE|HOLDINGS INC\.?$|TRUST|CAPITAL MANAGEMENT LLC", upper) and not re.search(
        r"HEDGE", upper
    ):
        if re.search(r"BERKSHIRE|MUNGER|BUFFETT", upper):
            return "value_fund"
    if re.search(r"MUTUAL FUND|FUND TRUST|INDEX FUND|VANGUARD|FIDELITY|BLACKROCK FUNDS", upper):
        return "mutual_fund"
    if re.search(r"ELLIOTT|ACTIVIST|PERSHING|SARISSA|STARBOARD|JANA|THIRD POINT|ICAHN", upper):
        return "pe_activist"
    if re.search(r"FAMILY OFFICE|DUQUESNE|DRUCKENMILLER|SOROS FUND|SAC CAPITAL|INDIVIDUAL", upper):
        return "individual"
    if re.search(
        r"FUND|CAPITAL|PARTNERS|MANAGEMENT|ADVISORS|INVESTMENTS|ASSET|LLC|LP|L\.P\.|HOLDINGS|GROUP|SECURITIES",
        upper,
    ):
        return "hedge_fund"
    return "unknown"


def normalize_13f_value(raw: str, report_period: str) -> int:
    n = float(raw.replace(",", "") or 0)
    if not n:
        return 0
    try:
        period_date = date.fromisoformat(report_period[:10])
        cutoff = date(2023, 1, 3)
        if period_date >= cutoff:
            return round(n)
        return round(n * 1000)
    except ValueError:
        return round(n)


def _sec_headers() -> dict[str, str]:
    return {"User-Agent": settings.sec_user_agent}


def fetch_sec_text(url: str) -> str:
    with httpx.Client(timeout=120.0) as client:
        res = client.get(url, headers=_sec_headers())
        res.raise_for_status()
        return res.text


def fetch_sec_buffer(url: str) -> bytes:
    with httpx.Client(timeout=300.0) as client:
        res = client.get(url, headers=_sec_headers())
        res.raise_for_status()
        return res.content


def resolve_latest_13f_zip_url() -> tuple[str, str]:
    if settings.sec_13f_zip_url:
        return settings.sec_13f_zip_url, settings.sec_13f_quarter_label or "custom"
    html = fetch_sec_text(
        "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
    )
    patterns = [
        r'href="(/files/structureddata/data/form-13f-data-sets/[^"]+\.zip)"',
        r'href="(/files/data/research/[^"]+\.zip)"',
        r'href="([^"]*form13f[^"]*\.zip)"',
    ]
    for pattern in patterns:
        m = re.search(pattern, html, re.I)
        if m:
            path = m.group(1)
            url = path if path.startswith("http") else f"https://www.sec.gov{path}"
            label_m = re.search(r"([^/]+)\.zip", url, re.I)
            return url, label_m.group(1) if label_m else "latest"
    raise RuntimeError("Could not find 13F ZIP download link on SEC page")


def initials_from_name(name: str) -> str:
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def avatar_color_for_cik(cik: str) -> str:
    n = int(re.sub(r"\D", "", cik) or "0")
    return AVATAR_COLORS[n % len(AVATAR_COLORS)]
