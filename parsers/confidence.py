"""Score parse quality 0-1 based on expected fields found."""

from decimal import Decimal

from parsers.schemas import ParsedFinancialPeriod, ParsedInsiderTrade, ParsedOwnershipSnapshot

CONFIDENCE_THRESHOLD = 0.8

FINANCIAL_REQUIRED = {"revenue", "pat"}
FINANCIAL_OPTIONAL = {
    "gross_profit",
    "ebitda",
    "eps_basic",
    "total_assets",
    "total_equity",
    "total_debt",
    "ocf",
    "capex",
}

INSIDER_REQUIRED_FIELDS = ("director_name", "transaction_date", "transaction_type", "shares")
OWNERSHIP_REQUIRED_CATEGORIES = {"sponsors", "directors", "public", "institutions"}


def score_financial_parse(result: ParsedFinancialPeriod) -> float:
    codes = {item.line_code for item in result.line_items}
    if not codes:
        return 0.0
    required_hits = sum(1 for c in FINANCIAL_REQUIRED if c in codes)
    optional_hits = sum(1 for c in FINANCIAL_OPTIONAL if c in codes)
    score = 0.4 * (required_hits / len(FINANCIAL_REQUIRED))
    score += 0.6 * min(optional_hits / 4, 1.0)
    if result.period_end:
        score = min(score + 0.1, 1.0)
    return round(min(score, 1.0), 2)


def score_insider_parse(trades: list[ParsedInsiderTrade]) -> float:
    if not trades:
        return 0.0
    complete = 0
    for trade in trades:
        fields_ok = all(getattr(trade, f) for f in INSIDER_REQUIRED_FIELDS)
        if fields_ok:
            complete += 1
    return round(complete / len(trades), 2)


def score_ownership_parse(result: ParsedOwnershipSnapshot) -> float:
    if not result.rows:
        return 0.0
    categories = {r.holder_category.lower() for r in result.rows}
    cat_hits = sum(
        1 for c in OWNERSHIP_REQUIRED_CATEGORIES if any(c in cat for cat in categories)
    )
    pct_sum = sum(float(r.pct_outstanding) for r in result.rows)
    pct_ok = 0.2 if 90 <= pct_sum <= 110 else 0.0
    score = 0.6 * min(cat_hits / 2, 1.0) + 0.2 + pct_ok
    if result.as_of_date:
        score += 0.1
    return round(min(score, 1.0), 2)


def needs_review(confidence: float) -> bool:
    return confidence < CONFIDENCE_THRESHOLD
