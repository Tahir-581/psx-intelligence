export type MetricInfo = {
  id: string;
  fullName: string;
  definition: string;
  benefit: string;
  aliases?: string[];
};

const METRICS: MetricInfo[] = [
  {
    id: "ltp",
    fullName: "Last Traded Price",
    definition: "The most recent price at which the stock was bought or sold on PSX during the current session.",
    benefit: "Shows what the market is paying right now so you can compare companies on equal, up-to-date footing.",
    aliases: ["LTP"],
  },
  {
    id: "change_pct",
    fullName: "Change %",
    definition: "The percentage move in share price from the previous session's close to the current last traded price.",
    benefit: "Quickly spot which stocks are gaining or losing momentum today within a sector or watchlist.",
    aliases: ["Chg %", "Change", "Daily % change"],
  },
  {
    id: "market_cap",
    fullName: "Market Capitalization",
    definition: "Total market value of a company's outstanding shares (share price × shares outstanding).",
    benefit: "Helps you compare company size, liquidity, and index weight when screening or ranking peers.",
    aliases: ["Mkt Cap", "Market Cap", "Market cap", "Total Mkt Cap", "Market cap (Bn PKR)"],
  },
  {
    id: "pe_ttm",
    fullName: "Price-to-Earnings (TTM)",
    definition: "Share price divided by earnings per share over the trailing twelve months.",
    benefit: "A lower P/E may suggest cheaper valuation relative to earnings; compare within the same sector for context.",
    aliases: ["P/E", "P/E TTM", "P/E min", "P/E max", "Median P/E"],
  },
  {
    id: "pb",
    fullName: "Price-to-Book",
    definition: "Share price divided by book value per share (net assets per share).",
    benefit: "Useful for asset-heavy sectors; a P/B below 1 can indicate the market values the company below its net assets.",
    aliases: ["P/B", "P/B min", "P/B max"],
  },
  {
    id: "eps_ttm",
    fullName: "Earnings Per Share (TTM)",
    definition: "Net profit attributable to ordinary shareholders divided by weighted average shares over the last twelve months.",
    benefit: "Tracks profit earned per share; rising EPS with stable P/E often signals improving fundamentals.",
    aliases: ["EPS", "EPS TTM", "eps basic", "eps_ttm"],
  },
  {
    id: "dividend_yield",
    fullName: "Dividend Yield",
    definition: "Annual dividends per share divided by the current share price, expressed as a percentage.",
    benefit: "Shows income potential; compare yield to sector medians and verify payout sustainability with earnings.",
    aliases: ["Div %", "Div Yield", "Div yield", "Div yield min %", "Div yield max %", "Median Div %"],
  },
  {
    id: "roe",
    fullName: "Return on Equity",
    definition: "Net income divided by shareholders' equity, showing how efficiently a company uses owner capital.",
    benefit: "Higher ROE often indicates stronger profitability; compare peers in the same industry for fair context.",
    aliases: ["ROE", "ROE min %"],
  },
  {
    id: "roa",
    fullName: "Return on Assets",
    definition: "Net income divided by total assets, measuring how well a company converts assets into profit.",
    benefit: "Useful for capital-intensive businesses where asset efficiency matters as much as leverage.",
    aliases: ["ROA", "ROA min %", "roa"],
  },
  {
    id: "debt_to_equity",
    fullName: "Debt-to-Equity Ratio",
    definition: "Total debt divided by shareholders' equity, indicating how much the company relies on borrowed funds.",
    benefit: "Lower D/E generally means less financial risk; high leverage can amplify gains but also losses.",
    aliases: ["D/E", "D/E max", "debt_to_equity"],
  },
  {
    id: "beta",
    fullName: "Beta",
    definition: "A measure of how much a stock's price tends to move relative to the broader market (often KSE-100).",
    benefit: "Beta above 1 means more volatile than the index; helps gauge portfolio risk and expected swing size.",
    aliases: ["Beta", "Beta min", "Beta max", "Portfolio beta"],
  },
  {
    id: "return_1d",
    fullName: "1-Day Return",
    definition: "Percentage price change over the last trading day.",
    benefit: "Highlights today's movers when comparing companies within a sector heatmap.",
    aliases: ["Ret 1D", "return_1d"],
  },
  {
    id: "return_1w",
    fullName: "1-Week Return",
    definition: "Percentage price change over the past five trading days (one week).",
    benefit: "Captures short-term momentum beyond a single session.",
    aliases: ["Ret 1W", "return_1w"],
  },
  {
    id: "return_1m",
    fullName: "1-Month Return",
    definition: "Percentage price change over roughly the last 20–22 trading days.",
    benefit: "A common horizon for comparing recent performance across peers and sectors.",
    aliases: ["Ret 1M", "return_1m", "1M ret", "Return 1M min %", "Return 1M max %", "Sector 1M"],
  },
  {
    id: "return_3m",
    fullName: "3-Month Return",
    definition: "Percentage price change over roughly the last three months of trading.",
    benefit: "Filters out daily noise and reveals medium-term trends when screening.",
    aliases: ["Return 3M min %", "return_3m"],
  },
  {
    id: "return_ytd",
    fullName: "Year-to-Date Return",
    definition: "Percentage price change from the start of the calendar year to today.",
    benefit: "Shows how a stock has performed in the current year relative to peers.",
    aliases: ["Ret YTD", "return_ytd", "YTD change"],
  },
  {
    id: "revenue",
    fullName: "Revenue",
    definition: "Total income from sales of goods or services before deducting expenses.",
    benefit: "Top-line growth signals demand; pair with margins to see if growth is profitable.",
    aliases: ["revenue"],
  },
  {
    id: "gross_profit",
    fullName: "Gross Profit",
    definition: "Revenue minus the direct cost of producing goods or services sold.",
    benefit: "Shows core product profitability before overhead; useful for comparing operating efficiency.",
    aliases: ["Gross Profit", "gross profit", "gross_profit"],
  },
  {
    id: "ebitda",
    fullName: "EBITDA",
    definition: "Earnings before interest, taxes, depreciation, and amortization.",
    benefit: "Approximates operating cash generation; helpful for comparing companies with different capital structures.",
    aliases: ["EBITDA", "ebitda"],
  },
  {
    id: "pat",
    fullName: "Profit After Tax",
    definition: "Net profit remaining after all expenses, interest, and taxes have been deducted.",
    benefit: "The bottom-line earnings figure that ultimately drives EPS and dividends.",
    aliases: ["PAT", "pat"],
  },
  {
    id: "total_assets",
    fullName: "Total Assets",
    definition: "Everything the company owns, including cash, inventory, property, and investments.",
    benefit: "Scale indicator for asset-heavy industries; use with ROA to judge asset productivity.",
    aliases: ["Assets", "total assets", "total_assets"],
  },
  {
    id: "total_equity",
    fullName: "Shareholders' Equity",
    definition: "Residual interest in assets after liabilities—what shareholders effectively own.",
    benefit: "The book value base for P/B; declining equity can signal losses or heavy distributions.",
    aliases: ["Equity", "total equity", "total_equity"],
  },
  {
    id: "total_debt",
    fullName: "Total Debt",
    definition: "Sum of short- and long-term borrowings owed by the company.",
    benefit: "Pair with equity and cash flow to assess whether debt levels are manageable.",
    aliases: ["Debt", "total debt", "total_debt"],
  },
  {
    id: "ocf",
    fullName: "Operating Cash Flow",
    definition: "Cash generated from core business operations before financing and investing activities.",
    benefit: "Shows whether reported profits convert to real cash—a key check on earnings quality.",
    aliases: ["OCF", "ocf"],
  },
  {
    id: "capex",
    fullName: "Capital Expenditure",
    definition: "Cash spent on long-term assets such as plants, equipment, and infrastructure.",
    benefit: "High capex may support future growth but reduces free cash available for dividends.",
    aliases: ["Capex", "capex"],
  },
  {
    id: "period_end",
    fullName: "Reporting Period",
    definition: "The end date of the financial statement period for the reported figures.",
    benefit: "Ensures you compare the same time frame when looking at revenue, profit, and balance sheet items.",
    aliases: ["Period", "period_end"],
  },
  {
    id: "gross_margin",
    fullName: "Gross Margin",
    definition: "Gross profit divided by revenue, expressed as a percentage.",
    benefit: "Higher margins often mean stronger pricing power or lower production costs versus peers.",
    aliases: ["Gross Margin", "gross_margin"],
  },
  {
    id: "ebitda_margin",
    fullName: "EBITDA Margin",
    definition: "EBITDA divided by revenue, showing operating profitability before non-cash charges.",
    benefit: "Useful for comparing operating efficiency across companies with different depreciation policies.",
    aliases: ["EBITDA Margin", "ebitda_margin"],
  },
  {
    id: "net_margin",
    fullName: "Net Margin",
    definition: "Net profit divided by revenue, expressed as a percentage.",
    benefit: "Shows how much of each rupee of sales becomes profit; compare within the same sector.",
    aliases: ["Net margin", "Net margin min %", "net_margin"],
  },
  {
    id: "current_ratio",
    fullName: "Current Ratio",
    definition: "Current assets divided by current liabilities, measuring short-term liquidity.",
    benefit: "A ratio below 1 may signal difficulty paying near-term obligations; compare to industry norms.",
    aliases: ["Current Ratio", "Current ratio min", "current_ratio"],
  },
  {
    id: "volume",
    fullName: "Trading Volume",
    definition: "Number of shares traded during the current or latest session.",
    benefit: "Higher volume confirms price moves and suggests easier entry or exit for your position.",
    aliases: ["Volume"],
  },
  {
    id: "vwap",
    fullName: "Volume-Weighted Average Price",
    definition: "Average price weighted by volume throughout the trading session.",
    benefit: "Institutional traders use VWAP as a benchmark; trading below VWAP may suggest intraday weakness.",
    aliases: ["VWAP"],
  },
  {
    id: "avg_volume_30d",
    fullName: "30-Day Average Volume",
    definition: "Average daily shares traded over the last 30 trading days.",
    benefit: "Helps judge typical liquidity; spikes above average often accompany news or breakouts.",
    aliases: ["Avg Vol 30d", "Avg volume 30d min", "avg_volume_30d"],
  },
  {
    id: "shares_outstanding",
    fullName: "Shares Outstanding",
    definition: "Total number of shares currently held by all shareholders.",
    benefit: "Used with price to calculate market cap; dilution from new issuance can affect EPS.",
    aliases: ["Shares Out", "shares_outstanding"],
  },
  {
    id: "free_float",
    fullName: "Free Float",
    definition: "Percentage of shares available for public trading, excluding closely held or locked shares.",
    benefit: "Higher free float usually means better liquidity and less price impact from large trades.",
    aliases: ["Free Float", "Free float", "Free float min %", "free_float_pct"],
  },
  {
    id: "fifty_two_week_high",
    fullName: "52-Week High",
    definition: "The highest price at which the stock traded over the past year.",
    benefit: "Stocks near 52-week highs may be in strong uptrends; breaking above can signal continuation.",
    aliases: ["52W High", "52W high", "New 52W high", "Near 52W high %"],
  },
  {
    id: "fifty_two_week_low",
    fullName: "52-Week Low",
    definition: "The lowest price at which the stock traded over the past year.",
    benefit: "Helps gauge how far a stock has recovered or fallen from its annual extremes.",
    aliases: ["52W Low", "52W low"],
  },
  {
    id: "foreign_pct",
    fullName: "Foreign Ownership",
    definition: "Percentage of shares held by foreign institutional or portfolio investors.",
    benefit: "Rising foreign ownership can signal international confidence; watch for regulatory limits.",
    aliases: ["Foreign %", "Foreign % min"],
  },
  {
    id: "pledged_shares",
    fullName: "Pledged Shares",
    definition: "Shares pledged by major shareholders as collateral for loans.",
    benefit: "High pledged shares can increase risk if promoters face margin calls or forced selling.",
    aliases: ["Pledged below %", "pledged_shares"],
  },
  {
    id: "institutional_pct",
    fullName: "Institutional Ownership",
    definition: "Percentage of shares held by institutions such as mutual funds, banks, and pension funds.",
    benefit: "Higher institutional ownership can mean more research coverage and steadier long-term holders.",
    aliases: ["Institutional %", "% Outstanding", "institutional_pct"],
  },
  {
    id: "quantity",
    fullName: "Quantity",
    definition: "Number of shares you hold in a position.",
    benefit: "Multiplied by price to get position value and by cost basis to track total invested capital.",
    aliases: ["Qty"],
  },
  {
    id: "avg_cost",
    fullName: "Average Cost",
    definition: "Your average purchase price per share across all lots in a holding.",
    benefit: "Compare to LTP to see unrealized gain or loss and decide whether to add or trim.",
    aliases: ["Avg cost", "avg_buy_price"],
  },
  {
    id: "pnl",
    fullName: "Profit & Loss",
    definition: "Unrealized gain or loss on a holding based on current price versus your average cost.",
    benefit: "Shows how each position is performing without selling; helps prioritize winners and losers.",
    aliases: ["P&L", "Unrealized P&L"],
  },
  {
    id: "weight",
    fullName: "Portfolio Weight",
    definition: "Percentage of your total portfolio value represented by a single holding.",
    benefit: "Monitor concentration risk; oversized positions amplify both gains and losses.",
    aliases: ["Weight", "weight_pct"],
  },
  {
    id: "total_value",
    fullName: "Total Portfolio Value",
    definition: "Sum of current market values of all holdings plus cash.",
    benefit: "Your portfolio's headline number for tracking growth over time.",
    aliases: ["Total value"],
  },
  {
    id: "dividend_income_ytd",
    fullName: "Year-to-Date Dividends",
    definition: "Total dividend income received from portfolio holdings so far this calendar year.",
    benefit: "Tracks passive income contribution separate from price appreciation.",
    aliases: ["YTD dividends"],
  },
  {
    id: "kse100",
    fullName: "KSE-100 Index",
    definition: "Pakistan's benchmark index of the 100 largest and most liquid companies on PSX.",
    benefit: "Use as a market benchmark to see if your stock or portfolio is beating or lagging the market.",
    aliases: ["KSE-100", "KSE100", "kse100"],
  },
  {
    id: "kse30",
    fullName: "KSE-30 Index",
    definition: "Index of 30 large-cap, liquid PSX stocks selected by free-float market capitalization.",
    benefit: "A narrower large-cap benchmark for comparing blue-chip performance.",
    aliases: ["KSE30"],
  },
  {
    id: "advances",
    fullName: "Advances",
    definition: "Number of stocks that closed higher than the previous session.",
    benefit: "Broad market breadth indicator; many advances suggest a healthy, broad-based rally.",
    aliases: ["Advances"],
  },
  {
    id: "declines",
    fullName: "Declines",
    definition: "Number of stocks that closed lower than the previous session.",
    benefit: "Rising declines with a flat index can signal weakness beneath the surface.",
    aliases: ["Declines"],
  },
  {
    id: "unchanged",
    fullName: "Unchanged",
    definition: "Number of stocks that closed at the same price as the previous session.",
    benefit: "Completes the market breadth picture alongside advances and declines.",
    aliases: ["Unchanged"],
  },
  {
    id: "sbp_rate",
    fullName: "SBP Policy Rate",
    definition: "The State Bank of Pakistan's benchmark interest rate for monetary policy.",
    benefit: "Higher rates can pressure valuations; banks and rate-sensitive sectors react strongly to changes.",
    aliases: ["SBP"],
  },
  {
    id: "pkr_usd",
    fullName: "PKR/USD Exchange Rate",
    definition: "Pakistani rupee value per US dollar.",
    benefit: "Affects exporters (benefit from weaker PKR) and importers; impacts foreign investor returns.",
    aliases: ["PKR/USD"],
  },
  {
    id: "sma20",
    fullName: "20-Day Simple Moving Average",
    definition: "Average closing price over the last 20 trading days.",
    benefit: "Short-term trend line; price above SMA20 often indicates near-term bullish momentum.",
    aliases: ["SMA20"],
  },
  {
    id: "sma50",
    fullName: "50-Day Simple Moving Average",
    definition: "Average closing price over the last 50 trading days.",
    benefit: "Medium-term trend indicator; golden crosses (SMA20 above SMA50) are watched by traders.",
    aliases: ["SMA50"],
  },
  {
    id: "vol_ma",
    fullName: "Volume Moving Average",
    definition: "Average trading volume over a rolling window, overlaid on the volume chart.",
    benefit: "Volume bars above the average confirm stronger conviction behind price moves.",
    aliases: ["Vol MA"],
  },
  {
    id: "adjusted",
    fullName: "Adjusted Prices",
    definition: "Historical prices revised for dividends, splits, and rights issues to maintain continuity.",
    benefit: "Essential for accurate long-term return and chart analysis; unadjusted prices distort history.",
    aliases: ["Adjusted"],
  },
  {
    id: "returns_tool",
    fullName: "Returns Calculator",
    definition: "Click two points on the price chart to measure percentage return between them.",
    benefit: "Quickly quantify gains or losses over any custom period without manual math.",
    aliases: ["Returns"],
  },
  {
    id: "terp",
    fullName: "Theoretical Ex-Rights Price",
    definition: "The estimated fair price after a rights issue, balancing old and new share values.",
    benefit: "Helps rights holders decide whether to subscribe, sell rights, or let them lapse.",
    aliases: ["TERP", "TERP Calculation"],
  },
  {
    id: "dps",
    fullName: "Dividend Per Share",
    definition: "Total dividends paid per share over a period, usually annualized.",
    benefit: "Track income history and payout consistency alongside dividend yield.",
    aliases: ["DPS", "DPS history (analytics)", "DPS by year"],
  },
  {
    id: "ex_date",
    fullName: "Ex-Dividend Date",
    definition: "The first day a stock trades without entitlement to the declared dividend.",
    benefit: "Buy before ex-date to receive the dividend; price often drops roughly by the dividend amount on ex-date.",
    aliases: ["Ex Date", "Next ex-dividend", "ex-dividend"],
  },
  {
    id: "top_gainer_loser",
    fullName: "Top Gainer / Loser",
    definition: "The stocks with the largest positive and negative price moves in the sector for the selected period.",
    benefit: "Quickly identifies leadership and laggards when scanning a sector heatmap.",
    aliases: ["Top gainer / loser"],
  },
  {
    id: "net_insider_buy",
    fullName: "Net Insider Buying",
    definition: "Net value of shares bought minus sold by company insiders over a period.",
    benefit: "Insider buying can signal management confidence; heavy selling may warrant caution.",
    aliases: ["Net insider buy (30d)", "Net 30d", "Net 90d"],
  },
  {
    id: "cluster_buy",
    fullName: "Cluster Buy",
    definition: "Multiple insiders purchasing shares within a short window (e.g. 14 days).",
    benefit: "Cluster buying is a stronger bullish signal than a single insider trade.",
    aliases: ["Cluster buy (14d)", "Cluster buy"],
  },
  {
    id: "aum",
    fullName: "Assets Under Management",
    definition: "Total market value of investments managed by a fund or institutional investor.",
    benefit: "Scale indicator for institutional investors; larger AUM can mean more market influence.",
    aliases: ["AUM", "Total AUM"],
  },
  {
    id: "qoq",
    fullName: "Quarter-over-Quarter Change",
    definition: "Percentage change in a metric compared to the previous quarter.",
    benefit: "Shows recent momentum in holdings or performance between quarterly filings.",
    aliases: ["QoQ"],
  },
  {
    id: "portfolio_pct",
    fullName: "% of Portfolio",
    definition: "What percentage of an investor's total portfolio a single holding represents.",
    benefit: "Reveals conviction levels and concentration in institutional portfolios.",
    aliases: ["% Portfolio"],
  },
  {
    id: "current_assets",
    fullName: "Current Assets",
    definition: "Assets expected to be converted to cash within one year, such as inventory and receivables.",
    benefit: "Used with current liabilities to assess short-term financial health.",
    aliases: ["current assets"],
  },
  {
    id: "current_liabilities",
    fullName: "Current Liabilities",
    definition: "Obligations due within one year, such as payables and short-term debt.",
    benefit: "Compare to current assets via the current ratio to gauge liquidity risk.",
    aliases: ["current liabilities"],
  },
  {
    id: "median_pe",
    fullName: "Median P/E",
    definition: "The middle P/E value across all companies in the sector, less skewed than the average.",
    benefit: "A fairer benchmark for whether a stock looks cheap or expensive versus its sector peers.",
    aliases: ["Median P/E"],
  },
  {
    id: "median_dividend_yield",
    fullName: "Median Dividend Yield",
    definition: "The middle dividend yield across companies in the sector.",
    benefit: "Compare a stock's yield to the sector median to spot unusually high or low income offerings.",
    aliases: ["Median Div %"],
  },
  {
    id: "insider_buys",
    fullName: "Insider Buys",
    definition: "Count of Form 4 filings showing insider purchases in the selected feed window.",
    benefit: "Tracks bullish insider activity clusters that may precede positive company news.",
    aliases: ["Insider buys"],
  },
  {
    id: "top5_concentration",
    fullName: "Top 5 Concentration",
    definition: "Combined portfolio weight of an investor's five largest holdings.",
    benefit: "High concentration signals conviction but also single-name risk in the portfolio.",
    aliases: ["Top 5 concentration"],
  },
];

