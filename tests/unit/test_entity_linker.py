"""Unit tests for entity linker."""

from nlp.entity_linker import build_alias_map, link_tickers


def test_exact_symbol_match():
    alias_map = build_alias_map(["ENGRO", "LUCK"], ["Engro Corporation Limited", "Lucky Cement"])
    links = link_tickers("ENGRO reported strong earnings", alias_map)
    assert any(l.symbol == "ENGRO" for l in links)


def test_fuzzy_name_match():
    alias_map = build_alias_map(["ENGRO"], ["Engro Corporation Limited"])
    links = link_tickers("Engro Corporation posts record profit", alias_map)
    assert any(l.symbol == "ENGRO" and l.confidence >= 0.7 for l in links)


def test_low_confidence_skipped():
    alias_map = build_alias_map(["ENGRO"], ["Engro Corporation Limited"])
    links = link_tickers("Random unrelated market news today", alias_map, min_confidence=0.99)
    assert links == []
