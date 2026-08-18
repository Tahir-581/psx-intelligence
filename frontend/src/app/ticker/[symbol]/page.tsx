"use client";

import { useQuery } from "@tanstack/react-query";
import { use, useCallback, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { SkeletonCard } from "@/components/movers-table";
import { PriceChart, type PriceChartConfig } from "@/components/price-chart";
import { SnapshotCard, useLiveSnapshot } from "@/components/snapshot-card";
import { AnnouncementsTab } from "@/components/ticker/announcements-tab";
import { CorporateActionsPanel } from "@/components/ticker/corporate-actions-panel";
import { EventsTimeline } from "@/components/ticker/events-timeline";
import { FinancialsTab } from "@/components/ticker/financials-tab";
import { GovernanceTab } from "@/components/ticker/governance-tab";
import { InsiderTradesTab } from "@/components/ticker/insider-trades-tab";
import { AiSummaryCard } from "@/components/ticker/ai-summary-card";
import { SentimentTab } from "@/components/ticker/sentiment-tab";
import { NewsTab } from "@/components/ticker/news-tab";
import { OwnershipTab } from "@/components/ticker/ownership-tab";
import { PeersTab } from "@/components/ticker/peers-tab";
import { SocialTab } from "@/components/ticker/social-tab";
import { apiGet } from "@/lib/api";
import type {
  ChartMarkersResponse,
  OverviewResponse,
  PriceSeriesResponse,
  SnapshotResponse,
} from "@/lib/types";
import { formatNumber } from "@/lib/utils";

type TabId =
  | "overview"
  | "chart"
  | "financials"
  | "announcements"
  | "insider trades"
  | "ownership"
  | "news"
  | "sentiment"
  | "peers"
  | "governance"
  | "corporate actions"
  | "social";

const TABS: { id: TabId; label: string; notifyKey?: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "chart", label: "Chart" },
  { id: "financials", label: "Financials" },
  { id: "announcements", label: "Announcements", notifyKey: "announcements" },
  { id: "insider trades", label: "Insider Trades", notifyKey: "insider" },
  { id: "ownership", label: "Ownership" },
  { id: "news", label: "News", notifyKey: "news" },
  { id: "sentiment", label: "Sentiment" },
  { id: "peers", label: "Peers" },
  { id: "governance", label: "Governance", notifyKey: "governance" },
  { id: "corporate actions", label: "Corp Actions", notifyKey: "corp_actions" },
  { id: "social", label: "Social", notifyKey: "social" },
];

const DEFAULT_CHART_CONFIG: PriceChartConfig = {
  chartType: "candle",
  adjusted: true,
  indexOverlay: null,
  overlays: [],
  showVolumeMa: false,
};

function buildPricesUrl(symbol: string, config: PriceChartConfig, sector?: string) {
  const params = new URLSearchParams();
  if (config.adjusted) params.set("adjusted", "true");
  if (config.overlays.length) params.set("overlays", config.overlays.join(","));
  if (config.indexOverlay === "KSE100") params.set("overlay", "KSE100");
  if (config.indexOverlay === "SECTOR" && sector) params.set("overlay", "SECTOR");
  const qs = params.toString();
  return `/ticker/${symbol}/prices${qs ? `?${qs}` : ""}`;
}

function tabDotKey(symbol: string, key: string) {
  return `psx:tab-seen:${symbol}:${key}`;
}

