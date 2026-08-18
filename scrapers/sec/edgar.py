"""SEC EDGAR live API client and mock data fallback."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from backend.config import settings

AVATAR_COLORS = ["blue", "teal", "purple", "amber", "green", "coral"]

MOCK_FILINGS: list[dict[str, Any]] = [
    {
        "id": "filing-nvda-huang",
        "investorName": "Jensen Huang",
        "investorCik": "",
        "investorType": "individual",
        "formType": "4",
        "ticker": "NVDA",
        "companyName": "NVIDIA Corp",
        "filedAt": datetime.now(UTC).isoformat(),
        "transactionDate": "2026-06-02",
        "amount": 48_200_000,
        "shares": 430_000,
        "avgPrice": 112.09,
        "action": "buy",
        "accessionNo": "mock-nvda-4",
        "avatarInitials": "JH",
        "avatarColor": "green",
    },
    {
        "id": "filing-hon-elliott",
        "investorName": "Elliott Management",
        "investorCik": "1048268",
        "investorType": "pe_activist",
        "formType": "13D",
        "ticker": "HON",
        "companyName": "Honeywell International",
        "filedAt": (datetime.now(UTC) - timedelta(minutes=14)).isoformat(),
        "amount": 1_200_000_000,
        "action": "increased",
        "portfolioPct": 8.3,
        "accessionNo": "mock-hon-13d",
        "avatarInitials": "EM",
        "avatarColor": "blue",
    },
    {
        "id": "filing-bridgewater-13f",
        "investorName": "Bridgewater Associates",
        "investorCik": "1350694",
        "investorType": "hedge_fund",
        "formType": "13F",
        "filedAt": datetime.now(UTC).isoformat(),
        "aum": 27_400_000_000,
        "accessionNo": "mock-bw-13f",
        "avatarInitials": "BW",
        "avatarColor": "teal",
    },
    {
        "id": "filing-berkshire-13f",
        "investorName": "Berkshire Hathaway",
        "investorCik": "1067983",
        "investorType": "value_fund",
        "formType": "13F",
        "filedAt": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
        "aum": 380_000_000_000,
        "accessionNo": "mock-bh-13f",
        "avatarInitials": "BH",
        "avatarColor": "amber",
    },
    {
        "id": "filing-tiger-13f",
        "investorName": "Tiger Global Management",
        "investorCik": "1167483",
        "investorType": "hedge_fund",
        "formType": "13F",
        "filedAt": (datetime.now(UTC) - timedelta(hours=4)).isoformat(),
        "aum": 14_100_000_000,
        "accessionNo": "mock-tg-13f",
        "avatarInitials": "TG",
        "avatarColor": "purple",
    },
]

MOCK_INVESTORS: list[dict[str, Any]] = [
    {
        "cik": "1067983",
        "name": "Berkshire Hathaway",
        "type": "value_fund",
        "aum": 380_100_000_000,
        "holdingsCount": 47,
        "lastFilingDate": "2026-05-15",
        "ytdChange": 8.3,
        "topTicker": "AAPL",
        "topPct": 22.6,
        "avatarInitials": "BH",
        "avatarColor": "amber",
    },
    {
        "cik": "1350694",
        "name": "Bridgewater Associates",
        "type": "hedge_fund",
        "aum": 27_400_000_000,
        "holdingsCount": 1040,
        "lastFilingDate": "2026-05-15",
        "ytdChange": 2.1,
        "topTicker": "SPY",
        "topPct": 11.4,
        "avatarInitials": "BW",
        "avatarColor": "teal",
    },
    {
        "cik": "1048268",
        "name": "Elliott Management",
        "type": "pe_activist",
        "aum": 65_200_000_000,
        "holdingsCount": 23,
        "lastFilingDate": "2026-06-02",
        "ytdChange": 14.7,
        "topTicker": "HON",
        "topPct": 8.3,
        "avatarInitials": "EM",
        "avatarColor": "blue",
    },
    {
        "cik": "1167483",
        "name": "Tiger Global Management",
        "type": "hedge_fund",
        "aum": 14_100_000_000,
        "holdingsCount": 138,
        "lastFilingDate": "2026-05-15",
        "ytdChange": -3.2,
        "topTicker": "META",
        "topPct": 9.1,
        "avatarInitials": "TG",
        "avatarColor": "purple",
    },
    {
        "cik": "1536411",
        "name": "Stanley Druckenmiller",
        "type": "individual",
        "aum": 2_900_000_000,
        "holdingsCount": 31,
        "lastFilingDate": "2026-05-15",
        "ytdChange": -1.4,
        "topTicker": "NVDA",
        "topPct": 17.2,
        "avatarInitials": "SD",
        "avatarColor": "green",
    },
]

BERKSHIRE_HOLDINGS = [
    {"ticker": "AAPL", "companyName": "Apple Inc", "value": 86_000_000_000, "shares": 400_000_000,
     "portfolioPct": 22.6, "qoqChange": -3.1, "isNew": False},
    {"ticker": "AXP", "companyName": "American Express", "value": 77_900_000_000, "shares": 151_000_000,
     "portfolioPct": 20.5, "qoqChange": 0.4, "isNew": False},
]

MOCK_INVESTOR_PROFILES: dict[str, dict[str, Any]] = {
    "0001067983": {
        "cik": "1067983", "name": "Berkshire Hathaway", "type": "value_fund",
        "aum": 380_100_000_000, "holdingsCount": 47, "lastFilingDate": "2026-05-15",
        "ytdChange": 8.3, "topTicker": "AAPL", "topPct": 22.6,
        "avatarInitials": "BH", "avatarColor": "amber",
        "holdings": BERKSHIRE_HOLDINGS, "totalHoldings": 47, "top5Concentration": 71,
        "quarterlyTurnover": 2.1,
        "description": "Value fund · Warren Buffett · CIK 1067983 · 13F filer since 1994",
    },
    "0001350694": {
        "cik": "1350694", "name": "Bridgewater Associates", "type": "hedge_fund",
        "aum": 27_400_000_000, "holdingsCount": 1040, "lastFilingDate": "2026-05-15",
        "ytdChange": 2.1, "topTicker": "SPY", "topPct": 11.4,
        "avatarInitials": "BW", "avatarColor": "teal",
        "holdings": [{"ticker": "SPY", "companyName": "SPDR S&P 500 ETF", "value": 3_100_000_000,
                      "shares": 1_400_000, "portfolioPct": 11.4, "qoqChange": 4.2, "isNew": False}],
        "totalHoldings": 1040, "top5Concentration": 28, "quarterlyTurnover": 8.5,
        "description": "Macro hedge fund · CIK 1350694",
    },
}

MOCK_INVESTMENTS: list[dict[str, Any]] = [
    {
        "id": "inv-bh-aapl", "investorName": "Berkshire Hathaway", "investorCik": "1067983",
        "investorType": "value_fund", "formType": "13F", "ticker": "AAPL",
        "companyName": "Apple Inc", "filedAt": "2026-03-31", "amount": 9_200_000_000,
        "shares": 400_000_000, "action": "increased", "portfolioPct": 22.6,
        "accessionNo": "mock-bh-aapl", "avatarInitials": "BH", "avatarColor": "amber", "sector": "tech",
    },
    {
        "id": "inv-em-hon", "investorName": "Elliott Management", "investorCik": "1048268",
        "investorType": "pe_activist", "formType": "13D", "ticker": "HON",
        "companyName": "Honeywell International", "filedAt": "2026-06-02", "amount": 1_200_000_000,
        "action": "new", "portfolioPct": 8.3, "accessionNo": "mock-em-hon",
        "avatarInitials": "EM", "avatarColor": "blue", "sector": "tech",
    },
]

SECTOR_MAP: dict[str, str] = {
    "AAPL": "tech", "MSFT": "tech", "NVDA": "tech", "META": "tech", "AMZN": "tech",
    "GOOGL": "tech", "GOOG": "tech", "TSLA": "tech", "HON": "tech", "SPY": "tech",
    "XOM": "energy", "CVX": "energy", "OXY": "energy",
    "JPM": "finance", "BAC": "finance", "AXP": "finance",
    "JNJ": "healthcare", "PFE": "healthcare",
    "KO": "consumer", "PG": "consumer",
}


def pad_cik(cik: str) -> str:
    digits = re.sub(r"\D", "", cik)
    return digits.zfill(10) if digits else ""


def strip_cik(cik: str) -> str:
    return cik.lstrip("0") or cik


def initials_from_name(name: str) -> str:
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def avatar_color_for_cik(cik: str) -> str:
    n = int(re.sub(r"\D", "", cik) or "0")
    return AVATAR_COLORS[n % len(AVATAR_COLORS)]


def get_sector_for_ticker(ticker: str) -> str:
    return SECTOR_MAP.get(ticker.upper(), "tech")


def _sec_headers() -> dict[str, str]:
    return {"User-Agent": settings.sec_user_agent}


async def fetch_sec(url: str) -> httpx.Response:
    async with httpx.AsyncClient(timeout=60.0) as client:
        return await client.get(url, headers=_sec_headers())


def date_minus_days(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")


def _map_form_type(raw: str) -> str | None:
    u = raw.upper()
    if "13F" in u:
        return "13F"
    if u == "4" or "FORM 4" in u:
        return "4"
    if "13D" in u:
        return "13D"
    if "13G" in u:
        return "13G"
    return None


def _parse_efts_hits(data: dict, form_type: str) -> list[dict[str, Any]]:
    hits = data.get("hits", {}).get("hits", [])
    results: list[dict[str, Any]] = []
    for hit in hits:
        src = hit.get("_source", {})
        entity_name = src.get("entity_name") or (src.get("display_names") or ["Unknown"])[0]
        filed_at = src.get("file_date") or src.get("period_of_report") or datetime.now(UTC).isoformat()
        accession_no = src.get("file_num") or f"efts-{len(results)}"
        ft = _map_form_type(src.get("form_type", form_type)) or form_type
        if "T" not in filed_at:
            filed_at = f"{filed_at}T12:00:00.000Z"
        results.append({
            "id": f"efts-{accession_no}-{len(results)}",
            "investorName": entity_name,
            "investorCik": src.get("cik", ""),
            "investorType": "hedge_fund",
            "formType": ft,
            "filedAt": filed_at,
            "accessionNo": accession_no,
            "avatarInitials": initials_from_name(entity_name),
            "avatarColor": "blue",
        })
    return results


async def fetch_efts_filings(form_type: str, start_days: int) -> list[dict[str, Any]]:
    startdt = date_minus_days(start_days)
    q = '"13F-HR"' if form_type == "13F" else f'"{form_type}"'
    extra = "&forms=13F-HR" if form_type == "13F" else ""
    url = (
        f"https://efts.sec.gov/LATEST/search-index?q={q}"
        f"&dateRange=custom&startdt={startdt}"
        f"&_source=file_date,entity_name,file_num,period_of_report,form_type{extra}"
    )
    try:
        res = await fetch_sec(url)
        if res.status_code != 200:
            return []
        return _parse_efts_hits(res.json(), form_type)
    except Exception:
        return []


async def fetch_form4_atom() -> list[dict[str, Any]]:
    url = (
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent"
        "&type=4&dateb=&owner=include&count=20&search_text=&output=atom"
    )
    try:
        res = await fetch_sec(url)
        if res.status_code != 200:
            return []
        xml = res.text
        entries = xml.split("<entry>")[1:]
        results: list[dict[str, Any]] = []
        for entry in entries:
            title_m = re.search(r"<title[^>]*>([^<]+)</title>", entry, re.I)
            updated_m = re.search(r"<updated>([^<]+)</updated>", entry)
            title = (title_m.group(1).strip() if title_m else "Form 4 Filing")
            filed_at = updated_m.group(1) if updated_m else datetime.now(UTC).isoformat()
            action = None
            if re.search(r"sell|sold|disposition", title, re.I):
                action = "sell"
            elif re.search(r"buy|purchase|acquired", title, re.I):
                action = "buy"
            name_part = title.split(" - ")[0] if " - " in title else title
            results.append({
                "id": f"form4-{len(results)}-{filed_at}",
                "investorName": name_part[:80],
                "investorCik": "",
                "investorType": "individual",
                "formType": "4",
                "filedAt": filed_at,
                "action": action,
                "accessionNo": f"atom-4-{len(results)}",
                "avatarInitials": initials_from_name(name_part),
                "avatarColor": "coral" if action == "sell" else "green",
            })
        return results
    except Exception:
        return []


async def get_recent_filings(form_types: list[str] | None = None) -> list[dict[str, Any]]:
    types = form_types or ["13F", "4", "13D", "13G"]
    batches: list[dict[str, Any]] = []
    try:
        if "13F" in types:
            batches.extend(await fetch_efts_filings("13F", 90))
        if "13D" in types:
            batches.extend(await fetch_efts_filings("13D", 7))
        if "13G" in types:
            batches.extend(await fetch_efts_filings("13G", 7))
        if "4" in types:
            batches.extend(await fetch_form4_atom())
        if batches:
            seen: set[str] = set()
            unique = []
            for f in batches:
                if f["id"] not in seen:
                    seen.add(f["id"])
                    unique.append(f)
            return unique
    except Exception:
        pass
    if form_types:
        return [f for f in MOCK_FILINGS if f["formType"] in form_types]
    return list(MOCK_FILINGS)


def filter_mock_investors(
    investor_type: str | None = None, q: str | None = None
) -> list[dict[str, Any]]:
    investors = list(MOCK_INVESTORS)
    if investor_type and investor_type != "all":
        investors = [i for i in investors if i["type"] == investor_type]
    if q:
        ql = q.lower()
        investors = [i for i in investors if ql in i["name"].lower()]
    return investors


def get_mock_investor_profile(cik: str) -> dict[str, Any] | None:
    padded = pad_cik(cik)
    if padded in MOCK_INVESTOR_PROFILES:
        return dict(MOCK_INVESTOR_PROFILES[padded])
    for inv in MOCK_INVESTORS:
        if pad_cik(inv["cik"]) == padded:
            return {
                **inv,
                "holdings": [],
                "totalHoldings": inv["holdingsCount"],
                "top5Concentration": 0,
                "quarterlyTurnover": 0,
                "description": f"{inv['name']} · CIK {inv['cik']} · 13F filer",
            }
    return None
