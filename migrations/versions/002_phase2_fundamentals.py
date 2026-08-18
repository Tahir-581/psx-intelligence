"""phase2 fundamentals schema

Revision ID: 002_phase2
Revises: 001_initial
Create Date: 2026-06-15

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_phase2"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="other"),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("structure_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "published_at", "title", name="uq_announcements_symbol_pub_title"),
    )
    op.create_index("ix_announcements_symbol", "announcements", ["symbol"])
    op.create_index("ix_announcements_category", "announcements", ["category"])
    op.create_index(
        "ix_announcements_symbol_published_desc",
        "announcements",
        ["symbol", sa.text("published_at DESC")],
    )

    op.create_table(
        "financial_periods",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_type", sa.String(length=20), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("fiscal_quarter", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="PKR"),
        sa.Column("source_pdf_url", sa.Text(), nullable=True),
        sa.Column("parser_confidence", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "period_end", "period_type", name="uq_fin_periods"),
    )
    op.create_index("ix_financial_periods_symbol", "financial_periods", ["symbol"])

    op.create_table(
        "financial_line_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("period_id", sa.Integer(), nullable=False),
        sa.Column("line_code", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False, server_default="absolute"),
        sa.ForeignKeyConstraint(["period_id"], ["financial_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("period_id", "line_code", name="uq_fin_line_items"),
    )
    op.create_index("ix_financial_line_items_period_id", "financial_line_items", ["period_id"])

    op.create_table(
        "insider_trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("director_name", sa.String(length=200), nullable=False),
        sa.Column("designation", sa.String(length=200), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("shares", sa.BigInteger(), nullable=False),
        sa.Column("price_per_share", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("post_holding_shares", sa.BigInteger(), nullable=True),
        sa.Column("source_announcement_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_announcement_id"], ["announcements.id"]),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_insider_trades_symbol", "insider_trades", ["symbol"])
    op.create_index(
        "ix_insider_trades_symbol_date_desc",
        "insider_trades",
        ["symbol", sa.text("transaction_date DESC")],
    )

    op.create_table(
        "ownership_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("holder_category", sa.String(length=50), nullable=False),
        sa.Column("shares", sa.BigInteger(), nullable=False),
        sa.Column("pct_outstanding", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("source_pdf_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "as_of_date", "holder_category", name="uq_ownership_snap"),
    )
    op.create_index("ix_ownership_snapshots_symbol", "ownership_snapshots", ["symbol"])

    op.create_table(
        "computed_ratios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("ratio_code", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["symbol"], ["tickers.symbol"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "period_end", "ratio_code", name="uq_computed_ratios"),
    )
    op.create_index("ix_computed_ratios_symbol", "computed_ratios", ["symbol"])

    op.create_table(
        "parser_review_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("raw_excerpt", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parser_review_queue_symbol", "parser_review_queue", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_parser_review_queue_symbol", table_name="parser_review_queue")
    op.drop_table("parser_review_queue")
    op.drop_index("ix_computed_ratios_symbol", table_name="computed_ratios")
    op.drop_table("computed_ratios")
    op.drop_index("ix_ownership_snapshots_symbol", table_name="ownership_snapshots")
    op.drop_table("ownership_snapshots")
    op.drop_index("ix_insider_trades_symbol_date_desc", table_name="insider_trades")
    op.drop_index("ix_insider_trades_symbol", table_name="insider_trades")
    op.drop_table("insider_trades")
    op.drop_index("ix_financial_line_items_period_id", table_name="financial_line_items")
    op.drop_table("financial_line_items")
    op.drop_index("ix_financial_periods_symbol", table_name="financial_periods")
    op.drop_table("financial_periods")
    op.drop_index("ix_announcements_symbol_published_desc", table_name="announcements")
    op.drop_index("ix_announcements_category", table_name="announcements")
    op.drop_index("ix_announcements_symbol", table_name="announcements")
    op.drop_table("announcements")
