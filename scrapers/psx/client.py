import hashlib
import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from backend.config import settings

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]*$")
KARACHI = ZoneInfo(settings.market_timezone)


class PsxClient:
    def __init__(self) -> None:
        self.base_url = settings.psx_base_url.rstrip("/")
        self.headers = {"User-Agent": settings.psx_user_agent}

    async def fetch_text(self, path: str) -> str:
        async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
            response = await client.get(f"{self.base_url}{path}")
            response.raise_for_status()
            return response.text

    async def fetch_json(self, path: str) -> dict | list:
        async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
            response = await client.get(f"{self.base_url}{path}")
            response.raise_for_status()
            return response.json()


def structure_hash(content: str) -> str:
    normalized = re.sub(r"\s+", " ", content.strip())
    return hashlib.sha256(normalized.encode()).hexdigest()


def is_market_open(now: datetime | None = None) -> bool:
    current = now or datetime.now(KARACHI)
    if current.weekday() >= 5:
        return False
    market_open = current.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = current.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= current <= market_close


def unix_to_utc(ts: int | float) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)


def parse_market_watch(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []
    for tr in soup.select("tbody.tbl__body tr"):
        symbol_el = tr.select_one("a.tbl__symbol strong")
        if not symbol_el:
            continue
        symbol = symbol_el.get_text(strip=True)
        cells = tr.find_all("td")
        if len(cells) < 11:
            continue
        try:
            rows.append(
                {
                    "symbol": symbol,
                    "sector_code": cells[1].get_text(strip=True),
                    "board": cells[2].get_text(strip=True),
                    "ldcp": float(cells[3].get("data-order", cells[3].get_text(strip=True))),
                    "open": float(cells[4].get("data-order", cells[4].get_text(strip=True))),
                    "high": float(cells[5].get("data-order", cells[5].get_text(strip=True))),
                    "low": float(cells[6].get("data-order", cells[6].get_text(strip=True))),
                    "close": float(cells[7].get("data-order", cells[7].get_text(strip=True))),
                    "change": float(cells[8].get("data-order", "0")),
                    "change_pct": float(cells[9].get("data-order", "0")),
                    "volume": int(float(cells[10].get("data-order", "0"))),
                }
            )
        except (TypeError, ValueError):
            continue
    return rows


def parse_company_equity(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    result: dict = {}
    sector_el = soup.select_one(".quote__sector span")
    if sector_el:
        result["sector"] = sector_el.get_text(strip=True)
    for item in soup.select("#equity .stats_item"):
        label_el = item.select_one(".stats_label")
        value_el = item.select_one(".stats_value")
        if not label_el or not value_el:
            continue
        label = label_el.get_text(strip=True).lower()
        raw = value_el.get_text(strip=True).replace(",", "")
        if label == "shares":
            try:
                result["shares_outstanding"] = int(float(raw))
            except ValueError:
                pass
    return result


TAB_CATEGORY_MAP = {
    "financial results": "financial_result",
    "board meetings": "board_meeting",
    "others": "other",
}

TITLE_CATEGORY_RULES: list[tuple[str, str]] = [
    (r"insider|director.*(buy|sell|purchase|disposal|pledge|unpledge)", "insider_trade"),
    (r"pattern of shareholding|shareholding pattern", "pattern_of_shareholding"),
    (r"cash dividend|dividend", "dividend"),
    (r"bonus share|stock dividend", "bonus_shares"),
    (r"rights issue", "rights_issue"),
    (r"financial result|quarterly report|annual report", "financial_result"),
    (r"board meeting", "board_meeting"),
    (r"agm|egm|annual general|extraordinary general", "agm_egm"),
    (r"credit rating", "credit_rating"),
    (r"litigation|court|arbitration", "litigation"),
]


def classify_announcement_category(tab_name: str, title: str) -> str:
    tab_key = tab_name.strip().lower()
    if tab_key in TAB_CATEGORY_MAP:
        base = TAB_CATEGORY_MAP[tab_key]
    else:
        base = "other"
    title_lower = title.lower()
    for pattern, category in TITLE_CATEGORY_RULES:
        if re.search(pattern, title_lower):
            return category
    return base


def parse_company_announcements(html: str, symbol: str, base_url: str) -> list[dict]:
    """Parse announcements embedded in /company/{symbol} page."""
    soup = BeautifulSoup(html, "lxml")
    section = soup.find(id="announcements")
    if not section:
        return []
    base = base_url.rstrip("/")
    source_url = f"{base}/company/{symbol}#announcements"
    records: list[dict] = []
    for panel in section.select(".tabs__panel"):
        tab_name = panel.get("data-name", "Others")
        for tr in panel.select("tbody.tbl__body tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            date_text = cells[0].get_text(strip=True)
            title = cells[1].get_text(" ", strip=True)
            if not date_text or not title:
                continue
            try:
                published_at = date_parser.parse(date_text).replace(tzinfo=UTC)
            except (ValueError, TypeError):
                continue
            pdf_url = None
            if len(cells) >= 3:
                pdf_link = cells[2].find("a", href=re.compile(r"\.pdf", re.I))
                if pdf_link and pdf_link.get("href"):
                    href = pdf_link["href"]
                    pdf_url = href if href.startswith("http") else f"{base}{href}"
            category = classify_announcement_category(tab_name, title)
            records.append(
                {
                    "symbol": symbol.upper(),
                    "published_at": published_at,
                    "title": title,
                    "category": category,
                    "pdf_url": pdf_url,
                    "source_url": source_url,
                    "body_text": None,
                }
            )
    return records
