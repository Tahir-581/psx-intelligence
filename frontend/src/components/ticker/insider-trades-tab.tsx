"use client";

import { useQuery } from "@tanstack/react-query";
import { MetricTooltip } from "@/components/metric-tooltip";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import type { InsiderTradesResponse } from "@/lib/types";
import { cn, formatNumber } from "@/lib/utils";

export function InsiderTradesTab({ symbol }: { symbol: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["insider-trades", symbol],
    queryFn: () => apiGet<InsiderTradesResponse>(`/ticker/${symbol}/insider-trades?days=90`),
  });

  if (isLoading) return <SkeletonCard />;

  const net90 = data?.net_90d ?? 0;
  const net30 = data?.net_30d ?? 0;

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Insider Trades</h2>
          {data?.cluster_buy_14d && (
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
              <MetricTooltip metricId="cluster_buy">Cluster buy (14d)</MetricTooltip>
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <NetPill label="30d" value={net30} />
          <NetPill label="90d" value={net90} />
        </div>
      </div>
      {!data?.trades?.length ? (
        <p className="text-sm text-zinc-500">No insider trades in the last 90 days.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-200 dark:border-zinc-800">
                <th className="py-2 pr-4">Date</th>
                <th className="py-2 pr-4">Director</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4 text-right">Shares</th>
                <th className="py-2 text-right">Price</th>
              </tr>
            </thead>
            <tbody>
              {data.trades.map((t) => (
                <tr key={t.id} className="border-b border-zinc-100 dark:border-zinc-900">
                  <td className="py-2 pr-4 tabular-nums">
                    {new Date(t.transaction_date).toLocaleDateString("en-PK")}
                  </td>
                  <td className="py-2 pr-4">
                    <div>{t.director_name}</div>
                    {t.designation && (
                      <div className="text-xs text-zinc-500">{t.designation}</div>
                    )}
                  </td>
                  <td className="py-2 pr-4 capitalize">{t.transaction_type}</td>
                  <td className="py-2 pr-4 text-right tabular-nums">{t.shares.toLocaleString()}</td>
                  <td className="py-2 text-right tabular-nums">
                    {t.price_per_share != null ? formatNumber(t.price_per_share) : "—"}
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

function NetPill({ label, value }: { label: string; value: number }) {
  const positive = value >= 0;
  const metricId = label === "30d" ? "net_insider_buy" : "net_insider_buy";
  return (
    <span
      className={cn(
        "rounded-full px-3 py-1 text-xs font-medium tabular-nums",
        positive
          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
          : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
      )}
    >
      <MetricTooltip metricId={metricId}>Net {label}</MetricTooltip>: {positive ? "+" : ""}
      {value.toLocaleString()}
    </span>
  );
}
