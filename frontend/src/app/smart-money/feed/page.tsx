"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { FilingFeedItem } from "@/components/smart-money/filing-feed-item";
import { FilterChips } from "@/components/smart-money/filter-chips";
import { MetricCard } from "@/components/smart-money/metric-card";
import { apiGet } from "@/lib/api";
import type { FilingsResponse, SecFiling } from "@/lib/smart-money-types";
import { formatCurrency } from "@/lib/smart-money-utils";

const FEED_FILTERS = [
  { label: "All Forms", value: "all" },
  { label: "13F", value: "13F" },
  { label: "Form 4", value: "4" },
  { label: "13D/G", value: "13DG" },
  { label: "Hedge Funds", value: "hedge_fund" },
  { label: "PE", value: "pe" },
  { label: "Insiders", value: "insiders" },
];

function filterFilings(filings: SecFiling[], filter: string): SecFiling[] {
  switch (filter) {
    case "13F":
      return filings.filter((f) => f.formType === "13F");
    case "4":
      return filings.filter((f) => f.formType === "4");
    case "13DG":
      return filings.filter((f) => f.formType === "13D" || f.formType === "13G");
    case "hedge_fund":
      return filings.filter((f) => f.investorType === "hedge_fund");
    case "pe":
      return filings.filter((f) => f.investorType === "pe_activist");
    case "insiders":
      return filings.filter((f) => f.investorType === "individual");
    default:
      return filings;
  }
}

export default function SmartMoneyFeedPage() {
  const [filter, setFilter] = useState("all");
  const seenIdsRef = useRef<Set<string>>(new Set());
  const [newIds, setNewIds] = useState<Set<string>>(new Set());

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["smart-money", "filings"],
    queryFn: () => apiGet<FilingsResponse>("/smart-money/filings"),
    refetchInterval: 60_000,
  });

  const filings = useMemo(() => data?.filings ?? [], [data?.filings]);
  const filtered = useMemo(() => filterFilings(filings, filter), [filings, filter]);

  useEffect(() => {
    const next = new Set<string>();
    for (const f of filings) {
      if (!seenIdsRef.current.has(f.id)) next.add(f.id);
      seenIdsRef.current.add(f.id);
    }
    if (next.size) setNewIds(next);
  }, [filings]);

  const metrics = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    const last24h = filings.filter((f) => f.filedAt.slice(0, 10) === today);
    return {
      filingsToday: last24h.length || filings.length,
      totalValue: filings.reduce((s, f) => s + Math.abs(f.amount ?? f.aum ?? 0), 0),
      insiderBuys: filings.filter((f) => f.formType === "4" && f.action === "buy").length,
      tickerCount: new Set(filings.filter((f) => f.ticker).map((f) => f.ticker)).size,
    };
  }, [filings]);

  return (
    <div>
      <div className="mb-5 grid grid-cols-2 gap-2.5 md:grid-cols-4">
        <MetricCard label="Filings today" value={String(metrics.filingsToday)} />
        <MetricCard label="Total value" metricId="total_value" value={formatCurrency(metrics.totalValue)} />
        <MetricCard label="Insider buys" metricId="insider_buys" value={String(metrics.insiderBuys)} />
        <MetricCard label="Tickers" value={String(metrics.tickerCount)} />
      </div>

      <FilterChips options={FEED_FILTERS} selected={filter} onChange={setFilter} />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-800" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((filing) => (
            <FilingFeedItem key={filing.id} filing={filing} isNew={newIds.has(filing.id)} />
          ))}
          {filtered.length === 0 ? (
            <p className="py-8 text-center text-sm text-zinc-500">No filings match this filter.</p>
          ) : null}
        </div>
      )}

      <button
        type="button"
        onClick={() => refetch()}
        className="mt-4 text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
      >
        Refresh feed
      </button>
    </div>
  );
}
