from celery import Celery
from celery.schedules import crontab

from backend.config import settings

celery_app = Celery(
    "psx",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "scrapers.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.market_timezone,
    enable_utc=True,
    task_default_queue="default",
    task_routes={
        "scrapers.tasks.scrape_tickers": {"queue": "default"},
        "scrapers.tasks.scrape_eod_prices": {"queue": "market"},
        "scrapers.tasks.scrape_ltp_prices": {"queue": "market"},
        "scrapers.tasks.scrape_announcements": {"queue": "default"},
        "scrapers.tasks.parse_pending_pdfs": {"queue": "default"},
        "scrapers.tasks.recompute_ratios": {"queue": "default"},
        "scrapers.tasks.extract_corporate_actions": {"queue": "default"},
        "scrapers.tasks.extract_material_events": {"queue": "default"},
        "scrapers.tasks.scrape_news_rss": {"queue": "default"},
        "scrapers.tasks.scrape_news_playwright": {"queue": "default"},
        "scrapers.tasks.scrape_macro": {"queue": "default"},
        "scrapers.tasks.refresh_sector_stats": {"queue": "default"},
        "scrapers.tasks.scrape_twitter": {"queue": "default"},
        "scrapers.tasks.score_new_social_posts": {"queue": "default"},
        "scrapers.tasks.score_news_articles": {"queue": "default"},
        "scrapers.tasks.aggregate_daily_sentiment": {"queue": "default"},
        "scrapers.tasks.summarize_news_batch": {"queue": "default"},
        "scrapers.tasks.generate_weekly_company_summaries": {"queue": "default"},
        "scrapers.tasks.evaluate_alerts": {"queue": "default"},
        "scrapers.tasks.ingest_sec_13f": {"queue": "default"},
        "scrapers.tasks.ingest_sec_delta": {"queue": "default"},
        "scrapers.tasks.ingest_sec_tickers": {"queue": "default"},
        "scrapers.tasks.ingest_sec_form4": {"queue": "default"},
    },
    beat_schedule={
        "scrape-tickers-weekly": {
            "task": "scrapers.tasks.scrape_tickers",
            "schedule": crontab(hour=2, minute=0, day_of_week=0),
        },
        "scrape-eod-prices-daily": {
            "task": "scrapers.tasks.scrape_eod_prices",
            "schedule": crontab(hour=16, minute=30, day_of_week="1-5"),
        },
        "scrape-ltp-every-minute": {
            "task": "scrapers.tasks.scrape_ltp_prices",
            "schedule": 60.0,
        },
        "scrape-announcements-market-hours": {
            "task": "scrapers.tasks.scrape_announcements",
            "schedule": crontab(minute="*/15", hour="9-15", day_of_week="1-5"),
        },
        "parse-pending-pdfs-hourly": {
            "task": "scrapers.tasks.parse_pending_pdfs",
            "schedule": crontab(minute=0, hour="9-18", day_of_week="1-5"),
        },
        "recompute-ratios-daily": {
            "task": "scrapers.tasks.recompute_ratios",
            "schedule": crontab(hour=17, minute=0, day_of_week="1-5"),
        },
        "extract-corporate-actions": {
            "task": "scrapers.tasks.extract_corporate_actions",
            "schedule": crontab(minute="5,20,35,50", hour="9-16", day_of_week="1-5"),
        },
        "extract-material-events-nightly": {
            "task": "scrapers.tasks.extract_material_events",
            "schedule": crontab(hour=2, minute=0),
        },
        "scrape-news-rss": {
            "task": "scrapers.tasks.scrape_news_rss",
            "schedule": crontab(minute="*/30", hour="9-16", day_of_week="1-5"),
        },
        "scrape-news-playwright": {
            "task": "scrapers.tasks.scrape_news_playwright",
            "schedule": crontab(minute=0, hour="*/2", day_of_week="1-5"),
        },
        "scrape-macro-daily": {
            "task": "scrapers.tasks.scrape_macro",
            "schedule": crontab(hour=18, minute=0),
        },
        "refresh-sector-stats-daily": {
            "task": "scrapers.tasks.refresh_sector_stats",
            "schedule": crontab(hour=17, minute=30, day_of_week="1-5"),
        },
        "scrape-twitter-market-hours": {
            "task": "scrapers.tasks.scrape_twitter",
            "schedule": crontab(minute=0, hour="9-15/2", day_of_week="1-5"),
        },
        "aggregate-daily-sentiment": {
            "task": "scrapers.tasks.aggregate_daily_sentiment",
            "schedule": crontab(hour=23, minute=0),
        },
        "summarize-news-batch": {
            "task": "scrapers.tasks.summarize_news_batch",
            "schedule": crontab(minute=15, hour="9-16", day_of_week="1-5"),
        },
        "weekly-company-summaries": {
            "task": "scrapers.tasks.generate_weekly_company_summaries",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),
        },
        "evaluate-alerts-market-hours": {
            "task": "scrapers.tasks.evaluate_alerts",
            "schedule": crontab(minute="*/5", hour="9-15", day_of_week="1-5"),
        },
        "evaluate-alerts-off-hours": {
            "task": "scrapers.tasks.evaluate_alerts",
            "schedule": crontab(minute="*/30"),
        },
        "scrape-governance-daily": {
            "task": "scrapers.tasks.scrape_governance",
            "schedule": crontab(hour=3, minute=30),
        },
        "daily-digest-email": {
            "task": "scrapers.tasks.send_daily_digest",
            "schedule": crontab(hour=8, minute=0),
        },
        "ingest-sec-13f-quarterly": {
            "task": "scrapers.tasks.ingest_sec_13f",
            "schedule": crontab(hour=6, minute=0, day_of_month=1, month_of_year="2,5,8,11"),
        },
        "ingest-sec-delta-daily": {
            "task": "scrapers.tasks.ingest_sec_delta",
            "schedule": crontab(hour=7, minute=0),
        },
        "ingest-sec-form4-daily": {
            "task": "scrapers.tasks.ingest_sec_form4",
            "schedule": crontab(hour=8, minute=0),
        },
    },
)
