"""Keyword-based news topic tagging (no ML)."""

from __future__ import annotations

import re

TOPIC_RULES: list[tuple[str, str]] = [
    (r"earnings|profit|revenue|quarterly result|financial result", "earnings"),
    (r"dividend|payout|dps", "dividend"),
    (r"expansion|capacity|plant|investment|capex", "expansion"),
    (r"litigation|court|lawsuit|arbitration", "litigation"),
    (r"inflation|cpi|policy rate|sbp|macro|gdp|imf", "macro"),
    (r"secp|regulatory|approval|compliance", "regulatory"),
    (r"rights?\s+issue|right\s+shares", "rights"),
    (r"buy[\s-]?back|share\s+repurchase", "buyback"),
    (r"financial\s+result|quarterly\s+result|annual\s+result", "result_preview"),
]


def tag_topic(text: str) -> str:
    lower = text.lower()
    for pattern, tag in TOPIC_RULES:
        if re.search(pattern, lower):
            return tag
    return "other"
