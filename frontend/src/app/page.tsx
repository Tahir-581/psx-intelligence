"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { AppShell } from "@/components/app-shell";
import { MoversTable, SkeletonCard } from "@/components/movers-table";
import { PriceChart } from "@/components/price-chart";
import { SectorHeatmap } from "@/components/sector-heatmap";
import { apiGet } from "@/lib/api";
import type { CorporateCalendarResponse, MarketSummaryResponse, PriceSeriesResponse } from "@/lib/types";
import Link from "next/link";

export default function HomePage() {
  const [range, setRange] = useState<"1W" | "1M" | "3M" | "6M" | "1Y" | "3Y" | "5Y" | "Max">("1M");

  const { data: summary, isLoading } = useQuery({
    queryKey: ["market-summary"],
    queryFn: () => apiGet<MarketSummaryResponse>("/market/summary"),
    refetchInterval: 60_000,
  });

  const { data: indexPrices } = useQuery({
    queryKey: ["kse100-prices"],
    queryFn: () => apiGet<PriceSeriesResponse>("/ticker/KSE100/prices"),
    refetchInterval: 300_000,
  });

  const { data: calendar } = useQuery({
    queryKey: ["corporate-calendar"],
    queryFn: () => apiGet<CorporateCalendarResponse>("/market/corporate-calendar"),
    refetchInterval: 300_000,
  });

  const upcomingCalendar = (calendar?.items ?? [])
    .filter((item) => item.ex_date && new Date(item.ex_date) >= new Date())
    .slice(0, 8);

  const indexBars =
    indexPrices?.bars.map((b) => ({
      ...b,
      open: b.close * 0.999,
      high: b.close * 1.001,
      low: b.close * 0.998,
    })) ?? [];

  return (
    <AppShell
      marketOpen={summary?.market_open}
      indexLevel={summary?.index_level}
      indexChangePct={summary?.index_change_pct}
    >
      <div className="space-y-6">
        <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
          <div className="mb-4 flex items-end justify-between">
            <div>
              <h2 className="text-lg font-semibold"><MetricTooltip metricId="kse100">KSE-100</MetricTooltip></h2>
              <p className="text-sm text-zinc-500">Pakistan benchmark index</p>
            </div>
            {summary && (
              <div className="text-right">
                <div className="text-2xl font-semibold tabular-nums">
                  {summary.index_level?.toLocaleString("en-PK", { maximumFractionDigits: 2 }) ?? "—"}
                </div>
                <div className={summary.index_change_pct && summary.index_change_pct >= 0 ? "text-emerald-600" : "text-rose-600"}>
                  {summary.index_change_pct != null ? `${summary.index_change_pct.toFixed(2)}%` : ""}
                </div>
              </div>
            )}
          </div>
          {indexBars.length > 0 ? (
            <PriceChart bars={indexBars} range={range} onRangeChange={setRange} />
          ) : (
            <SkeletonCard />
          )}
        </section>

        {summary && (
          <div className="grid grid-cols-3 gap-3 text-center text-sm">
            <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-950">
              <div className="text-emerald-600 font-semibold">{summary.advances}</div>
              <div className="text-zinc-500"><MetricTooltip metricId="advances">Advances</MetricTooltip></div>
            </div>
            <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-950">
              <div className="text-rose-600 font-semibold">{summary.declines}</div>
              <div className="text-zinc-500"><MetricTooltip metricId="declines">Declines</MetricTooltip></div>
            </div>
            <div className="rounded-lg border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-950">
              <div className="font-semibold">{summary.unchanged}</div>
              <div className="text-zinc-500"><MetricTooltip metricId="unchanged">Unchanged</MetricTooltip></div>
            </div>
          </div>
        )}

        <SectorHeatmap />

        {upcomingCalendar.length > 0 && (
          <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
            <h2 className="mb-4 text-lg font-semibold">Corporate Calendar</h2>
            <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
              {upcomingCalendar.map((item, i) => (
                <li key={`${item.symbol}-${item.ex_date}-${i}`} className="flex items-center justify-between py-2 text-sm">
                  <div>
                    <Link href={`/ticker/${item.symbol}`} className="font-medium hover:underline">
                      {item.symbol}
                    </Link>
                    <span className="ml-2 capitalize text-zinc-500">
                      {item.action_type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="text-right text-zinc-500">
                    <div className="tabular-nums">{item.ex_date}</div>
                    {item.amount_per_share != null && (
                      <div className="text-xs">Rs {item.amount_per_share}/sh</div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {isLoading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : (
            <>
              <MoversTable title="Top Gainers" items={summary?.top_gainers ?? []} positive />
              <MoversTable title="Top Losers" items={summary?.top_losers ?? []} positive={false} />
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
