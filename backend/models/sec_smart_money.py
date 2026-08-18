from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class SecFiler(Base):
    __tablename__ = "sec_filers"

    cik: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    investor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    last_report_period: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_portfolio_value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    holdings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    top_ticker: Mapped[str] = mapped_column(Text, nullable=False, default="")
    top_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    avatar_initials: Mapped[str] = mapped_column(Text, nullable=False, default="")
    avatar_color: Mapped[str] = mapped_column(Text, nullable=False, default="blue")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SecFiling13f(Base):
    __tablename__ = "sec_filings_13f"

    accession_number: Mapped[str] = mapped_column(String(25), primary_key=True)
    cik: Mapped[str] = mapped_column(String(10), ForeignKey("sec_filers.cik", ondelete="CASCADE"))
    report_period: Mapped[date] = mapped_column(Date, nullable=False)
    filed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    form_type: Mapped[str] = mapped_column(String(20), nullable=False, default="13F-HR")
    quarter_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SecHolding(Base):
    __tablename__ = "sec_holdings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    accession_number: Mapped[str] = mapped_column(
        String(25), ForeignKey("sec_filings_13f.accession_number", ondelete="CASCADE")
    )
    cik: Mapped[str] = mapped_column(String(10), ForeignKey("sec_filers.cik", ondelete="CASCADE"))
    report_period: Mapped[date] = mapped_column(Date, nullable=False)
    name_of_issuer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cusip: Mapped[str] = mapped_column(String(9), nullable=False, default="")
    ticker: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_of_class: Mapped[str] = mapped_column(Text, nullable=False, default="")
    value_usd: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    shares: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    portfolio_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=0)
    qoq_change_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    infotable_sk: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SecCusipTickerMap(Base):
    __tablename__ = "sec_cusip_ticker_map"

    cusip: Mapped[str] = mapped_column(String(9), primary_key=True)
    ticker: Mapped[str] = mapped_column(Text, nullable=False)
    company_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SecIngestionRun(Base):
    __tablename__ = "sec_ingestion_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    quarter_label: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="running")
    row_counts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class SecInsider(Base):
    __tablename__ = "sec_insiders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    reporting_owner_cik: Mapped[str | None] = mapped_column(String(10), nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    company_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    company_cik: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ticker: Mapped[str | None] = mapped_column(Text, nullable=True)
    form_type: Mapped[str] = mapped_column(Text, nullable=False, default="4")
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    shares: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    accession_number: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