function useTabNotifications(symbol: string, overview?: OverviewResponse) {
  const [dots, setDots] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const next: Record<string, boolean> = {};
    if (overview?.board_change_30d) {
      const seen = localStorage.getItem(tabDotKey(symbol, "governance"));
      if (!seen) next.governance = true;
    }
    if (overview?.recent_announcements?.length) {
      const latest = overview.recent_announcements[0]?.published_at;
      const seen = localStorage.getItem(tabDotKey(symbol, "announcements"));
      if (latest && seen !== latest) next.announcements = true;
    }
    if (overview?.recent_news?.length) {
      const latest = overview.recent_news[0]?.published_at;
      const seen = localStorage.getItem(tabDotKey(symbol, "news"));
      if (latest && seen !== latest) next.news = true;
    }
    setDots(next);
  }, [symbol, overview]);

  const markSeen = useCallback(
    (tab: TabId, overviewData?: OverviewResponse) => {
      const tabDef = TABS.find((t) => t.id === tab);
      if (!tabDef?.notifyKey) return;
      const key = tabDef.notifyKey;
      let stamp = new Date().toISOString();
      if (key === "announcements" && overviewData?.recent_announcements?.[0]) {
        stamp = overviewData.recent_announcements[0].published_at;
      }
      if (key === "news" && overviewData?.recent_news?.[0]) {
        stamp = overviewData.recent_news[0].published_at;
      }
      if (key === "governance") stamp = "seen";
      localStorage.setItem(tabDotKey(symbol, key), stamp);
      setDots((d) => ({ ...d, [key]: false }));
    },
    [symbol],
  );

  return { dots, markSeen };
}

