"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import { getMetricLabel } from "@/lib/metric-glossary";
import type { RatiosResponse } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

export function RatiosTab({ symbol }: { symbol: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["ratios", symbol],
    queryFn: () => apiGet<RatiosResponse>(`/ticker/${symbol}/ratios`),
  });

  const chartRatios = useMemo(() => {
    if (!data?.history?.length) return [];
    const codes = Object.keys(data.history[data.history.length - 1].ratios);
    return codes.slice(0, 4);
  }, [data]);

  if (isLoading) return <SkeletonCard />;
  if (!data) {
    return <p className="text-sm text-zinc-500">Unable to load ratios.</p>;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="mb-4 text-lg font-semibold">Latest Ratios</h2>
        <p className="mb-4 text-sm text-zinc-500">Sector: {data.sector}</p>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {data.latest.map((r) => {
            const median = data.sector_medians[r.code];
            const aboveMedian = r.value != null && median != null && r.value > median;
            return (
              <div
                key={r.code}
                className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800"
              >
                <div className="text-xs text-zinc-500">
                  <MetricTooltip metricId={r.code}>{getMetricLabel(r.code)}</MetricTooltip>
                </div>
                <div className="text-lg font-semibold tabular-nums">
                  {r.value != null ? formatNumber(r.value) : "—"}
                </div>
                {median != null && (
                  <div className={`text-xs ${aboveMedian ? "text-emerald-600" : "text-zinc-500"}`}>
                    Sector median: {formatNumber(median)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {chartRatios.map((code) => {
        const points = data.history
          .map((h) => ({
            period: h.period_end,
            value: h.ratios[code],
          }))
          .filter((p) => p.value != null);
        const max = Math.max(...points.map((p) => p.value ?? 0), 1);
        return (
          <section
            key={code}
            className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950"
          >
            <h3 className="mb-3 text-sm font-medium">
              <MetricTooltip metricId={code}>{getMetricLabel(code)}</MetricTooltip> — Time Series
            </h3>
            {points.length ? (
              <div className="flex h-28 items-end gap-1">
                {points.map((p) => (
                  <div key={p.period} className="flex flex-1 flex-col items-center gap-1">
                    <div
                      className="w-full rounded-t bg-sky-500"
                      style={{
                        height: `${((p.value ?? 0) / max) * 100}%`,
                        minHeight: 4,
                      }}
                      title={`${p.period}: ${p.value}`}
                    />
                    <span className="text-[9px] text-zinc-500">
                      {new Date(p.period).toLocaleDateString("en-PK", {
                        month: "short",
                        year: "2-digit",
                      })}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-500">No history for this ratio.</p>
            )}
          </section>
        );
      })}
    </div>
  );
}
