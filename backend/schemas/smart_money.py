from typing import Literal

from pydantic import BaseModel, Field

InvestorType = Literal[
    "hedge_fund", "pe_activist", "individual", "mutual_fund", "value_fund"
]
FormType = Literal["13F", "4", "13D", "13G"]
ActionType = Literal["new", "increased", "reduced", "exited", "buy", "sell"]
Sector = Literal["tech", "energy", "finance", "healthcare", "consumer"]


class InvestorOut(BaseModel):
    cik: str
    name: str
    type: InvestorType
    aum: int
    holdings_count: int = Field(alias="holdingsCount")
    last_filing_date: str = Field(alias="lastFilingDate")
    ytd_change: float = Field(alias="ytdChange", default=0)
    top_ticker: str = Field(alias="topTicker")
    top_pct: float = Field(alias="topPct")
    avatar_initials: str = Field(alias="avatarInitials")
    avatar_color: str = Field(alias="avatarColor")

    model_config = {"populate_by_name": True}


class InvestorsResponse(BaseModel):
    investors: list[InvestorOut]
    total: int
    page: int
    limit: int
    total_aum: int = Field(alias="totalAum")

    model_config = {"populate_by_name": True}


class HoldingOut(BaseModel):
    ticker: str
    company_name: str = Field(alias="companyName")
    value: int
    shares: int
    portfolio_pct: float = Field(alias="portfolioPct")
    qoq_change: float = Field(alias="qoqChange")
    is_new: bool = Field(alias="isNew")

    model_config = {"populate_by_name": True}


class HoldingsSummaryOut(BaseModel):
    total_value: int = Field(alias="totalValue")
    holdings_count: int = Field(alias="holdingsCount")
    top5_concentration: float = Field(alias="top5Concentration")

    model_config = {"populate_by_name": True}


class InvestorProfileOut(InvestorOut):
    holdings: list[HoldingOut] = []
    total_holdings: int = Field(alias="totalHoldings")
    top5_concentration: float = Field(alias="top5Concentration")
    quarterly_turnover: float = Field(alias="quarterlyTurnover", default=0)
    description: str = ""
    report_periods: list[str] | None = Field(alias="reportPeriods", default=None)
    latest_report_period: str | None = Field(alias="latestReportPeriod", default=None)

    model_config = {"populate_by_name": True}


class HoldingsResponse(BaseModel):
    holdings: list[HoldingOut]
    total: int
    page: int
    limit: int
    report_period: str = Field(alias="reportPeriod")
    periods: list[str]
    summary: HoldingsSummaryOut

    model_config = {"populate_by_name": True}


class FilingOut(BaseModel):
    id: str
    investor_name: str = Field(alias="investorName")
    investor_cik: str = Field(alias="investorCik")
    investor_type: InvestorType = Field(alias="investorType")
    form_type: FormType = Field(alias="formType")
    ticker: str | None = None
    company_name: str | None = Field(alias="companyName", default=None)
    filed_at: str = Field(alias="filedAt")
    transaction_date: str | None = Field(alias="transactionDate", default=None)
    amount: int | None = None
    shares: int | None = None
    avg_price: float | None = Field(alias="avgPrice", default=None)
    action: ActionType | None = None
    aum: int | None = None
    portfolio_pct: float | None = Field(alias="portfolioPct", default=None)
    accession_no: str = Field(alias="accessionNo")
    avatar_initials: str = Field(alias="avatarInitials")
    avatar_color: str = Field(alias="avatarColor")

    model_config = {"populate_by_name": True}


class FilingsResponse(BaseModel):
    filings: list[FilingOut]


class InvestmentOut(FilingOut):
    sector: Sector | str = "tech"


class InvestmentsResponse(BaseModel):
    investments: list[InvestmentOut]
    total: int
    page: int
    limit: int


class SecInsiderOut(BaseModel):
    id: int
    reporting_owner_cik: str | None = Field(alias="reportingOwnerCik", default=None)
    name: str
    company_name: str = Field(alias="companyName")
    company_cik: str | None = Field(alias="companyCik", default=None)
    ticker: str | None = None
    form_type: str = Field(alias="formType", default="4")
    filed_at: str = Field(alias="filedAt")
    transaction_date: str | None = Field(alias="transactionDate", default=None)
    action: str | None = None
    amount: int | None = None
    shares: int | None = None
    avg_price: float | None = Field(alias="avgPrice", default=None)
    accession_number: str = Field(alias="accessionNumber")

    model_config = {"populate_by_name": True}


class SecInsidersResponse(BaseModel):
    insiders: list[SecInsiderOut]
    total: int
    page: int
    limit: int