const byId = new Map<string, MetricInfo>();
const byAlias = new Map<string, MetricInfo>();

function normalizeKey(s: string): string {
  return s
    .toLowerCase()
    .replace(/[%()]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/ /g, "_")
    .replace(/[^a-z0-9_]/g, "");
}

for (const metric of METRICS) {
  byId.set(metric.id, metric);
  byAlias.set(normalizeKey(metric.id), metric);
  for (const alias of metric.aliases ?? []) {
    byAlias.set(normalizeKey(alias), metric);
  }
}

export function getMetricInfo(id: string): MetricInfo | undefined {
  return byId.get(id) ?? byAlias.get(normalizeKey(id));
}

export function resolveMetricInfo(labelOrId: string): MetricInfo | undefined {
  const direct = getMetricInfo(labelOrId);
  if (direct) return direct;

  const normalized = normalizeKey(labelOrId);
  const fromAlias = byAlias.get(normalized);
  if (fromAlias) return fromAlias;

  // Strip common filter suffixes: "pe min" -> "pe", "div yield min" -> "div yield"
  const stripped = normalized
    .replace(/_(min|max|below)$/, "")
    .replace(/_min_%$/, "")
    .replace(/_max_%$/, "");
  return byAlias.get(stripped);
}

export function getMetricLabel(id: string): string {
  const info = getMetricInfo(id);
  if (!info) return id;
  const alias = info.aliases?.[0];
  if (alias) return alias;
  return info.fullName;
}

export const METRIC_GLOSSARY = METRICS;
