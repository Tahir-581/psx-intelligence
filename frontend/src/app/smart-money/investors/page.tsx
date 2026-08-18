"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { FilterChips } from "@/components/smart-money/filter-chips";
import { InvestorAvatar } from "@/components/smart-money/investor-avatar";
import { MetricCard } from "@/components/smart-money/metric-card";
import { apiGet } from "@/lib/api";
import type { InvestorsResponse } from "@/lib/smart-money-types";
import {
  formatCurrency,
  formatPct,
  formatShortDate,
  getInvestorTypeLabel,
} from "@/lib/smart-money-utils";

const TYPE_FILTERS = [
  { label: "All", value: "all" },
  { label: "Hedge funds", value: "hedge_fund" },
  { label: "PE / Activist", value: "pe_activist" },
  { label: "Individuals", value: "individual" },
  { label: "Mutual funds", value: "mutual_fund" },
];

const PAGE_SIZE = 50;

export default function SmartMoneyInvestorsPage() {
  const [typeFilter, setTypeFilter] = useState("all");
  const [searchInput, setSearchInput] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQ(searchInput.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const queryKey = useMemo(
    () => ["smart-money", "investors", typeFilter, debouncedQ, page],
    [typeFilter, debouncedQ, page],
  );

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () => {
      const params = new URLSearchParams({
        type: typeFilter,
        page: String(page + 1),
        limit: String(PAGE_SIZE),
        sort: "aum",
      });
      if (debouncedQ) params.set("q", debouncedQ);
      return apiGet<InvestorsResponse>(`/smart-money/investors?${params}`);
    },
  });

  const investors = data?.investors ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const handleTypeChange = useCallback((value: string) => {
    setTypeFilter(value);
    setPage(0);
  }, []);

  return (
    <div>
      <div className="mb-5 grid grid-cols-2 gap-2.5 md:grid-cols-4">
        <MetricCard label="Tracked investors" value={total.toLocaleString()} />
        <MetricCard label="Total AUM" metricId="aum" value={formatCurrency(data?.totalAum ?? 0)} />
        <MetricCard label="On this page" value={String(investors.length)} />
        <MetricCard label="Page" value={`${page + 1} / ${totalPages}`} />
      </div>

      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-sm font-medium">13F filers directory</h2>
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by name…"
          className="w-full max-w-xs rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs dark:border-zinc-700 dark:bg-zinc-900"
        />
      </div>

      <FilterChips options={TYPE_FILTERS} selected={typeFilter} onChange={handleTypeChange} />

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-800" />
          ))}
        </div>
      ) : investors.length === 0 ? (
        <p className="py-8 text-center text-sm text-zinc-500">No investors match this filter.</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {investors.map((investor) => (
            <Link
              key={investor.cik}
              href={`/smart-money/investor/${investor.cik}`}
              className="block rounded-xl border border-zinc-200 bg-white p-4 transition-colors hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900"
            >
              <div className="mb-3 flex items-center gap-2">
                <InvestorAvatar initials={investor.avatarInitials} color={investor.avatarColor} size="md" />
                <span className="text-sm font-medium">{investor.name}</span>
                <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-600 dark:bg-zinc-800">
                  {getInvestorTypeLabel(investor.type)}
                </span>
              </div>
              <div className="mb-3 grid grid-cols-3 gap-2 text-xs">
                <div>
                  <div className="text-[11px] text-zinc-500"><MetricTooltip metricId="aum">AUM</MetricTooltip></div>
                  <div className="font-medium">{formatCurrency(investor.aum)}</div>
                </div>
                <div>
                  <div className="text-[11px] text-zinc-500">Holdings</div>
                  <div className="font-medium">{investor.holdingsCount.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-[11px] text-zinc-500"><MetricTooltip metricId="return_ytd">YTD change</MetricTooltip></div>
                  <div className={investor.ytdChange >= 0 ? "text-emerald-600" : "text-rose-600"}>
                    {formatPct(investor.ytdChange, true)}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap justify-between gap-2 text-[11px] text-zinc-500">
                <span>
                  Top: {investor.topTicker} {formatPct(investor.topPct)}
                </span>
                <span>Filed {formatShortDate(investor.lastFilingDate)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {totalPages > 1 ? (
        <div className="mt-4 flex items-center justify-center gap-2">
          <button
            type="button"
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            className="rounded-lg border px-3 py-1.5 text-xs disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-xs text-zinc-500">
            Page {page + 1} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            className="rounded-lg border px-3 py-1.5 text-xs disabled:opacity-40"
          >
            Next
          </button>
        </div>
      ) : null}
    </div>
  );
}
