export interface TickerListItem {
  symbol: string;
  name: string;
  sector: string;
  board: string;
  ltp?: number | null;
  change_pct?: number | null;
}

export interface TickerListResponse {
  items: TickerListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SnapshotResponse {
  symbol: string;
  name: string;
  sector: string;
  board: string;
  ltp: number;
  change: number;
  change_pct: number;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  volume?: number | null;
  market_cap?: number | null;
  fifty_two_week_high?: number | null;
  fifty_two_week_low?: number | null;
  avg_volume_30d?: number | null;
  shares_outstanding?: number | null;
  prev_close?: number | null;
  updated_at?: string | null;
  pe_ttm?: number | null;
  eps_ttm?: number | null;
  dividend_yield?: number | null;
  free_float_pct?: number | null;
  beta?: number | null;
  sector_return_1m?: number | null;
  next_dividend_ex_date?: string | null;
  vwap?: number | null;
  circuit_breaker?: boolean;
  trading_halt?: boolean;
  board_change_30d?: boolean;
}

export interface PriceBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorPoint {
  time: string;
  value: number;
}

export interface PriceSeriesResponse {
  symbol: string;
  bars: PriceBar[];
  overlay_bars?: PriceBar[] | null;
  indicator_series?: Record<string, IndicatorPoint[]> | null;
  volume_ma?: IndicatorPoint[] | null;
}

export interface ChartMarker {
  time: string;
  label: string;
  kind: "dividend" | "event" | "macro";
  significance?: number;
}

export interface ChartMarkersResponse {
  symbol: string;
  markers: ChartMarker[];
  delisting_detected: boolean;
  delisting_title?: string | null;
}

export interface MoverItem {
  symbol: string;
  name: string;
  sector: string;
  ltp: number;
  change_pct: number;
  volume: number;
}

export interface MarketSummaryResponse {
  index_symbol: string;
  index_level?: number | null;
  index_change_pct?: number | null;
  advances: number;
  declines: number;
  unchanged: number;
  top_gainers: MoverItem[];
  top_losers: MoverItem[];
  market_open: boolean;
}

export interface WsPriceTick {
  symbol: string;
  ltp: number;
  change_pct: number;
  ts: string;
}

export interface AnnouncementItem {
  id: number;
  symbol: string;
  published_at: string;
  title: string;
  category: string;
  pdf_url?: string | null;
  source_url?: string | null;
}

export interface AnnouncementListResponse {
  items: AnnouncementItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface FinancialPeriodColumn {
  period_id: number;
  period_end: string;
  fiscal_year: number;
  fiscal_quarter?: number | null;
  parser_confidence?: number | null;
  is_verified: boolean;
  source_pdf_url?: string | null;
}

export interface FinancialLineRow {
  line_code: string;
  unit: string;
  values: Record<string, number>;
  yoy_change_pct?: Record<string, number | null>;
}

export interface FinancialsResponse {
  symbol: string;
  period_type: string;
  periods: FinancialPeriodColumn[];
  rows: FinancialLineRow[];
  low_confidence: boolean;
  validation_flags?: string[];
}

export interface RatioValue {
  code: string;
  value?: number | null;
}

export interface RatiosResponse {
  symbol: string;
  sector: string;
  latest: RatioValue[];
  history: { period_end: string; ratios: Record<string, number | null> }[];
  sector_medians: Record<string, number>;
}

export interface InsiderTradeItem {
  id: number;
  director_name: string;
  designation?: string | null;
  transaction_date: string;
  transaction_type: string;
  shares: number;
  price_per_share?: number | null;
  post_holding_shares?: number | null;
}

export interface InsiderTradesResponse {
  symbol: string;
  trades: InsiderTradeItem[];
  net_30d: number;
  net_90d: number;
  cluster_buy_14d?: boolean;
}

export interface OwnershipSnapshotItem {
  holder_category: string;
  shares: number;
  pct_outstanding: number;
  pledged_shares_pct?: number | null;
  holder_name?: string | null;
}

export interface OwnershipResponse {
  symbol: string;
  latest_snapshot: OwnershipSnapshotItem[];
  history: { as_of_date: string; snapshots: OwnershipSnapshotItem[] }[];
  pledged_shares_pct?: number | null;
  pledged_warning?: boolean;
  named_holders?: OwnershipSnapshotItem[];
  free_float_pct?: number | null;
}

export interface BoardMemberItem {
  name: string;
  role: string;
  appointment_date?: string | null;
  resignation_date?: string | null;
}

export interface SecpFilingItem {
  form_type: string;
  filed_at: string;
  raw_url?: string | null;
}

export interface GovernanceResponse {
  symbol: string;
  board: BoardMemberItem[];
  director_changes: BoardMemberItem[];
  board_change_30d: boolean;
  filings: SecpFilingItem[];
  ccg_checklist: { item: string; filed: boolean }[];
}

export interface CreditRatingItem {
  agency: string;
  rating: string;
  outlook?: string | null;
  effective_date: string;
  source_url?: string | null;
}

export interface CreditRatingsResponse {
  symbol: string;
  ratings: CreditRatingItem[];
}

export interface OverviewNewsItem {
  id: number;
  headline: string;
  source: string;
  published_at: string;
}

export interface OverviewResponse {
  symbol: string;
  ai_summary?: AiSummaryResponse | null;
  key_ratios: RatioValue[];
  next_dividend_ex_date?: string | null;
  upcoming_actions: Record<string, unknown>[];
  recent_announcements: AnnouncementItem[];
  recent_news: OverviewNewsItem[];
  board_change_30d: boolean;
  delisting_detected: boolean;
  delisting_title?: string | null;
}

export interface MacroPoint {
  time: string;
  value: number;
  unit?: string | null;
}

export interface MacroSeriesResponse {
  series_code: string;
  points: MacroPoint[];
}

export interface CorporateCalendarItem {
  symbol: string;
  action_type: string;
  announced_at: string;
  ex_date?: string | null;
  record_date?: string | null;
  amount_per_share?: number | null;
  ratio?: string | null;
}

export interface CorporateCalendarResponse {
  items: CorporateCalendarItem[];
}

export interface DpsDataPoint {
  year: number;
  ex_date: string;
  dps: number;
  payout_ratio?: number | null;
}

export interface TerpCalculation {
  rights_ratio: string;
  market_price: number;
  rights_price: number;
  terp: number;
}

export interface CorpActionAnalyticsResponse {
  symbol: string;
  dps_series: DpsDataPoint[];
  terp?: TerpCalculation | null;
}

export interface NewsVolumePoint {
  date: string;
  count: number;
}

export interface NewsVolumeResponse {
  symbol: string;
  days: number;
  points: NewsVolumePoint[];
}

export interface NewsKeywordsResponse {
  symbol: string;
  keywords: { word: string; weight: number }[];
}

export interface SocialPostItem {
  id: number;
  source: string;
  author_handle?: string | null;
  posted_at: string;
  text: string;
  url?: string | null;
  engagement_json?: Record<string, unknown> | null;
  link_confidence?: number | null;
}

export interface SocialFeedResponse {
  symbol: string;
  items: SocialPostItem[];
  total: number;
}

export interface NewsItem {
  id: number;
  source: string;
  headline: string;
  published_at: string;
  author?: string | null;
  source_url: string;
  excerpt?: string | null;
  topic_tag?: string | null;
  link_confidence?: number | null;
  ai_summary?: string | null;
  sentiment_badge?: string | null;
}

export interface NewsListResponse {
  items: NewsItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface CorporateActionItem {
  id: number;
  symbol: string;
  action_type: string;
  announced_at: string;
  ex_date?: string | null;
  record_date?: string | null;
  payment_date?: string | null;
  amount_per_share?: number | null;
  ratio?: string | null;
  currency: string;
  source_announcement_id?: number | null;
}

export interface CorporateActionListResponse {
  items: CorporateActionItem[];
}

export interface MaterialEventItem {
  id: number;
  symbol: string;
  event_type: string;
  headline: string;
  event_date: string;
  counterparty?: string | null;
  amount_pkr?: number | null;
  significance_score: number;
  summary?: string | null;
  source_announcement_id?: number | null;
}

export interface MaterialEventListResponse {
  items: MaterialEventItem[];
}

export interface SectorStatsItem {
  sector: string;
  company_count: number;
  total_market_cap?: number | null;
  median_pe?: number | null;
  median_dividend_yield?: number | null;
  return_1d?: number | null;
  return_1w?: number | null;
  return_1m?: number | null;
  return_ytd?: number | null;
  top_gainer_symbol?: string | null;
  top_loser_symbol?: string | null;
}

export interface SectorStatsResponse {
  trade_date?: string | null;
  range: string;
  sectors: SectorStatsItem[];
}

export interface SectorCompanyFinancials {
  revenue?: number | null;
  gross_profit?: number | null;
  ebitda?: number | null;
  pat?: number | null;
  total_assets?: number | null;
  total_equity?: number | null;
  total_debt?: number | null;
  ocf?: number | null;
  capex?: number | null;
  period_end?: string | null;
}

export interface SectorCompanyRow {
  symbol: string;
  name: string;
  ltp?: number | null;
  change_pct?: number | null;
  market_cap?: number | null;
  volume?: number | null;
  avg_volume_30d?: number | null;
  pe_ttm?: number | null;
  eps_ttm?: number | null;
  dividend_yield?: number | null;
  roe?: number | null;
  roa?: number | null;
  gross_margin?: number | null;
  ebitda_margin?: number | null;
  net_margin?: number | null;
  debt_to_equity?: number | null;
  current_ratio?: number | null;
  beta?: number | null;
  return_range?: number | null;
  financials: SectorCompanyFinancials;
}

export interface SectorDetailResponse {
  sector: string;
  range: string;
  trade_date?: string | null;
  stats?: SectorStatsItem | null;
  companies: SectorCompanyRow[];
}

export interface SentimentDataPoint {
  time: string;
  source: string;
  score: number;
  positive_pct?: number | null;
  negative_pct?: number | null;
  neutral_pct?: number | null;
  post_count: number;
}

export interface SentimentSeriesResponse {
  symbol: string;
  days: number;
  aggregate: SentimentDataPoint[];
  by_source: Record<string, SentimentDataPoint[]>;
  momentum_3d?: number | null;
  current_score?: number | null;
}

export interface AiSummaryResponse {
  symbol?: string | null;
  summary_type: string;
  content: string;
  generated_at: string;
  model: string;
}

export interface WatchlistItemSnapshot {
  symbol: string;
  name?: string | null;
  ltp?: number | null;
  change_pct?: number | null;
  added_at: string;
}

export interface WatchlistResponse {
  items: WatchlistItemSnapshot[];
  limit?: number | null;
  count: number;
}

export interface PortalSessionResponse {
  portal_url: string;
}

export interface CheckoutSessionResponse {
  checkout_url: string;
}

// Phase 5 — Screener
export interface ScreenerFilters {
  sectors?: string[] | null;
  boards?: string[] | null;
  index_membership?: string[] | null;
  market_cap_min_bn?: number | null;
  market_cap_max_bn?: number | null;
  pe_min?: number | null;
  pe_max?: number | null;
  pb_min?: number | null;
  pb_max?: number | null;
  dividend_yield_min?: number | null;
  dividend_yield_max?: number | null;
  roe_min?: number | null;
  roa_min?: number | null;
  net_margin_min?: number | null;
  debt_to_equity_max?: number | null;
  current_ratio_min?: number | null;
  return_1m_min?: number | null;
  return_1m_max?: number | null;
  return_3m_min?: number | null;
  return_3m_max?: number | null;
  beta_min?: number | null;
  beta_max?: number | null;
  avg_volume_30d_min?: number | null;
  near_52w_high_pct?: number | null;
  net_insider_buy_30d?: boolean | null;
  pledged_shares_below_pct?: number | null;
  free_float_min?: number | null;
  foreign_pct_min?: number | null;
  sentiment_score_min?: number | null;
  sentiment_momentum_positive?: boolean | null;
}

export interface ScreenerResultRow {
  symbol: string;
  name: string;
  sector: string;
  ltp?: number | null;
  change_pct?: number | null;
  market_cap?: number | null;
  pe_ttm?: number | null;
  roe?: number | null;
  debt_to_equity?: number | null;
  dividend_yield?: number | null;
  avg_volume_30d?: number | null;
  beta?: number | null;
}

export interface ScreenerResponse {
  items: ScreenerResultRow[];
  total: number;
  page: number;
  page_size: number;
  filter_groups_active: number;
  filter_groups_limit?: number | null;
}

export interface ScreenerPresetItem {
  id: number;
  name: string;
  filters: ScreenerFilters;
  created_at?: string;
  updated_at?: string;
}

export interface ScreenerPresetListResponse {
  items: ScreenerPresetItem[];
  limit: number;
  count: number;
}

// Notification preferences
export interface NotificationPrefsResponse {
  email_enabled: boolean;
  push_enabled: boolean;
  whatsapp_enabled: boolean;
  digest_enabled: boolean;
  whatsapp_number?: string | null;
}

// API keys (Pro)
export interface ApiKeyItem {
  id: number;
  key_prefix: string;
  label: string;
  last_used_at?: string | null;
  created_at: string;
}

export interface ApiKeyCreateResponse extends ApiKeyItem {
  key: string;
}

export interface ApiKeyListResponse {
  items: ApiKeyItem[];
}

// Admin
export interface FailedTaskItem {
  id: number;
  task_id: string;
  task_name: string;
  error_message?: string | null;
  failed_at: string;
  retried: boolean;
}

export interface FailedTaskListResponse {
  items: FailedTaskItem[];
}

export interface DataQualityReport {
  stale_scrapers: string[];
  stale_index_symbols: string[];
  tickers_missing_financials: number;
  total_tickers: number;
  scraper_health?: Record<string, unknown> | null;
}

// Phase 5 — Portfolio
export interface HoldingItem {
  id: number;
  symbol: string;
  name?: string | null;
  sector?: string | null;
  quantity: number;
  avg_buy_price: number;
  purchase_date: string;
  ltp?: number | null;
  current_value?: number | null;
  cost_basis?: number | null;
  unrealized_pnl?: number | null;
  unrealized_pnl_pct?: number | null;
  weight_pct?: number | null;
}

export interface PortfolioSummary {
  total_value: number;
  total_cost: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  dividend_income_ytd: number;
  portfolio_beta?: number | null;
  concentration_warning: boolean;
  sector_exposure: { sector: string; weight_pct: number; concentrated: boolean }[];
  vs_kse100: { date: string; portfolio: number; kse100?: number | null }[];
}

export interface PortfolioResponse {
  holdings: HoldingItem[];
  summary: PortfolioSummary;
}

// Phase 5 — Compare & Peers
export interface CompareResponse {
  symbols: string[];
  series: { symbol: string; name: string; sector?: string | null; points: { date: string; value: number }[] }[];
  ratios: { ratio_code: string; values: Record<string, number | null> }[];
}

export interface PeersResponse {
  symbol: string;
  sector: string;
  peers: {
    symbol: string;
    name: string;
    pe_ttm?: number | null;
    roe?: number | null;
    debt_to_equity?: number | null;
    dividend_yield?: number | null;
    return_1m?: number | null;
  }[];
  sector_median: {
    symbol: string;
    name: string;
    pe_ttm?: number | null;
    roe?: number | null;
    debt_to_equity?: number | null;
    dividend_yield?: number | null;
    return_1m?: number | null;
  };
}

// Phase 5 — Alerts & Notifications
export interface AlertItem {
  id: number;
  symbol?: string | null;
  alert_type: string;
  params_json: Record<string, unknown>;
  is_active: boolean;
  one_shot: boolean;
}

export interface NotificationItem {
  id: number;
  title: string;
  body: string;
  link_url?: string | null;
  read_at?: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  unread_count: number;
}
