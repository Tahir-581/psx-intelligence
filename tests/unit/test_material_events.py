"""Unit tests for material event parser."""

from datetime import UTC, datetime

from parsers.material_events import parse_material_events


def test_litigation_event():
    published = datetime(2024, 5, 1, tzinfo=UTC)
    results = parse_material_events(
        symbol="ENGRO",
        title="Litigation update - Court proceedings",
        body_text="Claim amount Rs. 500 million in arbitration.",
        category="litigation",
        published_at=published,
    )
    assert len(results) == 1
    assert results[0].event_type == "litigation"
    assert results[0].significance_score >= 2


def test_contract_event():
    published = datetime(2024, 2, 1, tzinfo=UTC)
    results = parse_material_events(
        symbol="LUCK",
        title="Off-take agreement signed",
        body_text="Supply contract worth Rs. 2 billion with major buyer.",
        category="other",
        published_at=published,
    )
    assert results[0].event_type == "contract"
    assert results[0].amount_pkr is not None


def test_no_event_for_routine():
    published = datetime(2024, 2, 1, tzinfo=UTC)
    results = parse_material_events(
        symbol="MCB",
        title="Board meeting held",
        body_text="Routine board meeting minutes.",
        category="board_meeting",
        published_at=published,
    )
    assert results == []
