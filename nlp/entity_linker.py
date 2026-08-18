"""Ticker entity linking via fuzzy alias matching."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

MIN_LINK_CONFIDENCE = 0.70
FUZZY_THRESHOLD = 88


@dataclass
class TickerLink:
    symbol: str
    confidence: float


def normalize_name(name: str) -> str:
    n = name.lower().strip()
    for suffix in (
        " limited",
        " ltd",
        " ltd.",
        " (pvt) limited",
        " pvt ltd",
        " company",
        " co.",
        " plc",
    ):
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return re.sub(r"\s+", " ", n)


def build_alias_map(symbols: list[str], names: list[str]) -> dict[str, str]:
    """Map alias -> symbol."""
    alias_map: dict[str, str] = {}
    for symbol, name in zip(symbols, names, strict=True):
        alias_map[symbol.lower()] = symbol
        alias_map[normalize_name(name)] = symbol
        # First word of company name as abbreviation (e.g. Engro)
        parts = normalize_name(name).split()
        if parts:
            alias_map[parts[0]] = symbol
    # Common PSX shorthand aliases
    extra_aliases = {
        "engro": "ENGRO",
        "lucky": "LUCK",
        "hbl": "HBL",
        "ubl": "UBL",
        "mcb": "MCB",
        "psx": "PSX",
        "kse": "KSE100",
        "fauji": "FFC",
        "ogdc": "OGDC",
        "ppl": "PPL",
        "pso": "PSO",
        "nestle": "NESTLE",
        "unilever": "UNILEVER",
        "packages": "PKGS",
        "meezan": "MEBL",
        "habib metro": "HMB",
        "systems": "SYS",
        "trg": "TRG",
    }
    for alias, sym in extra_aliases.items():
        if sym in symbols:
            alias_map[alias] = sym
    return alias_map


def link_tickers(
    text: str,
    alias_map: dict[str, str],
    *,
    min_confidence: float = MIN_LINK_CONFIDENCE,
) -> list[TickerLink]:
    """Find ticker mentions in text using fuzzy matching."""
    if not text or not alias_map:
        return []

    aliases = list(alias_map.keys())
    seen: set[str] = set()
    links: list[TickerLink] = []

    # Exact symbol matches (uppercase tokens)
    for token in re.findall(r"\b[A-Z]{2,10}\b", text):
        sym = token.upper()
        if sym in {v for v in alias_map.values()} and sym not in seen:
            seen.add(sym)
            links.append(TickerLink(symbol=sym, confidence=1.0))

    # Fuzzy alias matching on sliding windows of words
    words = re.findall(r"[A-Za-z][A-Za-z0-9&.-]*", text)
    for window in (4, 3, 2, 1):
        for i in range(len(words) - window + 1):
            phrase = " ".join(words[i : i + window]).lower()
            if len(phrase) < 3:
                continue
            match = process.extractOne(
                phrase,
                aliases,
                scorer=fuzz.ratio,
                score_cutoff=FUZZY_THRESHOLD,
            )
            if not match:
                continue
            alias, score, _ = match
            symbol = alias_map[alias]
            confidence = round(score / 100.0, 2)
            if confidence < min_confidence or symbol in seen:
                continue
            seen.add(symbol)
            links.append(TickerLink(symbol=symbol, confidence=confidence))

    return sorted(links, key=lambda x: x.confidence, reverse=True)
