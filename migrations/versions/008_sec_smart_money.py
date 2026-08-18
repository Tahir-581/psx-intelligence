"""SEC smart money schema

Revision ID: 008_sec_smart_money
Revises: 007_notifications
Create Date: 2026-06-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_sec_smart_money"
down_revision: Union[str, None] = "007_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

sec_investor_type = postgresql.ENUM(
    "hedge_fund",
    "pe_activist",
    "individual",
    "mutual_fund",
    "value_fund",
    "unknown",
    name="sec_investor_type",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        CREATE TYPE sec_investor_type AS ENUM (
          'hedge_fund', 'pe_activist', 'individual',
          'mutual_fund', 'value_fund', 'unknown'
        )
        """
    )

    op.create_table(
        "sec_filers",
        sa.Column("cik", sa.CHAR(length=10), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "investor_type",
            sec_investor_type,
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("last_report_period", sa.Date(), nullable=True),
        sa.Column("last_filing_date", sa.Date(), nullable=True),
        sa.Column("total_portfolio_value", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("holdings_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("top_ticker", sa.Text(), server_default="", nullable=False),
        sa.Column("top_pct", sa.Numeric(precision=8, scale=4), server_default="0", nullable=False),
        sa.Column("avatar_initials", sa.Text(), server_default="", nullable=False),
        sa.Column("avatar_color", sa.Text(), server_default="blue", nullable=False),
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
        sa.PrimaryKeyConstraint("cik"),
    )
    op.execute(
        """
        ALTER TABLE sec_filers ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('english', coalesce(name, ''))) STORED
        """
    )
    op.create_index("idx_sec_filers_name", "sec_filers", ["name"])
    op.create_index("idx_sec_filers_investor_type", "sec_filers", ["investor_type"])
    op.create_index(
        "idx_sec_filers_total_portfolio_value",
        "sec_filers",
        [sa.text("total_portfolio_value DESC")],
    )
    op.create_index(
        "idx_sec_filers_last_filing_date",
        "sec_filers",
        [sa.text("last_filing_date DESC")],
    )
    op.create_index(
        "idx_sec_filers_search_vector",
        "sec_filers",
        ["search_vector"],
        postgresql_using="gin",
    )

    op.create_table(
        "sec_filings_13f",
        sa.Column("accession_number", sa.String(length=25), nullable=False),
        sa.Column("cik", sa.CHAR(length=10), nullable=False),
        sa.Column("report_period", sa.Date(), nullable=False),
        sa.Column("filed_at", sa.Date(), nullable=True),
        sa.Column("form_type", sa.String(length=20), server_default="13F-HR", nullable=False),
        sa.Column("quarter_label", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cik"], ["sec_filers.cik"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("accession_number"),
    )
    op.create_index(
        "idx_sec_filings_13f_cik_period",
        "sec_filings_13f",
        ["cik", "report_period"],
        unique=True,
    )
    op.create_index(
        "idx_sec_filings_13f_report_period",
        "sec_filings_13f",
        [sa.text("report_period DESC")],
    )

    op.create_table(
        "sec_holdings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("accession_number", sa.String(length=25), nullable=False),
        sa.Column("cik", sa.CHAR(length=10), nullable=False),
        sa.Column("report_period", sa.Date(), nullable=False),
        sa.Column("name_of_issuer", sa.Text(), server_default="", nullable=False),
        sa.Column("cusip", sa.CHAR(length=9), server_default="", nullable=False),
        sa.Column("ticker", sa.Text(), nullable=True),
        sa.Column("title_of_class", sa.Text(), server_default="", nullable=False),
        sa.Column("value_usd", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("shares", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("portfolio_pct", sa.Numeric(precision=10, scale=6), server_default="0", nullable=False),
        sa.Column("qoq_change_pct", sa.Numeric(precision=10, scale=4), server_default="0", nullable=False),
        sa.Column("is_new", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("infotable_sk", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["accession_number"], ["sec_filings_13f.accession_number"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["cik"], ["sec_filers.cik"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sec_holdings_cik_period", "sec_holdings", ["cik", "report_period"])
    op.create_index("idx_sec_holdings_accession", "sec_holdings", ["accession_number"])
    op.create_index(
        "idx_sec_holdings_ticker",
        "sec_holdings",
        ["ticker"],
        postgresql_where=sa.text("ticker IS NOT NULL"),
    )
    op.create_index(
        "idx_sec_holdings_value",
        "sec_holdings",
        ["cik", "report_period", sa.text("value_usd DESC")],
    )
    op.create_index(
        "idx_sec_holdings_unique_position",
        "sec_holdings",
        ["accession_number", "cusip", "name_of_issuer", "title_of_class"],
        unique=True,
    )

    op.create_table(
        "sec_cusip_ticker_map",
        sa.Column("cusip", sa.CHAR(length=9), nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("company_name", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("cusip"),
    )
    op.create_index("idx_sec_cusip_ticker_map_ticker", "sec_cusip_ticker_map", ["ticker"])

    op.create_table(
        "sec_ingestion_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("quarter_label", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), server_default="running", nullable=False),
        sa.Column(
            "row_counts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_sec_ingestion_runs_quarter",
        "sec_ingestion_runs",
        [sa.text("quarter_label DESC")],
    )

    op.create_table(
        "sec_insiders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("reporting_owner_cik", sa.CHAR(length=10), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("company_name", sa.Text(), server_default="", nullable=False),
        sa.Column("company_cik", sa.CHAR(length=10), nullable=True),
        sa.Column("ticker", sa.Text(), nullable=True),
        sa.Column("form_type", sa.Text(), server_default="4", nullable=False),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("action", sa.Text(), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=True),
        sa.Column("shares", sa.BigInteger(), nullable=True),
        sa.Column("avg_price", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("accession_number", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        ALTER TABLE sec_insiders ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
          to_tsvector('english',
            coalesce(name, '') || ' ' || coalesce(company_name, '') || ' ' || coalesce(ticker, ''))
        ) STORED
        """
    )
    op.create_index("idx_sec_insiders_name", "sec_insiders", ["name"])
    op.create_index("idx_sec_insiders_reporting_owner_cik", "sec_insiders", ["reporting_owner_cik"])
    op.create_index(
        "idx_sec_insiders_filed_at",
        "sec_insiders",
        [sa.text("filed_at DESC")],
    )
    op.create_index(
        "idx_sec_insiders_search_vector",
        "sec_insiders",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_sec_insiders_accession_unique",
        "sec_insiders",
        ["accession_number", "name", "transaction_date", "action", "shares"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("sec_insiders")
    op.drop_table("sec_ingestion_runs")
    op.drop_table("sec_cusip_ticker_map")
    op.drop_table("sec_holdings")
    op.drop_table("sec_filings_13f")
    op.drop_table("sec_filers")
    op.execute("DROP TYPE IF EXISTS sec_investor_type")
