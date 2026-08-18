"use client";

import { useQuery } from "@tanstack/react-query";
import { MetricTooltip } from "@/components/metric-tooltip";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import type { OwnershipResponse } from "@/lib/types";
import { formatPct } from "@/lib/utils";

const DONUT_COLORS = ["#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#71717a"];

export function OwnershipTab({ symbol }: { symbol: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["ownership", symbol],
    queryFn: () => apiGet<OwnershipResponse>(`/ticker/${symbol}/ownership`),
  });

  if (isLoading) return <SkeletonCard />;

  const latest = data?.latest_snapshot ?? [];
  const namedHolders = data?.named_holders ?? [];

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-4 text-lg font-semibold">Ownership</h2>

      {data?.pledged_warning && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
          Pledged shares warning:{" "}
          {data.pledged_shares_pct != null ? formatPct(data.pledged_shares_pct) : "elevated pledge levels detected"}
        </div>
      )}

      {!latest.length ? (
        <p className="text-sm text-zinc-500">No ownership snapshots yet.</p>
      ) : (
        <>
          <div className="mb-6 flex flex-wrap items-center gap-6">
            <DonutChart items={latest} />
            {data && data.history.length > 1 && <OwnershipTrend history={data.history} />}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800">
                  <th className="py-2 pr-4">Category</th>
                  <th className="py-2 pr-4 text-right">Shares</th>
                  <th className="py-2 text-right"><MetricTooltip metricId="institutional_pct">% Outstanding</MetricTooltip></th>
                </tr>
              </thead>
              <tbody>
                {latest.map((row) => (
                  <tr key={row.holder_category} className="border-b border-zinc-100 dark:border-zinc-900">
                    <td className="py-2 pr-4 capitalize">{row.holder_category.replace(/_/g, " ")}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{row.shares.toLocaleString()}</td>
                    <td className="py-2 text-right tabular-nums">{formatPct(row.pct_outstanding)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {namedHolders.length > 0 && (
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-medium">Named Holders</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200 dark:border-zinc-800">
                      <th className="py-2 pr-4">Holder</th>
                      <th className="py-2 pr-4">Category</th>
                      <th className="py-2 text-right"><MetricTooltip metricId="institutional_pct">% Outstanding</MetricTooltip></th>
                    </tr>
                  </thead>
                  <tbody>
                    {namedHolders.map((h) => (
                      <tr key={`${h.holder_name}-${h.holder_category}`} className="border-b border-zinc-100 dark:border-zinc-900">
                        <td className="py-2 pr-4 font-medium">{h.holder_name ?? "—"}</td>
                        <td className="py-2 pr-4 capitalize text-zinc-500">{h.holder_category.replace(/_/g, " ")}</td>
                        <td className="py-2 text-right tabular-nums">{formatPct(h.pct_outstanding)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {data?.free_float_pct != null && (
            <p className="mt-4 text-xs text-zinc-500">
              <MetricTooltip metricId="free_float">Free float</MetricTooltip>: {formatPct(data.free_float_pct)}
            </p>
          )}
        </>
      )}
    </section>
  );
}

function DonutChart({ items }: { items: OwnershipResponse["latest_snapshot"] }) {
  let cumulative = 0;
  const segments = items.map((item, i) => {
    const start = cumulative;
    cumulative += item.pct_outstanding;
    return { ...item, start, end: cumulative, color: DONUT_COLORS[i % DONUT_COLORS.length] };
  });

  const gradient = segments
    .map((s) => `${s.color} ${s.start}% ${s.end}%`)
    .join(", ");

  return (
    <div className="flex items-center gap-4">
      <div
        className="h-24 w-24 rounded-full"
        style={{ background: `conic-gradient(${gradient})` }}
      />
      <div className="space-y-1 text-xs">
        {segments.map((s) => (
          <div key={s.holder_category} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
            <span className="capitalize">{s.holder_category.replace(/_/g, " ")}</span>
            <span className="tabular-nums text-zinc-500">{formatPct(s.pct_outstanding)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function OwnershipTrend({ history }: { history: OwnershipResponse["history"] }) {
  const categories = history[history.length - 1]?.snapshots.map((s) => s.holder_category) ?? [];
  const dates = history.slice(-6);

  return (
    <div className="flex-1 min-w-[200px]">
      <h3 className="mb-2 text-xs font-medium text-zinc-500">Ownership trend</h3>
      <div className="flex h-16 items-end gap-1">
        {dates.map((h) => {
          const institutional = h.snapshots.find((s) => s.holder_category === "institutional");
          const pct = institutional?.pct_outstanding ?? 0;
          return (
            <div key={h.as_of_date} className="flex flex-1 flex-col items-center gap-1">
              <div
                className="w-full rounded-t bg-sky-500"
                style={{ height: `${Math.max(4, pct * 2)}%`, minHeight: 4 }}
                title={`${h.as_of_date}: ${pct}%`}
              />
              <span className="text-[9px] text-zinc-500">
                {new Date(h.as_of_date).toLocaleDateString("en-PK", { month: "short" })}
              </span>
            </div>
          );
        })}
      </div>
      {categories.length > 0 && (
        <p className="mt-1 text-[10px] text-zinc-500">
          <MetricTooltip metricId="institutional_pct">Institutional % over time</MetricTooltip>
        </p>
      )}
    </div>
  );
}
