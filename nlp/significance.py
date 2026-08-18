"""Rule-based significance scoring for material events (no ML)."""

from __future__ import annotations

from decimal import Decimal

EVENT_TYPE_WEIGHT: dict[str, int] = {
    "litigation": 2,
    "regulatory": 2,
    "capex": 2,
    "credit_rating": 2,
    "contract": 1,
    "jv": 1,
    "loan": 1,
    "force_majeure": 2,
    "other": 0,
}

REGULATORY_BODIES = ("secp", "sbp", "nepra", "ogra", "pta", "fbr")


def amount_tier_bonus(amount_pkr: Decimal | None) -> int:
    if amount_pkr is None:
        return 0
    value = float(amount_pkr)
    if value >= 10_000_000_000:
        return 3
    if value >= 1_000_000_000:
        return 2
    if value >= 100_000_000:
        return 1
    return 0


def score_event(event_type: str, text: str, amount_pkr: Decimal | None = None) -> int:
    """Return significance score 1–5."""
    lower = text.lower()
    base = 1 + EVENT_TYPE_WEIGHT.get(event_type, 0)
    base += amount_tier_bonus(amount_pkr)
    if any(body in lower for body in REGULATORY_BODIES):
        base += 1
    if len(text) > 500:
        base += 1
    return max(1, min(5, base))
