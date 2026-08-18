"""phase5 screener alerts portfolio schema

Revision ID: 005_phase5
Revises: 004_phase4
Create Date: 2026-06-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_phase5"
down_revision: Union[str, None] = "004_phase4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "index_constituents",
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("index_code", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("symbol", "index_code"),
    )
    op.create_index("ix_index_constituents_index_code", "index_constituents", ["index_code"])

    op.create_table(
        "screener_presets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_screener_presets_user_name"),
    )
    op.create_index("ix_screener_presets_user_id", "screener_presets", ["user_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("alert_type", sa.String(length=40), nullable=False),
        sa.Column("params_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("one_shot", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_user_active", "alerts", ["user_id", "is_active"])
    op.create_index("ix_alerts_symbol_active", "alerts", ["symbol", "is_active"])

    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("delivered_email", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("delivered_in_app", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_alert_events_user_triggered",
        "alert_events",
        ["user_id", sa.text("triggered_at DESC")],
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notifications_user_read_created",
        "notifications",
        ["user_id", "read_at", sa.text("created_at DESC")],
    )

    op.create_table(
        "portfolio_holdings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("avg_buy_price", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portfolio_holdings_user_id", "portfolio_holdings", ["user_id"])
    op.create_index("ix_portfolio_holdings_symbol", "portfolio_holdings", ["symbol"])

    op.create_table(
        "portfolio_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("txn_type", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("txn_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portfolio_transactions_user_id", "portfolio_transactions", ["user_id"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("key_prefix", sa.String(length=20), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_prefix", name="uq_api_keys_key_prefix"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index("ix_portfolio_transactions_user_id", table_name="portfolio_transactions")
    op.drop_table("portfolio_transactions")
    op.drop_index("ix_portfolio_holdings_symbol", table_name="portfolio_holdings")
    op.drop_index("ix_portfolio_holdings_user_id", table_name="portfolio_holdings")
    op.drop_table("portfolio_holdings")
    op.drop_index("ix_notifications_user_read_created", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_alert_events_user_triggered", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_index("ix_alerts_symbol_active", table_name="alerts")
    op.drop_index("ix_alerts_user_active", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_screener_presets_user_id", table_name="screener_presets")
    op.drop_table("screener_presets")
    op.drop_index("ix_index_constituents_index_code", table_name="index_constituents")
    op.drop_table("index_constituents")
