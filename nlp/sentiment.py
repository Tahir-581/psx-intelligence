"""finBERT sentiment scoring and daily aggregation."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import redis
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.news_article import NewsArticle
from backend.models.sentiment_score import SentimentScore
from backend.models.social_post import SocialPost
from backend.models.social_post_ticker import SocialPostTicker

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 2000
ANALYST_HANDLES: set[str] | None = None


@dataclass
class SentimentResult:
    positive: float
    negative: float
    neutral: float
    score: float  # composite in [-1, +1]

    @property
    def badge(self) -> str:
        if self.score >= 0.15:
            return "bullish"
        if self.score <= -0.15:
            return "bearish"
        return "neutral"


@dataclass
class ScoredPost:
    text: str
    posted_at: datetime
    source: str
    author_handle: str | None = None
    result: SentimentResult | None = None


def _redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def truncate_for_model(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text[:max_chars])
    return " ".join(sentences[:3]) if sentences else text[:max_chars]


def _load_analyst_handles() -> set[str]:
    global ANALYST_HANDLES
    if ANALYST_HANDLES is not None:
        return ANALYST_HANDLES
    from pathlib import Path

    import json

    path = Path(__file__).parent.parent / "scrapers" / "social" / "config" / "twitter_analysts.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        ANALYST_HANDLES = {h.lstrip("@").lower() for h in data}
    else:
        ANALYST_HANDLES = set()
    return ANALYST_HANDLES


def _parse_hf_response(data: list | dict) -> SentimentResult:
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict) and "label" in data:
        label = data["label"].lower()
        score_val = float(data.get("score", 0))
        pos = score_val if "positive" in label else 0.0
        neg = score_val if "negative" in label else 0.0
        neu = score_val if "neutral" in label else 0.0
        return SentimentResult(positive=pos, negative=neg, neutral=neu, score=pos - neg)
    if isinstance(data, list):
        probs = {item["label"].lower(): float(item["score"]) for item in data}
        pos = probs.get("positive", 0.0)
        neg = probs.get("negative", 0.0)
        neu = probs.get("neutral", 0.0)
        return SentimentResult(positive=pos, negative=neg, neutral=neu, score=pos - neg)
    return SentimentResult(positive=0.33, negative=0.33, neutral=0.34, score=0.0)


def score_text(text: str) -> SentimentResult:
    """Score text via HuggingFace Inference API or local endpoint."""
    truncated = truncate_for_model(text)
    if not truncated:
        return SentimentResult(positive=0.0, negative=0.0, neutral=1.0, score=0.0)

    if settings.sentiment_inference_url:
        url = settings.sentiment_inference_url
        headers = {}
    elif settings.hf_api_token:
        model = settings.sentiment_model
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {settings.hf_api_token}"}
    else:
        logger.debug("No HF token — returning neutral sentiment")
        return SentimentResult(positive=0.33, negative=0.33, neutral=0.34, score=0.0)

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json={"inputs": truncated}, headers=headers)
            resp.raise_for_status()
            return _parse_hf_response(resp.json())
    except Exception as exc:
        logger.warning("Sentiment scoring failed: %s", exc)
        return SentimentResult(positive=0.33, negative=0.33, neutral=0.34, score=0.0)


def recency_weight(posted_at: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(UTC)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=UTC)
    age = now - posted_at
    if age <= timedelta(hours=6):
        return 3.0
    if age <= timedelta(hours=24):
        return 2.0
    return 1.0


def author_weight(handle: str | None, source: str) -> float:
    if source == "twitter" and handle and handle.lower() in _load_analyst_handles():
        return 3.0
    return 1.0


def aggregate_posts(posts: list[ScoredPost], now: datetime | None = None) -> SentimentResult:
    """Weighted aggregate of scored posts."""
    if not posts:
        return SentimentResult(positive=0.0, negative=0.0, neutral=1.0, score=0.0)

    total_w = 0.0
    w_pos = w_neg = w_neu = w_score = 0.0
    for post in posts:
        if not post.result:
            continue
        w = recency_weight(post.posted_at, now) * author_weight(post.author_handle, post.source)
        total_w += w
        w_pos += post.result.positive * w
        w_neg += post.result.negative * w
        w_neu += post.result.neutral * w
        w_score += post.result.score * w

    if total_w == 0:
        return SentimentResult(positive=0.0, negative=0.0, neutral=1.0, score=0.0)

    return SentimentResult(
        positive=w_pos / total_w,
        negative=w_neg / total_w,
        neutral=w_neu / total_w,
        score=max(-1.0, min(1.0, w_score / total_w)),
    )


def cache_article_sentiment(article_id: int, result: SentimentResult) -> None:
    r = _redis()
    key = f"article:{article_id}:sentiment"
    r.setex(key, 86400 * 7, f"{result.score}:{result.badge}")


def get_cached_article_sentiment(article_id: int) -> tuple[float, str] | None:
    r = _redis()
    val = r.get(f"article:{article_id}:sentiment")
    if not val:
        return None
    parts = val.split(":", 1)
    if len(parts) == 2:
        return float(parts[0]), parts[1]
    return None


def score_new_social_posts(session: Session, limit: int = 200) -> int:
    """Score unscored social posts (cache scores in Redis)."""
    rows = session.execute(
        select(SocialPost)
        .order_by(SocialPost.ingested_at.desc())
        .limit(limit)
    ).scalars().all()
    count = 0
    r = _redis()
    for post in rows:
        key = f"social:{post.id}:sentiment"
        if r.exists(key):
            continue
        result = score_text(post.text)
        r.setex(key, 86400 * 30, f"{result.score}:{result.positive}:{result.negative}:{result.neutral}")
        count += 1
    return count


def score_news_articles(session: Session, limit: int = 200) -> int:
    """Score news articles not yet cached."""
    rows = session.execute(
        select(NewsArticle).order_by(NewsArticle.ingested_at.desc()).limit(limit)
    ).scalars().all()
    count = 0
    for article in rows:
        if get_cached_article_sentiment(article.id):
            continue
        text = f"{article.headline}. {article.excerpt or ''}"
        result = score_text(text)
        cache_article_sentiment(article.id, result)
        count += 1
    return count


def _day_bucket(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def aggregate_daily_sentiment(session: Session, target_date: datetime | None = None) -> int:
    """Aggregate per-symbol per-source daily sentiment into hypertable."""
    now = target_date or datetime.now(UTC)
    day_start = _day_bucket(now)
    day_end = day_start + timedelta(days=1)
    r = _redis()

    symbols = set()
    social_rows = session.execute(
        select(SocialPost, SocialPostTicker.symbol)
        .join(SocialPostTicker, SocialPostTicker.post_id == SocialPost.id)
        .where(SocialPost.posted_at >= day_start, SocialPost.posted_at < day_end)
    ).all()
    for post, sym in social_rows:
        symbols.add(sym)

    news_rows = session.execute(
        select(NewsArticle)
        .where(NewsArticle.published_at >= day_start, NewsArticle.published_at < day_end)
    ).scalars().all()

    from backend.models.news_article_ticker import NewsArticleTicker

    news_by_symbol: dict[str, list[NewsArticle]] = {}
    for article in news_rows:
        tickers = session.scalars(
            select(NewsArticleTicker.symbol).where(NewsArticleTicker.article_id == article.id)
        ).all()
        for sym in tickers:
            symbols.add(sym)
            news_by_symbol.setdefault(sym, []).append(article)

    rows_written = 0
    for symbol in symbols:
        by_source: dict[str, list[ScoredPost]] = {}

        for post, sym in social_rows:
            if sym != symbol:
                continue
            cached = r.get(f"social:{post.id}:sentiment")
            if cached:
                parts = cached.split(":")
                result = SentimentResult(
                    positive=float(parts[1]) if len(parts) > 1 else 0.33,
                    negative=float(parts[2]) if len(parts) > 2 else 0.33,
                    neutral=float(parts[3]) if len(parts) > 3 else 0.34,
                    score=float(parts[0]),
                )
            else:
                result = score_text(post.text)
            by_source.setdefault(post.source, []).append(
                ScoredPost(
                    text=post.text,
                    posted_at=post.posted_at,
                    source=post.source,
                    author_handle=post.author_handle,
                    result=result,
                )
            )

        news_posts: list[ScoredPost] = []
        for article in news_by_symbol.get(symbol, []):
            cached = get_cached_article_sentiment(article.id)
            if cached:
                score_val, _ = cached
                result = SentimentResult(
                    positive=max(0, score_val),
                    negative=max(0, -score_val),
                    neutral=1 - abs(score_val),
                    score=score_val,
                )
            else:
                result = score_text(f"{article.headline}. {article.excerpt or ''}")
            news_posts.append(
                ScoredPost(
                    text=article.headline,
                    posted_at=article.published_at,
                    source="news",
                    result=result,
                )
            )
        if news_posts:
            by_source["news"] = news_posts

        all_posts: list[ScoredPost] = []
        for source, posts in by_source.items():
            agg = aggregate_posts(posts, now=day_end)
            stmt = insert(SentimentScore).values(
                {
                    "time": day_start,
                    "symbol": symbol,
                    "source": source,
                    "score": Decimal(str(round(agg.score, 4))),
                    "positive_pct": Decimal(str(round(agg.positive, 4))),
                    "negative_pct": Decimal(str(round(agg.negative, 4))),
                    "neutral_pct": Decimal(str(round(agg.neutral, 4))),
                    "post_count": len(posts),
                }
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["time", "symbol", "source"],
                set_={
                    "score": stmt.excluded.score,
                    "positive_pct": stmt.excluded.positive_pct,
                    "negative_pct": stmt.excluded.negative_pct,
                    "neutral_pct": stmt.excluded.neutral_pct,
                    "post_count": stmt.excluded.post_count,
                },
            )
            session.execute(stmt)
            rows_written += 1
            all_posts.extend(posts)

        if all_posts:
            total_agg = aggregate_posts(all_posts, now=day_end)
            stmt = insert(SentimentScore).values(
                {
                    "time": day_start,
                    "symbol": symbol,
                    "source": "aggregate",
                    "score": Decimal(str(round(total_agg.score, 4))),
                    "positive_pct": Decimal(str(round(total_agg.positive, 4))),
                    "negative_pct": Decimal(str(round(total_agg.negative, 4))),
                    "neutral_pct": Decimal(str(round(total_agg.neutral, 4))),
                    "post_count": len(all_posts),
                }
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["time", "symbol", "source"],
                set_={
                    "score": stmt.excluded.score,
                    "positive_pct": stmt.excluded.positive_pct,
                    "negative_pct": stmt.excluded.negative_pct,
                    "neutral_pct": stmt.excluded.neutral_pct,
                    "post_count": stmt.excluded.post_count,
                },
            )
            session.execute(stmt)
            rows_written += 1

    session.commit()
    return rows_written


def run_score_social() -> dict:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    with Session(engine) as session:
        count = score_new_social_posts(session)
    return {"scored": count}


def run_score_news() -> dict:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    with Session(engine) as session:
        count = score_news_articles(session)
    return {"scored": count}


def run_aggregate_daily() -> dict:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    with Session(engine) as session:
        rows = aggregate_daily_sentiment(session)
    return {"rows_written": rows}
