"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { SkeletonCard } from "@/components/movers-table";
import { RatiosTab } from "@/components/ticker/ratios-tab";
import { apiGet } from "@/lib/api";
import type { FinancialsResponse } from "@/lib/types";
import { cn, formatNumber } from "@/lib/utils";

function yoyClass(pct: number | null | undefined) {
  if (pct == null) return "";
  if (pct >= 20) return "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300";
  if (pct <= -20) return "bg-rose-50 text-rose-800 dark:bg-rose-950 dark:text-rose-300";
  return "";
}

export function FinancialsTab({ symbol }: { symbol: string }) {
  const [periodType, setPeriodType] = useState<"quarterly" | "annual">("quarterly");
  const [subTab, setSubTab] = useState<"statements" | "ratios">("statements");
  const { data, isLoading } = useQuery({
    queryKey: ["financials", symbol, periodType],
    queryFn: () =>
      apiGet<FinancialsResponse>(`/ticker/${symbol}/financials?period_type=${periodType}`),
  });

  const exportCsv = async () => {
    if (!data?.rows?.length) return;
    const headers = ["Line Item", ...data.periods.map((p) => p.period_end)];
    const rows = data.rows.map((r) => [
      r.line_code,
      ...data.periods.map((p) => String(r.values[p.period_end] ?? "")),
    ]);
    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${symbol}-financials-${periodType}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (subTab === "ratios") {
    return (
      <div className="space-y-4">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setSubTab("statements")}
            className="rounded-full bg-zinc-100 px-3 py-1 text-xs dark:bg-zinc-800"
          >
            Statements
          </button>
          <button
            type="button"
            className="rounded-full bg-zinc-900 px-3 py-1 text-xs text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            Ratios
          </button>
        </div>
        <RatiosTab symbol={symbol} />
      </div>
    );
  }

  if (isLoading) return <SkeletonCard />;

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Financials</h2>
          <button
            type="button"
            onClick={() => setSubTab("ratios")}
            className="rounded-full bg-zinc-100 px-3 py-1 text-xs dark:bg-zinc-800"
          >
            Ratios →
          </button>
        </div>
        <div className="flex gap-2">
          {(["quarterly", "annual"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setPeriodType(t)}
              className={`rounded-full px-3 py-1 text-xs capitalize ${
                periodType === t
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800"
              }`}
            >
              {t}
            </button>
          ))}
          <button
            type="button"
            onClick={exportCsv}
            disabled={!data?.rows?.length}
            className="rounded-full bg-sky-600 px-3 py-1 text-xs text-white disabled:opacity-50"
          >
            Export CSV
          </button>
        </div>
      </div>
      {data?.low_confidence && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
          Some figures were parsed with low confidence and may need review.
        </div>
      )}
      {!!data?.validation_flags?.length && (
        <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:border-rose-900 dark:bg-rose-950">
          {data.validation_flags.join(" · ")}
        </div>
      )}
      {!data?.rows?.length ? (
        <p className="text-sm text-zinc-500">No financial data yet. PDF parsing runs after announcements backfill.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-200 dark:border-zinc-800">
                <th className="py-2 pr-4 font-medium">Line Item</th>
                {data.periods.map((p) => (
                  <th key={p.period_id} className="py-2 pr-4 font-medium tabular-nums">
                    <div>
                      {new Date(p.period_end).toLocaleDateString("en-PK", {
                        month: "short",
                        year: "2-digit",
                      })}
                    </div>
                    {p.source_pdf_url && (
                      <a
                        href={p.source_pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] font-normal text-sky-600 hover:underline dark:text-sky-400"
                      >
                        PDF
                      </a>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row) => (
                <tr key={row.line_code} className="border-b border-zinc-100 dark:border-zinc-900">
                  <td className="py-2 pr-4 capitalize text-zinc-600 dark:text-zinc-400">
                    <MetricTooltip metricId={row.line_code}>
                      {row.line_code.replace(/_/g, " ")}
                    </MetricTooltip>
                  </td>
                  {data.periods.map((p) => {
                    const yoy = row.yoy_change_pct?.[p.period_end];
                    return (
                      <td
                        key={p.period_id}
                        className={cn("py-2 pr-4 tabular-nums", yoyClass(yoy))}
                        title={yoy != null ? `YoY: ${yoy.toFixed(1)}%` : undefined}
                      >
                        {row.values[p.period_end] != null
                          ? formatNumber(row.values[p.period_end])
                          : "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
