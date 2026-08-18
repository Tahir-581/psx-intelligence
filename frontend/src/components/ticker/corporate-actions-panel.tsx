"use client";

import { useQuery } from "@tanstack/react-query";
import { MetricTooltip } from "@/components/metric-tooltip";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import type { CorpActionAnalyticsResponse, CorporateActionListResponse } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

function daysUntil(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  const diff = new Date(dateStr).getTime() - Date.now();
  return Math.ceil(diff / (24 * 60 * 60 * 1000));
}

export function CorporateActionsPanel({ symbol, fullTab = false }: { symbol: string; fullTab?: boolean }) {
  const { data, isLoading } = useQuery({
    queryKey: ["corporate-actions", symbol],
    queryFn: () => apiGet<CorporateActionListResponse>(`/ticker/${symbol}/corporate-actions`),
  });

  const { data: analytics } = useQuery({
    queryKey: ["corp-analytics", symbol],
    queryFn: () => apiGet<CorpActionAnalyticsResponse>(`/ticker/${symbol}/corporate-actions/analytics`),
    enabled: fullTab,
  });

  if (isLoading) return <SkeletonCard />;

  const dividends = (data?.items ?? []).filter((a) => a.action_type === "cash_dividend");
  const upcoming = dividends.find((d) => daysUntil(d.ex_date) !== null && (daysUntil(d.ex_date) ?? 0) >= 0);
  const allActions = data?.items ?? [];

  const dpsSeries = analytics?.dps_series ?? [];
  const maxDps = Math.max(...dpsSeries.map((d) => d.dps), 1);

  const byYear: Record<number, number> = {};
  for (const d of dividends) {
    if (d.amount_per_share) {
      const year = new Date(d.announced_at).getFullYear();
      byYear[year] = (byYear[year] ?? 0) + d.amount_per_share;
    }
  }
  const years = Object.keys(byYear)
    .map(Number)
    .sort((a, b) => a - b)
    .slice(-10);
  const maxYearDps = Math.max(...years.map((y) => byYear[y]), 1);

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-4 text-lg font-semibold">Corporate Actions</h2>
      {upcoming && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm dark:border-emerald-900 dark:bg-emerald-950">
          <span className="font-medium">Upcoming ex-dividend: </span>
          {upcoming.ex_date} ({daysUntil(upcoming.ex_date)} days)
          {upcoming.amount_per_share != null && ` — Rs ${upcoming.amount_per_share}/share`}
        </div>
      )}

      {analytics?.terp && (
        <div className="mb-4 rounded-lg border border-zinc-200 p-3 text-sm dark:border-zinc-800">
          <h3 className="mb-1 font-medium"><MetricTooltip metricId="terp">TERP Calculation</MetricTooltip></h3>
          <p>
            Ratio {analytics.terp.rights_ratio} · Market Rs {formatNumber(analytics.terp.market_price)} · Rights Rs{" "}
            {formatNumber(analytics.terp.rights_price)} → TERP Rs {formatNumber(analytics.terp.terp)}
          </p>
        </div>
      )}

      {dpsSeries.length > 0 ? (
        <div className="mb-4">
          <h3 className="mb-2 text-sm font-medium text-zinc-500"><MetricTooltip metricId="dps">DPS history (analytics)</MetricTooltip></h3>
          <div className="flex h-24 items-end gap-2">
            {dpsSeries.map((pt) => (
              <div key={pt.year} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="w-full rounded-t bg-sky-500"
                  style={{ height: `${(pt.dps / maxDps) * 100}%`, minHeight: 4 }}
                  title={`${pt.year}: Rs ${pt.dps}`}
                />
                <span className="text-[10px] text-zinc-500">{pt.year}</span>
              </div>
            ))}
          </div>
        </div>
      ) : years.length > 0 ? (
        <div className="mb-4">
          <h3 className="mb-2 text-sm font-medium text-zinc-500"><MetricTooltip metricId="dps">DPS by year</MetricTooltip></h3>
          <div className="flex h-24 items-end gap-2">
            {years.map((year) => (
              <div key={year} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="w-full rounded-t bg-sky-500"
                  style={{ height: `${(byYear[year] / maxYearDps) * 100}%`, minHeight: 4 }}
                  title={`Rs ${byYear[year]}`}
                />
                <span className="text-[10px] text-zinc-500">{year}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="mb-4 text-sm text-zinc-500">No dividend history extracted yet.</p>
      )}

      {fullTab && allActions.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-200 dark:border-zinc-800">
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Announced</th>
                <th className="py-2 pr-4"><MetricTooltip metricId="ex_date">Ex Date</MetricTooltip></th>
                <th className="py-2">Amount</th>
              </tr>
            </thead>
            <tbody>
              {allActions.map((a) => (
                <tr key={a.id} className="border-b border-zinc-100 dark:border-zinc-900">
                  <td className="py-2 pr-4 capitalize">{a.action_type.replace(/_/g, " ")}</td>
                  <td className="py-2 pr-4 tabular-nums">
                    {new Date(a.announced_at).toLocaleDateString("en-PK")}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">{a.ex_date ?? "—"}</td>
                  <td className="py-2 tabular-nums">
                    {a.amount_per_share != null ? `Rs ${a.amount_per_share}` : a.ratio ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
