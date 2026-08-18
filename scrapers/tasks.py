from celery import chain

from backend.celery_app import celery_app
from backend.services.ratios import run_recompute_ratios
from backend.services.sector import run_refresh_sector_stats
from scrapers.macro.run import run_scrape_macro
from scrapers.news.run import run_scrape_news_playwright, run_scrape_news_rss
from scrapers.psx.announcements import run_scrape_announcements
from scrapers.psx.eod_prices import run_scrape_eod
from scrapers.psx.extract_corporate_actions import run_extract_corporate_actions
from scrapers.psx.extract_material_events import run_extract_material_events
from scrapers.psx.ltp import run_scrape_ltp
from scrapers.psx.parse_pdfs import run_parse_pending_pdfs
from scrapers.psx.tickers import run_scrape_tickers
from scrapers.social.run import run_twitter_scrape_standalone

from backend.services.alerts_runner import run_evaluate_alerts, run_event_alerts_hook
from nlp.ai_summaries import run_summarize_news_batch, run_weekly_summaries
from nlp.sentiment import run_aggregate_daily, run_score_news, run_score_social


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.scrape_tickers",
)
def scrape_tickers(self) -> dict:
    return run_scrape_tickers()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.scrape_eod_prices",
)
def scrape_eod_prices(self) -> dict:
    return run_scrape_eod()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    name="scrapers.tasks.scrape_ltp_prices",
)
def scrape_ltp_prices(self) -> dict:
    return run_scrape_ltp()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.scrape_announcements",
)
def scrape_announcements(self) -> dict:
    result = run_scrape_announcements()
    if result.get("ingested", 0) > 0:
        extract_corporate_actions.delay()
        extract_material_events.delay()
        symbols = result.get("symbols", [])
        if symbols:
            run_event_alerts_hook(symbols)
    return result


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks._parse_pdfs_impl",
)
def _parse_pdfs_impl(self, limit: int = 50) -> dict:
    return run_parse_pending_pdfs(limit=limit)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.recompute_ratios",
)
def recompute_ratios(self, _parse_result: dict | None = None) -> dict:
    return run_recompute_ratios()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.parse_pending_pdfs",
)
def parse_pending_pdfs(self, limit: int = 50) -> dict:
    workflow = chain(_parse_pdfs_impl.s(limit), recompute_ratios.s())
    return workflow.apply_async().get()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.extract_corporate_actions",
)
def extract_corporate_actions(self) -> dict:
    return run_extract_corporate_actions()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.extract_material_events",
)
def extract_material_events(self) -> dict:
    return run_extract_material_events()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.scrape_news_rss",
)
def scrape_news_rss(self) -> dict:
    return run_scrape_news_rss()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.scrape_news_playwright",
)
def scrape_news_playwright(self) -> dict:
    return run_scrape_news_playwright()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.scrape_macro",
)
def scrape_macro(self) -> dict:
    return run_scrape_macro()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.refresh_sector_stats",
)
def refresh_sector_stats(self) -> dict:
    return run_refresh_sector_stats()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.scrape_twitter",
)
def scrape_twitter(self) -> dict:
    result = run_twitter_scrape_standalone()
    score_new_social_posts.delay()
    return result


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.score_new_social_posts",
)
def score_new_social_posts(self) -> dict:
    return run_score_social()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.score_news_articles",
)
def score_news_articles(self) -> dict:
    return run_score_news()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.aggregate_daily_sentiment",
)
def aggregate_daily_sentiment(self) -> dict:
    return run_aggregate_daily()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.summarize_news_batch",
)
def summarize_news_batch(self) -> dict:
    return run_summarize_news_batch()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.generate_weekly_company_summaries",
)
def generate_weekly_company_summaries(self) -> dict:
    return run_weekly_summaries()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.evaluate_alerts",
)
def evaluate_alerts(self) -> dict:
    return run_evaluate_alerts()


@celery_app.task(name="scrapers.tasks.scrape_governance")
def scrape_governance() -> dict:
    from backend.services.ratios import get_sync_session
    from scrapers.governance.from_announcements import ingest_governance_from_announcements

    session = get_sync_session()
    try:
        return ingest_governance_from_announcements(session)
    finally:
        session.close()


@celery_app.task(name="scrapers.tasks.send_daily_digest")
def send_daily_digest() -> dict:
    from backend.services.digest import run_daily_digest

    return run_daily_digest()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,
    max_retries=2,
    name="scrapers.tasks.ingest_sec_13f",
)
def ingest_sec_13f(self) -> dict:
    from scrapers.sec.ingest_13f import run_ingest_13f
    from scrapers.sec.ingest_tickers import run_ingest_tickers

    result = run_ingest_13f()
    run_ingest_tickers()
    return result


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.ingest_sec_delta",
)
def ingest_sec_delta(self) -> dict:
    from scrapers.sec.ingest_delta import run_ingest_delta

    return run_ingest_delta()


@celery_app.task(name="scrapers.tasks.ingest_sec_tickers")
def ingest_sec_tickers() -> dict:
    from scrapers.sec.ingest_tickers import run_ingest_tickers

    return run_ingest_tickers()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=3,
    name="scrapers.tasks.ingest_sec_form4",
)
def ingest_sec_form4(self) -> dict:
    from scrapers.sec.ingest_form4 import run_ingest_form4

    return run_ingest_form4()
