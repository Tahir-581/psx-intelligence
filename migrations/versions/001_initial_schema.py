"""initial schema with timescaledb

Revision ID: 001_initial
Revises:
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    op.create_table(
        "tickers",
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sector", sa.String(length=100), nullable=False),
        sa.Column("board", sa.String(length=20), nullable=False),
        sa.Column("isin", sa.String(length=20), nullable=True),
        sa.Column("shares_outstanding", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_debt", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_etf", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.PrimaryKeyConstraint("symbol"),
    )

    op.create_table(
        "prices",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("open", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("high", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("low", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("close", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("value_traded", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("time", "symbol"),
        sa.UniqueConstraint("symbol", "time", name="uq_prices_symbol_time"),
    )

    op.execute(
        "SELECT create_hypertable('prices', 'time', if_not_exists => TRUE, migrate_data => TRUE)"
    )
    op.create_index("ix_prices_symbol_time_desc", "prices", ["symbol", sa.text("time DESC")])

    op.create_table(
        "scraper_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scraper_name", sa.String(length=100), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_run_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("records_ingested", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("structure_hash", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scraper_runs_scraper_name", "scraper_runs", ["scraper_name"])


def downgrade() -> None:
    op.drop_index("ix_scraper_runs_scraper_name", table_name="scraper_runs")
    op.drop_table("scraper_runs")
    op.drop_index("ix_prices_symbol_time_desc", table_name="prices")
    op.drop_table("prices")
    op.drop_table("tickers")
