"""Claude AI summaries for news articles and weekly company briefs."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import redis
from sqlalchemy import create_engine, desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.ai_summary import AiSummary
from backend.models.announcement import Announcement
from backend.models.computed_ratio import ComputedRatio
from backend.models.insider_trade import InsiderTrade
from backend.models.news_article import NewsArticle
from backend.models.news_article_ticker import NewsArticleTicker
from backend.models.ownership import OwnershipSnapshot
from backend.models.ticker import Ticker

logger = logging.getLogger(__name__)


def _redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def _daily_budget_key() -> str:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"ai:articles:today:{today}"


def check_article_budget() -> bool:
    if not settings.anthropic_api_key:
        return False
    r = _redis()
    count = int(r.get(_daily_budget_key()) or 0)
    return count < settings.ai_daily_article_budget


def increment_article_budget() -> None:
    r = _redis()
    key = _daily_budget_key()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, 86400)
    pipe.execute()


def _anthropic_client():
    import anthropic

    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _call_claude(prompt: str, max_tokens: int = 300) -> tuple[str, int]:
    if not settings.anthropic_api_key:
        return "", 0
    client = _anthropic_client()
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text if message.content else ""
    tokens = message.usage.input_tokens + message.usage.output_tokens
    return text.strip(), tokens


def summarize_article_text(headline: str, excerpt: str | None) -> tuple[str, int]:
    prompt = (
        "Summarize this Pakistan stock market news article in exactly 2 concise sentences. "
        "Focus on market impact for investors.\n\n"
        f"Headline: {headline}\n"
        f"Excerpt: {excerpt or headline}"
    )
    return _call_claude(prompt, max_tokens=200)


def summarize_news_batch(session: Session, limit: int = 50) -> dict:
    if not check_article_budget():
        logger.warning("Daily AI article budget exceeded — skipping batch")
        return {"summarized": 0, "skipped": "budget"}

    articles = session.scalars(
        select(NewsArticle)
        .outerjoin(
            AiSummary,
            (AiSummary.reference_id == NewsArticle.id)
            & (AiSummary.summary_type == "news_article"),
        )
        .where(AiSummary.id.is_(None))
        .order_by(desc(NewsArticle.published_at))
        .limit(limit)
    ).all()

    summarized = 0
    for article in articles:
        if not check_article_budget():
            break
        try:
            content, tokens = summarize_article_text(article.headline, article.excerpt)
            if not content:
                continue
            stmt = insert(AiSummary).values(
                {
                    "symbol": None,
                    "summary_type": "news_article",
                    "reference_id": article.id,
                    "content": content,
                    "model": settings.anthropic_model,
                    "tokens_used": tokens,
                }
            )
            stmt = stmt.on_conflict_do_nothing(constraint="uq_ai_summaries_type_symbol_ref")
            session.execute(stmt)
            session.commit()
            increment_article_budget()
            summarized += 1
        except Exception as exc:
            logger.error("Failed to summarize article %s: %s", article.id, exc)
            session.rollback()

    return {"summarized": summarized}


def _build_weekly_prompt(session: Session, symbol: str) -> str:
    ticker = session.scalar(select(Ticker).where(Ticker.symbol == symbol))
    sector = ticker.sector if ticker else "Unknown"

    ratios = session.scalars(
        select(ComputedRatio)
        .where(ComputedRatio.symbol == symbol)
        .order_by(desc(ComputedRatio.computed_at))
        .limit(5)
    ).all()
    ratio_text = ", ".join(f"{r.ratio_code}={r.value}" for r in ratios) if ratios else "N/A"

    announcements = session.scalars(
        select(Announcement)
        .where(Announcement.symbol == symbol)
        .order_by(desc(Announcement.published_at))
        .limit(5)
    ).all()
    ann_text = "\n".join(f"- {a.title}" for a in announcements) if announcements else "None"

    since = datetime.now(UTC) - timedelta(days=7)
    news = session.execute(
        select(NewsArticle.headline)
        .join(NewsArticleTicker, NewsArticleTicker.article_id == NewsArticle.id)
        .where(NewsArticleTicker.symbol == symbol, NewsArticle.published_at >= since)
        .order_by(desc(NewsArticle.published_at))
        .limit(10)
    ).all()
    news_text = "\n".join(f"- {h}" for h, in news) if news else "None"

    since_90 = datetime.now(UTC) - timedelta(days=90)
    insider_rows = session.scalars(
        select(InsiderTrade)
        .where(InsiderTrade.symbol == symbol, InsiderTrade.transaction_date >= since_90.date())
    ).all()
    net_buy = sum(
        (t.shares or 0) if t.transaction_type == "buy" else -(t.shares or 0)
        for t in insider_rows
    )

    ownership_rows = session.scalars(
        select(OwnershipSnapshot)
        .where(OwnershipSnapshot.symbol == symbol)
        .order_by(desc(OwnershipSnapshot.as_of_date))
        .limit(10)
    ).all()
    free_float = next(
        (r.pct_outstanding for r in ownership_rows if r.holder_category in ("public", "general_public")),
        None,
    )
    own_text = f"Free float {free_float}%" if free_float else "N/A"

    return (
        f"Write a 5-6 sentence plain-English weekly brief for PSX ticker {symbol} "
        f"({ticker.name if ticker else symbol}).\n"
        f"Sector: {sector}\n"
        f"Key ratios: {ratio_text}\n"
        f"Recent announcements:\n{ann_text}\n"
        f"Last 7 days news:\n{news_text}\n"
        f"Insider 90d net shares: {net_buy}\n"
        f"Ownership: {own_text}\n"
        "Be factual, concise, and investor-focused. No disclaimers."
    )


def generate_weekly_company_summaries(session: Session) -> dict:
    if not settings.ai_weekly_summary_enabled or not settings.anthropic_api_key:
        return {"generated": 0, "skipped": "disabled"}

    symbols = list(
        session.scalars(select(Ticker.symbol).where(Ticker.is_active.is_(True))).all()
    )
    generated = 0
    errors = 0
    for symbol in symbols:
        if errors / max(generated + errors, 1) > 0.10 and generated > 10:
            logger.error("Weekly summary error rate > 10%% — halting batch")
            break
        try:
            prompt = _build_weekly_prompt(session, symbol)
            content, tokens = _call_claude(prompt, max_tokens=400)
            if not content:
                errors += 1
                continue
            stmt = insert(AiSummary).values(
                {
                    "symbol": symbol,
                    "summary_type": "company_weekly",
                    "reference_id": None,
                    "content": content,
                    "model": settings.anthropic_model,
                    "tokens_used": tokens,
                }
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_ai_summaries_type_symbol_ref",
                set_={
                    "content": stmt.excluded.content,
                    "model": stmt.excluded.model,
                    "tokens_used": stmt.excluded.tokens_used,
                    "generated_at": datetime.now(UTC),
                },
            )
            session.execute(stmt)
            session.commit()
            generated += 1
        except Exception as exc:
            logger.error("Weekly summary failed for %s: %s", symbol, exc)
            session.rollback()
            errors += 1

    return {"generated": generated, "errors": errors}


def run_summarize_news_batch() -> dict:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    with Session(engine) as session:
        return summarize_news_batch(session)


def run_weekly_summaries() -> dict:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    with Session(engine) as session:
        return generate_weekly_company_summaries(session)


def generate_single_company_summary(symbol: str) -> bool:
    if not settings.anthropic_api_key:
        return False
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    with Session(engine) as session:
        try:
            prompt = _build_weekly_prompt(session, symbol.upper())
            content, tokens = _call_claude(prompt, max_tokens=400)
            if not content:
                return False
            stmt = insert(AiSummary).values(
                {
                    "symbol": symbol.upper(),
                    "summary_type": "company_weekly",
                    "reference_id": None,
                    "content": content,
                    "model": settings.anthropic_model,
                    "tokens_used": tokens,
                }
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_ai_summaries_type_symbol_ref",
                set_={
                    "content": stmt.excluded.content,
                    "model": stmt.excluded.model,
                    "tokens_used": stmt.excluded.tokens_used,
                    "generated_at": datetime.now(UTC),
                },
            )
            session.execute(stmt)
            session.commit()
            return True
        except Exception as exc:
            logger.error("Single summary failed for %s: %s", symbol, exc)
            session.rollback()
            return False
