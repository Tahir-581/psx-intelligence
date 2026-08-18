import json
from pathlib import Path

import pytest

from scrapers.psx.client import parse_market_watch, structure_hash
from scrapers.psx.schemas import PsxSymbolApiItem, parse_eod_rows, parse_symbols_json

FIXTURES = Path(__file__).parent.parent / "fixtures"
MARKET_WATCH_SNIPPET = """
<table class="tbl"><thead class="tbl__head"><tr>
<th>SYMBOL</th><th>SECTOR</th><th>LISTED IN</th><th>LDCP</th><th>OPEN</th>
<th>HIGH</th><th>LOW</th><th>CURRENT</th><th>CHANGE</th><th>CHANGE (%)</th><th>VOLUME</th>
</tr></thead><tbody class="tbl__body">
<tr><td data-search="ENGRO"><a class="tbl__symbol" href="/company/ENGRO"><strong>ENGRO</strong></a></td>
<td>0830</td><td>ALLSHR</td><td class="right" data-order="481.99">481.99</td>
<td class="right" data-order="481.99">481.99</td><td class="right" data-order="496">496</td>
<td class="right" data-order="474.01">474.01</td><td class="right" data-order="485.38">485.38</td>
<td class="right" data-order="3.39">3.39</td><td class="right" data-order="0.70">0.70</td>
<td class="right" data-order="4496408">4,496,408</td></tr>
</tbody></table>
"""


def test_structure_hash_stable() -> None:
    assert structure_hash("hello world") == structure_hash("hello   world")


def test_parse_symbols_json_sample() -> None:
    raw = [
        {"symbol": "ENGRO", "name": "Engro Corporation Limited", "sectorName": "FERTILIZER"},
        {"symbol": "AKBLTFC6", "name": "Askari Bank(TFC6)", "sectorName": "BILLS AND BONDS", "isDebt": True},
    ]
    records = parse_symbols_json(raw)
    assert len(records) == 2
    assert records[0].symbol == "ENGRO"
    assert records[1].is_debt is True


def test_psx_symbol_api_item() -> None:
    item = PsxSymbolApiItem(symbol="hbl", name="HBL", sectorName="BANKS")
    record = item.to_ticker_record()
    assert record.symbol == "HBL"


def test_parse_eod_rows() -> None:
    payload = {
        "status": 1,
        "data": [[1735902000, 485.38, 4496408, 481.99], [1735815600, 478.3, 3602326, 452.0]],
    }
    records = parse_eod_rows("ENGRO", payload)
    assert len(records) == 2
    assert records[0].close == 485.38
    assert records[0].open == 481.99
    assert records[0].high == 485.38
    assert records[0].low == 481.99


def test_parse_market_watch() -> None:
    rows = parse_market_watch(MARKET_WATCH_SNIPPET)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "ENGRO"
    assert rows[0]["close"] == 485.38
    assert rows[0]["volume"] == 4496408


@pytest.mark.skipif(
    not (FIXTURES / "psx_symbols_sample.json").exists(),
    reason="Live symbols fixture not captured",
)
def test_parse_live_symbols_fixture() -> None:
    raw = json.loads((FIXTURES / "psx_symbols_sample.json").read_text(encoding="utf-8"))
    records = parse_symbols_json(raw)
    assert len(records) > 400
