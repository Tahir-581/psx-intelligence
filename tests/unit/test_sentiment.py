"""Tests for sentiment scoring and aggregation."""

from datetime import UTC, datetime, timedelta

from nlp.sentiment import (
    ScoredPost,
    SentimentResult,
    aggregate_posts,
    recency_weight,
    score_text,
    truncate_for_model,
)


def test_truncate_for_model():
    text = "A. " * 500
    result = truncate_for_model(text, max_chars=100)
    assert len(result) <= 100


def test_recency_weight():
    now = datetime.now(UTC)
    assert recency_weight(now - timedelta(hours=3), now) == 3.0
    assert recency_weight(now - timedelta(hours=12), now) == 2.0
    assert recency_weight(now - timedelta(days=2), now) == 1.0


def test_aggregate_posts_weighted():
    now = datetime.now(UTC)
    posts = [
        ScoredPost(
            text="bullish",
            posted_at=now - timedelta(hours=2),
            source="twitter",
            author_handle="test",
            result=SentimentResult(positive=0.8, negative=0.1, neutral=0.1, score=0.7),
        ),
        ScoredPost(
            text="bearish",
            posted_at=now - timedelta(days=3),
            source="news",
            result=SentimentResult(positive=0.1, negative=0.8, neutral=0.1, score=-0.7),
        ),
    ]
    agg = aggregate_posts(posts, now=now)
    assert -1.0 <= agg.score <= 1.0
    assert agg.score > 0  # recent bullish should dominate


def test_score_text_no_token_returns_neutral(monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "hf_api_token", "")
    monkeypatch.setattr(settings, "sentiment_inference_url", "")
    result = score_text("Market rallies on strong earnings")
    assert -1.0 <= result.score <= 1.0
    assert result.neutral > 0
