"""phase4 intelligence saas schema

Revision ID: 004_phase4
Revises: 003_phase3
Create Date: 2026-06-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_phase4"
down_revision: Union[str, None] = "003_phase3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("plan_tier", sa.String(length=10), nullable=False, server_default="free"),
        sa.Column("stripe_customer_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_watchlists_user_name"),
    )
    op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"])

    op.create_table(
        "watchlist_items",
        sa.Column("watchlist_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["watchlist_id"], ["watchlists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("watchlist_id", "symbol"),
    )
    op.create_index("ix_watchlist_items_symbol", "watchlist_items", ["symbol"])

    op.create_table(
        "social_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("author_handle", sa.String(length=100), nullable=True),
        sa.Column("author_followers", sa.Integer(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("engagement_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_social_posts_source_external"),
    )
    op.create_index(
        "ix_social_posts_symbol_posted_desc",
        "social_posts",
        ["symbol", sa.text("posted_at DESC")],
    )
    op.create_index(
        "ix_social_posts_source_posted_desc",
        "social_posts",
        ["source", sa.text("posted_at DESC")],
    )

    op.create_table(
        "social_post_tickers",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("link_confidence", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["social_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("post_id", "symbol"),
    )
    op.create_index("ix_social_post_tickers_symbol", "social_post_tickers", ["symbol"])

    op.create_table(
        "sentiment_scores",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("positive_pct", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("negative_pct", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("neutral_pct", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("post_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("time", "symbol", "source"),
    )
    op.execute(
        "SELECT create_hypertable('sentiment_scores', 'time', if_not_exists => TRUE, migrate_data => TRUE)"
    )
    op.create_index(
        "ix_sentiment_scores_symbol_time_desc",
        "sentiment_scores",
        ["symbol", sa.text("time DESC")],
    )

    op.create_table(
        "ai_summaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("summary_type", sa.String(length=30), nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "summary_type",
            "symbol",
            "reference_id",
            name="uq_ai_summaries_type_symbol_ref",
        ),
    )
    op.create_index("ix_ai_summaries_symbol_type", "ai_summaries", ["symbol", "summary_type"])

    op.create_table(
        "api_usage",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "window_start"),
    )

    op.add_column(
        "parser_review_queue",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "parser_review_queue",
        sa.Column("reviewer_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("parser_review_queue", "reviewer_note")
    op.drop_column("parser_review_queue", "reviewed_at")
    op.drop_table("api_usage")
    op.drop_index("ix_ai_summaries_symbol_type", table_name="ai_summaries")
    op.drop_table("ai_summaries")
    op.drop_index("ix_sentiment_scores_symbol_time_desc", table_name="sentiment_scores")
    op.drop_table("sentiment_scores")
    op.drop_index("ix_social_post_tickers_symbol", table_name="social_post_tickers")
    op.drop_table("social_post_tickers")
    op.drop_index("ix_social_posts_source_posted_desc", table_name="social_posts")
    op.drop_index("ix_social_posts_symbol_posted_desc", table_name="social_posts")
    op.drop_table("social_posts")
    op.drop_index("ix_watchlist_items_symbol", table_name="watchlist_items")
    op.drop_table("watchlist_items")
    op.drop_index("ix_watchlists_user_id", table_name="watchlists")
    op.drop_table("watchlists")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
