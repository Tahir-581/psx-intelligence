from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://psx:psx@localhost:5432/psx"
    database_url_sync: str = "postgresql://psx:psx@localhost:5432/psx"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    psx_base_url: str = "https://dps.psx.com.pk"
    psx_request_delay_seconds: float = 1.5
    psx_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    market_timezone: str = "Asia/Karachi"

    # Clerk auth
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    # Stripe billing
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_monthly_price_id: str = ""
    stripe_pro_annual_price_id: str = ""

    # Twitter API v2
    twitter_bearer_token: str = ""

    # Anthropic / AI
    anthropic_api_key: str = ""
    ai_daily_article_budget: int = 500
    ai_weekly_summary_enabled: bool = True
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Sentiment (HuggingFace)
    hf_api_token: str = ""
    sentiment_model: str = "ProsusAI/finbert"
    sentiment_inference_url: str = ""

    # Admin
    admin_api_key: str = ""

    # Alerts email (SendGrid)
    sendgrid_api_key: str = ""
    alerts_from_email: str = "alerts@yourdomain.com"

    # API keys (Pro)
    api_key_hash_salt: str = ""

    # Alert evaluator
    alert_eval_interval_minutes: int = 5

    # B2 archive
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket: str = ""
    b2_endpoint: str = "https://api.backblazeb2.com"

    # Sentry
    sentry_dsn: str = ""

    # Web Push
    vapid_public_key: str = ""
    vapid_private_key: str = ""

    # Twilio WhatsApp
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""

    # Billing provider
    billing_provider: str = "stripe"
    lemonsqueezy_api_key: str = ""
    lemonsqueezy_webhook_secret: str = ""
    lemonsqueezy_store_id: str = ""
    lemonsqueezy_pro_variant_id: str = ""

    # Feature flags
    webhooks_enabled: bool = False
    psx_intraday_api_key: str = ""
    significance_ml_enabled: bool = False

    # SEC smart money
    sec_user_agent: str = "PSXIntelligence contact@yourdomain.com"
    sec_13f_zip_url: str = ""
    sec_13f_quarter_label: str = ""
    sec_ingest_delta_days: int = 14
    sec_form4_count: int = 100

    # Social scrapers
    telegram_bot_token: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "psx-platform/1.0"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
