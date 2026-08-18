"""phase3 context schema

Revision ID: 003_phase3
Revises: 002_phase2
Create Date: 2026-06-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_phase3"
down_revision: Union[str, None] = "002_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.String(length=500), nullable=True),
        sa.Column("topic_tag", sa.String(length=30), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url", name="uq_news_articles_source_url"),
        sa.UniqueConstraint("external_id", name="uq_news_articles_external_id"),
    )
    op.create_index(
        "ix_news_articles_published_desc",
        "news_articles",
        [sa.text("published_at DESC")],
    )
    op.create_index("ix_news_articles_source", "news_articles", ["source"])

    op.create_table(
        "news_article_tickers",
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("link_confidence", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["news_articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("article_id", "symbol"),
    )
    op.create_index("ix_news_article_tickers_symbol", "news_article_tickers", ["symbol"])

    op.create_table(
        "corporate_actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=True),
        sa.Column("record_date", sa.Date(), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("amount_per_share", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("ratio", sa.String(length=50), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="PKR"),
        sa.Column("source_announcement_id", sa.Integer(), nullable=True),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_announcement_id"], ["announcements.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol",
            "action_type",
            "announced_at",
            "amount_per_share",
            "ratio",
            name="uq_corporate_actions_key",
        ),
    )
    op.create_index(
        "ix_corporate_actions_symbol_ex_date_desc",
        "corporate_actions",
        ["symbol", sa.text("ex_date DESC")],
    )
    op.create_index(
        "ix_corporate_actions_symbol_announced_desc",
        "corporate_actions",
        ["symbol", sa.text("announced_at DESC")],
    )

    op.create_table(
        "material_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("counterparty", sa.String(length=200), nullable=True),
        sa.Column("amount_pkr", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("significance_score", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_announcement_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_announcement_id"], ["announcements.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol",
            "event_type",
            "event_date",
            "headline",
            name="uq_material_events_key",
        ),
    )
    op.create_index(
        "ix_material_events_symbol_date_desc",
        "material_events",
        ["symbol", sa.text("event_date DESC")],
    )
    op.create_index(
        "ix_material_events_significance_desc",
        "material_events",
        [sa.text("significance_score DESC")],
    )

    op.create_table(
        "macro_series",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("series_code", sa.String(length=30), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.PrimaryKeyConstraint("time", "series_code"),
    )
    op.execute(
        "SELECT create_hypertable('macro_series', 'time', if_not_exists => TRUE, migrate_data => TRUE)"
    )
    op.create_index(
        "ix_macro_series_code_time_desc",
        "macro_series",
        ["series_code", sa.text("time DESC")],
    )

    op.create_table(
        "sector_daily_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("sector", sa.String(length=100), nullable=False),
        sa.Column("company_count", sa.Integer(), nullable=False),
        sa.Column("total_market_cap", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("median_pe", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("median_dividend_yield", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("return_1d", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("return_1w", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("return_1m", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("return_ytd", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("top_gainer_symbol", sa.String(length=20), nullable=True),
        sa.Column("top_loser_symbol", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "sector", name="uq_sector_daily_stats"),
    )
    op.create_index(
        "ix_sector_daily_stats_trade_date_desc",
        "sector_daily_stats",
        [sa.text("trade_date DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_sector_daily_stats_trade_date_desc", table_name="sector_daily_stats")
    op.drop_table("sector_daily_stats")
    op.drop_index("ix_macro_series_code_time_desc", table_name="macro_series")
    op.drop_table("macro_series")
    op.drop_index("ix_material_events_significance_desc", table_name="material_events")
    op.drop_index("ix_material_events_symbol_date_desc", table_name="material_events")
    op.drop_table("material_events")
    op.drop_index("ix_corporate_actions_symbol_announced_desc", table_name="corporate_actions")
    op.drop_index("ix_corporate_actions_symbol_ex_date_desc", table_name="corporate_actions")
    op.drop_table("corporate_actions")
    op.drop_index("ix_news_article_tickers_symbol", table_name="news_article_tickers")
    op.drop_table("news_article_tickers")
    op.drop_index("ix_news_articles_source", table_name="news_articles")
    op.drop_index("ix_news_articles_published_desc", table_name="news_articles")
    op.drop_table("news_articles")
