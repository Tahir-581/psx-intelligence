"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use, useMemo, useState } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { InvestorAvatar } from "@/components/smart-money/investor-avatar";
import { MetricCard } from "@/components/smart-money/metric-card";
import { TickerPill } from "@/components/smart-money/ticker-pill";
import { apiGet } from "@/lib/api";
import type { HoldingsResponse, SecInvestorProfile } from "@/lib/smart-money-types";
import {
  formatCurrency,
  formatPct,
  formatShares,
  formatShortDate,
  getInvestorTypeLabel,
} from "@/lib/smart-money-utils";

type Tab = "holdings" | "changes";

export default function InvestorProfilePage({
  params,
}: {
  params: Promise<{ cik: string }>;
}) {
  const { cik } = use(params);
  const [tab, setTab] = useState<Tab>("holdings");
  const [period, setPeriod] = useState<string | undefined>();
  const [page, setPage] = useState(0);

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["smart-money", "investor", cik],
    queryFn: () => apiGet<SecInvestorProfile>(`/smart-money/investor/${cik}`),
  });

  const holdingsQuery = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page + 1),
      limit: "50",
      sort: "value",
      order: "desc",
    });
    if (period) params.set("period", period);
    if (tab === "changes") params.set("changes", "true");
    return params.toString();
  }, [cik, page, period, tab]);

  const { data: holdingsData, isLoading: holdingsLoading } = useQuery({
    queryKey: ["smart-money", "holdings", cik, holdingsQuery],
    queryFn: () => apiGet<HoldingsResponse>(`/smart-money/investor/${cik}/holdings?${holdingsQuery}`),
    enabled: !!profile,
  });

  const periods = holdingsData?.periods ?? profile?.reportPeriods ?? [];
  const activePeriod = period ?? holdingsData?.reportPeriod ?? profile?.latestReportPeriod ?? "";

  if (profileLoading) {
    return <div className="h-40 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-800" />;
  }

  if (!profile) {
    return <p className="text-sm text-zinc-500">Investor not found.</p>;
  }

  const holdings = holdingsData?.holdings ?? [];

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <InvestorAvatar initials={profile.avatarInitials} color={profile.avatarColor} size="lg" />
          <div>
            <h2 className="text-xl font-semibold">{profile.name}</h2>
            <p className="text-sm text-zinc-500">
              {getInvestorTypeLabel(profile.type)} · CIK {profile.cik}
            </p>
            <p className="mt-1 text-xs text-zinc-500">{profile.description}</p>
          </div>
        </div>
        <Link
          href={`/smart-money/investor/${cik}/analysis`}
          className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
        >
          Thesis analysis →
        </Link>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-2.5 md:grid-cols-4">
        <MetricCard label="AUM" metricId="aum" value={formatCurrency(profile.aum)} />
        <MetricCard label="Holdings" value={profile.holdingsCount.toLocaleString()} />
        <MetricCard label="Top 5 concentration" metricId="top5_concentration" value={formatPct(profile.top5Concentration)} />
        <MetricCard label="Last filed" value={formatShortDate(profile.lastFilingDate)} />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => { setTab("holdings"); setPage(0); }}
          className={`rounded-lg px-3 py-1.5 text-sm ${tab === "holdings" ? "bg-zinc-100 font-medium dark:bg-zinc-800" : "text-zinc-500"}`}
        >
          Holdings
        </button>
        <button
          type="button"
          onClick={() => { setTab("changes"); setPage(0); }}
          className={`rounded-lg px-3 py-1.5 text-sm ${tab === "changes" ? "bg-zinc-100 font-medium dark:bg-zinc-800" : "text-zinc-500"}`}
        >
          Changes this quarter
        </button>
        {periods.length > 0 ? (
          <select
            value={activePeriod}
            onChange={(e) => { setPeriod(e.target.value); setPage(0); }}
            className="ml-auto rounded-lg border border-zinc-200 bg-white px-2 py-1 text-xs dark:border-zinc-700 dark:bg-zinc-900"
          >
            {periods.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        ) : null}
      </div>

      {holdingsLoading ? (
        <div className="h-32 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-800" />
      ) : holdings.length === 0 ? (
        <p className="py-8 text-center text-sm text-zinc-500">No holdings for this period.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-500 dark:bg-zinc-900">
              <tr>
                <th className="px-3 py-2">Company</th>
                <th className="px-3 py-2">Ticker</th>
                <th className="px-3 py-2 text-right">Value</th>
                <th className="px-3 py-2 text-right">Shares</th>
                <th className="px-3 py-2 text-right"><MetricTooltip metricId="portfolio_pct">% Portfolio</MetricTooltip></th>
                <th className="px-3 py-2 text-right"><MetricTooltip metricId="qoq">QoQ</MetricTooltip></th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h) => (
                <tr key={`${h.ticker}-${h.companyName}`} className="border-t border-zinc-100 dark:border-zinc-800">
                  <td className="px-3 py-2">{h.companyName}</td>
                  <td className="px-3 py-2"><TickerPill ticker={h.ticker} /></td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatCurrency(h.value)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatShares(h.shares)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatPct(h.portfolioPct)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {h.isNew ? (
                      <span className="text-blue-600">New</span>
                    ) : h.qoqChange > 0 ? (
                      <span className="text-emerald-600">+{formatPct(h.qoqChange)}</span>
                    ) : h.qoqChange < 0 ? (
                      <span className="text-rose-600">{formatPct(h.qoqChange)}</span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
