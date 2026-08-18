"""NLP announcement classifier tests."""

from nlp.classifier import classify_announcement


def test_dividend_classification():
    cat, conf = classify_announcement("Board approves interim cash dividend of Rs 5")
    assert cat == "dividend"
    assert conf >= 0.8


def test_board_change_classification():
    cat, _ = classify_announcement("Appointment of Mr. Ali as Director")
    assert cat == "board_change"


def test_other_fallback():
    cat, conf = classify_announcement("General notice to shareholders")
    assert cat in ("other", "agm_egm")
    assert conf > 0
