"""Twitter API v2 social post scraper."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
import redis
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.ticker import Ticker
from scrapers.social.base import ingest_social_post, load_alias_map
from scrapers.social.schemas import SocialPostRecord

logger = logging.getLogger(__name__)

TWITTER_API = "https://api.twitter.com/2"
ANALYSTS_PATH = Path(__file__).parent / "config" / "twitter_analysts.json"
SYMBOL_BATCH_SIZE = 10
MAX_RESULTS = 50


def _redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def _since_key(query_hash: str) -> str:
    return f"social:twitter:since:{query_hash}"


def _query_hash(query: str) -> str:
    return hashlib.md5(query.encode()).hexdigest()[:16]


def load_analyst_handles() -> list[str]:
    if not ANALYSTS_PATH.exists():
        return []
    data = json.loads(ANALYSTS_PATH.read_text(encoding="utf-8"))
    return [h.lstrip("@") for h in data]


def _parse_tweet(tweet: dict, includes: dict) -> SocialPostRecord | None:
    tweet_id = tweet.get("id")
    text = tweet.get("text", "")
    if not tweet_id or not text:
        return None
    author_id = tweet.get("author_id", "")
    users = {u["id"]: u for u in includes.get("users", [])}
    user = users.get(author_id, {})
    handle = user.get("username")
    followers = user.get("public_metrics", {}).get("followers_count")
    metrics = tweet.get("public_metrics", {})
    engagement = {
        "likes": metrics.get("like_count", 0),
        "retweets": metrics.get("retweet_count", 0),
        "replies": metrics.get("reply_count", 0),
    }
    created = tweet.get("created_at")
    posted_at = datetime.fromisoformat(created.replace("Z", "+00:00")) if created else datetime.now(UTC)
    url = f"https://twitter.com/{handle}/status/{tweet_id}" if handle else None
    return SocialPostRecord(
        source="twitter",
        external_id=str(tweet_id),
        text=text,
        posted_at=posted_at,
        author_handle=handle,
        author_followers=followers,
        engagement_json=engagement,
        url=url,
    )


def search_tweets(
    query: str,
    *,
    since_id: str | None = None,
    max_results: int = MAX_RESULTS,
) -> tuple[list[SocialPostRecord], str | None]:
    if not settings.twitter_bearer_token:
        logger.warning("TWITTER_BEARER_TOKEN not set — skipping Twitter scrape")
        return [], since_id

    params: dict = {
        "query": query,
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,author_id,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,public_metrics",
    }
    if since_id:
        params["since_id"] = since_id

    headers = {"Authorization": f"Bearer {settings.twitter_bearer_token}"}
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{TWITTER_API}/tweets/search/recent", params=params, headers=headers)
        if resp.status_code == 429:
            logger.warning("Twitter rate limit hit for query: %s", query[:80])
            return [], since_id
        resp.raise_for_status()
        data = resp.json()

    includes = data.get("includes", {})
    records: list[SocialPostRecord] = []
    for tweet in data.get("data", []):
        record = _parse_tweet(tweet, includes)
        if record:
            records.append(record)

    meta = data.get("meta", {})
    new_since_id = meta.get("newest_id") or since_id
    return records, new_since_id


def _active_symbols(session: Session, limit: int | None = None) -> list[str]:
    q = select(Ticker.symbol).where(Ticker.is_active.is_(True)).order_by(Ticker.symbol)
    if limit:
        q = q.limit(limit)
    return list(session.scalars(q).all())


def _cashtag_queries(symbols: list[str]) -> list[str]:
    queries = []
    for i in range(0, len(symbols), SYMBOL_BATCH_SIZE):
        batch = symbols[i : i + SYMBOL_BATCH_SIZE]
        cashtags = " OR ".join(f"${s}" for s in batch)
        queries.append(f"({cashtags}) lang:en -is:retweet")
    return queries


def _analyst_query(handles: list[str]) -> str:
    from_handles = " OR ".join(f"from:{h}" for h in handles[:25])
    return f"({from_handles}) (PSX OR KSE OR pakistan OR stock OR shares) -is:retweet lang:en"


def scrape_twitter(
    session: Session,
    *,
    limit_symbols: int | None = None,
) -> dict:
    alias_map = load_alias_map(session)
    symbols = _active_symbols(session, limit_symbols)
    r = _redis_client()
    ingested = 0
    linked = 0

    queries = _cashtag_queries(symbols)
    analysts = load_analyst_handles()
    if analysts:
        queries.append(_analyst_query(analysts))

    for query in queries:
        qh = _query_hash(query)
        since_id = r.get(_since_key(qh))
        try:
            records, new_since_id = search_tweets(query, since_id=since_id)
        except httpx.HTTPError as exc:
            logger.error("Twitter search failed: %s", exc)
            continue
        if new_since_id:
            r.set(_since_key(qh), new_since_id)
        for record in records:
            post_id, link_count = ingest_social_post(session, record, alias_map)
            if post_id:
                ingested += 1
                linked += link_count

    return {"ingested": ingested, "linked": linked, "queries": len(queries)}


def run_scrape_twitter(limit_symbols: int | None = None) -> dict:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    with Session(engine) as session:
        return scrape_twitter(session, limit_symbols=limit_symbols)
