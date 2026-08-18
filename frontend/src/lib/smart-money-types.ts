export type InvestorType =
  | "hedge_fund"
  | "pe_activist"
  | "individual"
  | "mutual_fund"
  | "value_fund";

export type FormType = "13F" | "4" | "13D" | "13G";
export type ActionType = "new" | "increased" | "reduced" | "exited" | "buy" | "sell";

export interface SecInvestor {
  cik: string;
  name: string;
  type: InvestorType;
  aum: number;
  holdingsCount: number;
  lastFilingDate: string;
  ytdChange: number;
  topTicker: string;
  topPct: number;
  avatarInitials: string;
  avatarColor: string;
}

export interface SecHolding {
  ticker: string;
  companyName: string;
  value: number;
  shares: number;
  portfolioPct: number;
  qoqChange: number;
  isNew: boolean;
}

export interface SecInvestorProfile extends SecInvestor {
  holdings: SecHolding[];
  totalHoldings: number;
  top5Concentration: number;
  quarterlyTurnover: number;
  description: string;
  reportPeriods?: string[];
  latestReportPeriod?: string;
}

export interface SecFiling {
  id: string;
  investorName: string;
  investorCik: string;
  investorType: InvestorType;
  formType: FormType;
  ticker?: string;
  companyName?: string;
  filedAt: string;
  transactionDate?: string;
  amount?: number;
  shares?: number;
  avgPrice?: number;
  action?: ActionType;
  aum?: number;
  portfolioPct?: number;
  accessionNo: string;
  avatarInitials: string;
  avatarColor: string;
  sector?: string;
}

export interface InvestorsResponse {
  investors: SecInvestor[];
  total: number;
  page: number;
  limit: number;
  totalAum: number;
}

export interface HoldingsResponse {
  holdings: SecHolding[];
  total: number;
  page: number;
  limit: number;
  reportPeriod: string;
  periods: string[];
  summary: {
    totalValue: number;
    holdingsCount: number;
    top5Concentration: number;
  };
}

export interface FilingsResponse {
  filings: SecFiling[];
}

export interface InvestmentsResponse {
  investments: SecFiling[];
  total: number;
  page: number;
  limit: number;
}

export interface SecInsiderRow {
  id: number;
  reportingOwnerCik?: string | null;
  name: string;
  companyName: string;
  companyCik?: string | null;
  ticker?: string | null;
  formType: string;
  filedAt: string;
  transactionDate?: string | null;
  action?: string | null;
  amount?: number | null;
  shares?: number | null;
  avgPrice?: number | null;
  accessionNumber: string;
}

export interface SecInsidersResponse {
  insiders: SecInsiderRow[];
  total: number;
  page: number;
  limit: number;
}
