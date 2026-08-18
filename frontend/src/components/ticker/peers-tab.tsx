"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { MetricTooltip } from "@/components/metric-tooltip";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import type { PeersResponse } from "@/lib/types";

export function PeersTab({ symbol }: { symbol: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["peers", symbol],
    queryFn: () => apiGet<PeersResponse>(`/ticker/${symbol}/peers`),
  });

  if (isLoading) return <SkeletonCard />;
  if (error || !data) {
    return (
      <p className="rounded-xl border border-zinc-200 p-4 text-sm text-zinc-500 dark:border-zinc-800">
        Unable to load sector peers.
      </p>
    );
  }

  const rows = [...data.peers, data.sector_median];

  return (
    <div>
      <p className="mb-4 text-sm text-zinc-500">
        Sector: <span className="font-medium text-zinc-900 dark:text-zinc-100">{data.sector}</span>
      </p>
      <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-200 text-left dark:border-zinc-800">
              <th className="px-4 py-3">Symbol</th>
              <th className="px-4 py-3"><MetricTooltip metricId="pe_ttm">P/E</MetricTooltip></th>
              <th className="px-4 py-3"><MetricTooltip metricId="roe">ROE</MetricTooltip></th>
              <th className="px-4 py-3"><MetricTooltip metricId="debt_to_equity">D/E</MetricTooltip></th>
              <th className="px-4 py-3"><MetricTooltip metricId="dividend_yield">Div %</MetricTooltip></th>
              <th className="px-4 py-3"><MetricTooltip metricId="return_1m">1M ret</MetricTooltip></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.symbol}
                className={`border-b border-zinc-100 dark:border-zinc-900 ${
                  row.symbol === "SECTOR_MEDIAN" ? "bg-zinc-50 font-medium dark:bg-zinc-900/50" : ""
                }`}
              >
                <td className="px-4 py-2">
                  {row.symbol === "SECTOR_MEDIAN" ? (
                    row.name
                  ) : (
                    <Link href={`/ticker/${row.symbol}`} className="hover:underline">
                      {row.symbol}
                    </Link>
                  )}
                </td>
                <td className="px-4 py-2 tabular-nums">{row.pe_ttm?.toFixed(1) ?? "—"}</td>
                <td className="px-4 py-2 tabular-nums">{row.roe?.toFixed(1) ?? "—"}</td>
                <td className="px-4 py-2 tabular-nums">{row.debt_to_equity?.toFixed(2) ?? "—"}</td>
                <td className="px-4 py-2 tabular-nums">{row.dividend_yield?.toFixed(2) ?? "—"}</td>
                <td className="px-4 py-2 tabular-nums">{row.return_1m?.toFixed(2) ?? "—"}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
