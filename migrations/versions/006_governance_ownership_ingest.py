"""governance ownership ingest schema

Revision ID: 006_governance
Revises: 005_phase5
Create Date: 2026-06-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_governance"
down_revision: Union[str, None] = "005_phase5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "secp_filings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("form_type", sa.String(length=40), nullable=False),
        sa.Column("filed_at", sa.Date(), nullable=False),
        sa.Column("raw_url", sa.Text(), nullable=True),
        sa.Column("parsed_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "form_type", "filed_at", name="uq_secp_filing"),
    )
    op.create_index("ix_secp_filings_symbol", "secp_filings", ["symbol"])

    op.create_table(
        "board_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=True),
        sa.Column("resignation_date", sa.Date(), nullable=True),
        sa.Column("filing_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.ForeignKeyConstraint(["filing_id"], ["secp_filings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_board_members_symbol", "board_members", ["symbol"])

    op.create_table(
        "credit_ratings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("agency", sa.String(length=20), nullable=False),
        sa.Column("rating", sa.String(length=20), nullable=False),
        sa.Column("outlook", sa.String(length=30), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol", "agency", "effective_date", name="uq_credit_rating"
        ),
    )
    op.create_index("ix_credit_ratings_symbol", "credit_ratings", ["symbol"])

    op.add_column(
        "ownership_snapshots",
        sa.Column("pledged_shares_pct", sa.Numeric(8, 4), nullable=True),
    )
    op.add_column(
        "ownership_snapshots",
        sa.Column("holder_name", sa.String(length=200), nullable=True),
    )

    op.create_table(
        "ingest_archives",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scraper_name", sa.String(length=80), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("b2_key", sa.String(length=512), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingest_archives_scraper", "ingest_archives", ["scraper_name"])

    op.create_table(
        "failed_celery_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=128), nullable=False),
        sa.Column("task_name", sa.String(length=200), nullable=False),
        sa.Column("args_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retried", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_failed_tasks_name", "failed_celery_tasks", ["task_name"])


def downgrade() -> None:
    op.drop_index("ix_failed_tasks_name", table_name="failed_celery_tasks")
    op.drop_table("failed_celery_tasks")
    op.drop_index("ix_ingest_archives_scraper", table_name="ingest_archives")
    op.drop_table("ingest_archives")
    op.drop_column("ownership_snapshots", "holder_name")
    op.drop_column("ownership_snapshots", "pledged_shares_pct")
    op.drop_index("ix_credit_ratings_symbol", table_name="credit_ratings")
    op.drop_table("credit_ratings")
    op.drop_index("ix_board_members_symbol", table_name="board_members")
    op.drop_table("board_members")
    op.drop_index("ix_secp_filings_symbol", table_name="secp_filings")
    op.drop_table("secp_filings")