function TickerContent({
  symbol,
  snapshot,
}: {
  symbol: string;
  snapshot: SnapshotResponse;
}) {
  const [range, setRange] = useState<"1W" | "1M" | "3M" | "6M" | "1Y" | "3Y" | "5Y" | "Max">("1Y");
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [chartConfig, setChartConfig] = useState<PriceChartConfig>(DEFAULT_CHART_CONFIG);
  const liveSnapshot = useLiveSnapshot(symbol, snapshot);

  const { data: overview } = useQuery({
    queryKey: ["overview", symbol],
    queryFn: () => apiGet<OverviewResponse>(`/ticker/${symbol}/overview`),
  });

  const { dots, markSeen } = useTabNotifications(symbol, overview);

  const { data: prices } = useQuery({
    queryKey: ["prices", symbol, chartConfig, snapshot.sector],
    queryFn: () =>
      apiGet<PriceSeriesResponse>(buildPricesUrl(symbol, chartConfig, snapshot.sector)),
  });

  const { data: chartMarkersData } = useQuery({
    queryKey: ["chart-markers", symbol],
    queryFn: () => apiGet<ChartMarkersResponse>(`/ticker/${symbol}/chart-markers`),
  });

  const markers = useMemo(() => chartMarkersData?.markers ?? [], [chartMarkersData]);

  const delisting = overview?.delisting_detected || chartMarkersData?.delisting_detected;
  const delistingTitle = overview?.delisting_title ?? chartMarkersData?.delisting_title;

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    markSeen(tab, overview);
  };

  return (
    <div className="space-y-6">
      {delisting && (
        <div className="rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">
          <span className="font-semibold">Delisting notice: </span>
          {delistingTitle ?? "This symbol may be subject to delisting proceedings."}
        </div>
      )}

      <SnapshotCard snapshot={liveSnapshot} />

      <div className="flex flex-wrap gap-2 border-b border-zinc-200 dark:border-zinc-800">
        {TABS.map((tab) => {
          const hasDot = tab.notifyKey ? dots[tab.notifyKey] : false;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => handleTabChange(tab.id)}
              className={`relative px-4 py-2 text-sm ${
                activeTab === tab.id
                  ? "border-b-2 border-zinc-900 font-medium dark:border-zinc-100"
                  : "text-zinc-500"
              }`}
            >
              {tab.label}
              {hasDot && (
                <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-sky-500" />
              )}
            </button>
          );
        })}
      </div>

      {activeTab === "overview" && (
        <div className="space-y-6">
          <AiSummaryCard symbol={symbol} />

          {overview?.key_ratios?.length ? (
            <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
              <h2 className="mb-4 text-lg font-semibold">Key Ratios</h2>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {overview.key_ratios.map((r) => (
                  <div key={r.code} className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
                    <div className="text-xs text-zinc-500">{r.code.replace(/_/g, " ")}</div>
                    <div className="text-lg font-semibold tabular-nums">
                      {r.value != null ? formatNumber(r.value) : "—"}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
            <h2 className="mb-4 text-lg font-semibold">Price Chart</h2>
            {prices?.bars?.length ? (
              <PriceChart
                bars={prices.bars}
                range={range}
                onRangeChange={setRange}
                sector={snapshot.sector}
                overlayBars={prices.overlay_bars}
                indicatorSeries={prices.indicator_series}
                volumeMa={prices.volume_ma}
                markers={markers}
                onConfigChange={setChartConfig}
              />
            ) : (
              <p className="text-sm text-zinc-500">No price history yet.</p>
            )}
          </section>

          {overview?.upcoming_actions?.length ? (
            <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
              <h2 className="mb-4 text-lg font-semibold">Upcoming Corporate Actions</h2>
              <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {overview.upcoming_actions.map((action, i) => (
                  <li key={i} className="py-2 text-sm capitalize">
                    {(action.action_type as string)?.replace(/_/g, " ") ?? "Action"}
                    {action.ex_date ? ` — ex ${String(action.ex_date)}` : ""}
                    {action.amount_per_share != null ? ` · Rs ${action.amount_per_share}/sh` : ""}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {overview?.recent_announcements?.length ? (
            <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
              <h2 className="mb-4 text-lg font-semibold">Recent Announcements</h2>
              <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {overview.recent_announcements.slice(0, 5).map((a) => (
                  <li key={a.id} className="py-2 text-sm">
                    <span className="text-zinc-500">
                      {new Date(a.published_at).toLocaleDateString("en-PK")} ·{" "}
                    </span>
                    {a.title}
                    {a.pdf_url && (
                      <a
                        href={a.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-2 text-xs text-sky-600 hover:underline dark:text-sky-400"
                      >
                        PDF
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {overview?.recent_news?.length ? (
            <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
              <h2 className="mb-4 text-lg font-semibold">Recent News</h2>
              <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {overview.recent_news.slice(0, 5).map((n) => (
                  <li key={n.id} className="py-2 text-sm">
                    <span className="text-zinc-500">{n.source} · </span>
                    {n.headline}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <CorporateActionsPanel symbol={symbol} />
          <EventsTimeline symbol={symbol} />
        </div>
      )}

      {activeTab === "chart" && (
        <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
          <h2 className="mb-4 text-lg font-semibold">Price Chart</h2>
          {prices?.bars?.length ? (
            <PriceChart
              bars={prices.bars}
              range={range}
              onRangeChange={setRange}
              sector={snapshot.sector}
              overlayBars={prices.overlay_bars}
              indicatorSeries={prices.indicator_series}
              volumeMa={prices.volume_ma}
              markers={markers}
              onConfigChange={setChartConfig}
            />
          ) : (
            <p className="text-sm text-zinc-500">No price history yet.</p>
          )}
        </section>
      )}

      {activeTab === "financials" && <FinancialsTab symbol={symbol} />}
      {activeTab === "announcements" && <AnnouncementsTab symbol={symbol} />}
      {activeTab === "insider trades" && <InsiderTradesTab symbol={symbol} />}
      {activeTab === "ownership" && <OwnershipTab symbol={symbol} />}
      {activeTab === "news" && <NewsTab symbol={symbol} />}
      {activeTab === "sentiment" && <SentimentTab symbol={symbol} />}
      {activeTab === "peers" && <PeersTab symbol={symbol} />}
      {activeTab === "governance" && <GovernanceTab symbol={symbol} />}
      {activeTab === "corporate actions" && <CorporateActionsPanel symbol={symbol} fullTab />}
      {activeTab === "social" && <SocialTab symbol={symbol} />}
    </div>
  );
}

export default function TickerPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = use(params);
  const upper = symbol.toUpperCase();

  const { data: snapshot, isLoading, error } = useQuery({
    queryKey: ["snapshot", upper],
    queryFn: () => apiGet<SnapshotResponse>(`/ticker/${upper}/snapshot`),
  });

  return (
    <AppShell>
      {isLoading && <SkeletonCard />}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">
          Ticker not found or API unavailable.
        </div>
      )}
      {snapshot && <TickerContent symbol={upper} snapshot={snapshot} />}
    </AppShell>
  );
}
