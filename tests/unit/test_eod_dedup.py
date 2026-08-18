from scrapers.psx.eod_prices import dedupe_price_records
from scrapers.psx.schemas import EodPriceRecord


def test_dedupe_price_records_last_wins() -> None:
    ts = 1735902000
    records = [
        EodPriceRecord(
            symbol="KMI30",
            time_unix=ts,
            open=100.0,
            high=105.0,
            low=99.0,
            close=102.0,
            volume=1000,
        ),
        EodPriceRecord(
            symbol="KMI30",
            time_unix=ts,
            open=100.0,
            high=110.0,
            low=98.0,
            close=108.0,
            volume=2000,
        ),
    ]
    deduped = dedupe_price_records(records)
    assert len(deduped) == 1
    assert deduped[0].close == 108.0
    assert deduped[0].volume == 2000


def test_dedupe_price_records_distinct_times_kept() -> None:
    records = [
        EodPriceRecord(
            symbol="ENGRO",
            time_unix=1735902000,
            open=480.0,
            high=490.0,
            low=475.0,
            close=485.0,
            volume=1000,
        ),
        EodPriceRecord(
            symbol="ENGRO",
            time_unix=1735815600,
            open=470.0,
            high=480.0,
            low=465.0,
            close=478.0,
            volume=800,
        ),
    ]
    assert len(dedupe_price_records(records)) == 2
