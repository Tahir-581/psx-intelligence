"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { AppShell } from "@/components/app-shell";
import { SkeletonCard } from "@/components/movers-table";
import { useApi } from "@/lib/use-api";
import type { PortfolioResponse } from "@/lib/types";

export default function PortfolioPage() {
  const { get, post, del, isSignedIn } = useApi();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    symbol: "",
    quantity: "",
    avg_buy_price: "",
    purchase_date: new Date().toISOString().slice(0, 10),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["portfolio", isSignedIn],
    queryFn: () => get<PortfolioResponse>("/portfolio"),
    enabled: isSignedIn,
    retry: false,
  });

  const addHolding = useMutation({
    mutationFn: () =>
      post<PortfolioResponse>("/portfolio/holdings", {
        symbol: form.symbol.toUpperCase(),
        quantity: Number(form.quantity),
        avg_buy_price: Number(form.avg_buy_price),
        purchase_date: form.purchase_date,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      setShowForm(false);
    },
  });

  const removeHolding = useMutation({
    mutationFn: (id: number) => del<PortfolioResponse>(`/portfolio/holdings/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["portfolio"] }),
  });

  return (
    <AppShell>
      {!isSignedIn ? (
        <p className="rounded-xl border border-zinc-200 bg-white p-6 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950">
          Sign in to manage your portfolio.
        </p>
      ) : (
        <>
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Portfolio</h1>
            <p className="mt-1 text-sm text-zinc-500">Manual holdings with live P&L and sector exposure.</p>
          </div>
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            Add holding
          </button>
        </div>

        {isLoading && <SkeletonCard />}

        {data && (
          <>
            <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { label: "Total value", metricId: "total_value", value: `PKR ${data.summary.total_value.toLocaleString()}` },
                { label: "Unrealized P&L", metricId: "pnl", value: `${data.summary.unrealized_pnl_pct.toFixed(2)}%` },
                { label: "YTD dividends", metricId: "dividend_income_ytd", value: `PKR ${data.summary.dividend_income_ytd.toLocaleString()}` },
                { label: "Portfolio beta", metricId: "beta", value: data.summary.portfolio_beta?.toFixed(2) ?? "—" },
              ].map((c) => (
                <div
                  key={c.label}
                  className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950"
                >
                  <p className="text-xs text-zinc-500">
                    <MetricTooltip metricId={c.metricId}>{c.label}</MetricTooltip>
                  </p>
                  <p className="mt-1 text-lg font-semibold tabular-nums">{c.value}</p>
                </div>
              ))}
            </div>

            {data.summary.concentration_warning && (
              <p className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm dark:border-amber-900 dark:bg-amber-950/40">
                Concentration risk: one or more sectors exceed 30% of portfolio.
              </p>
            )}

            <div className="mb-6 grid gap-6 lg:grid-cols-2">
              <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
                <h2 className="mb-3 text-sm font-medium">Sector exposure</h2>
                <div className="space-y-2">
                  {data.summary.sector_exposure.map((s) => (
                    <div key={s.sector}>
                      <div className="flex justify-between text-xs">
                        <span>{s.sector}</span>
                        <span>{s.weight_pct.toFixed(1)}%</span>
                      </div>
                      <div className="mt-1 h-2 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                        <div
                          className={`h-full rounded-full ${s.concentrated ? "bg-amber-500" : "bg-emerald-500"}`}
                          style={{ width: `${Math.min(s.weight_pct, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
                <h2 className="mb-3 text-sm font-medium"><MetricTooltip metricId="kse100">Portfolio vs KSE-100</MetricTooltip></h2>
                <svg viewBox="0 0 400 120" className="h-32 w-full">
                  {data.summary.vs_kse100.length > 1 &&
                    (() => {
                      const pts = data.summary.vs_kse100;
                      const xs = pts.map((_, i) => (i / (pts.length - 1)) * 380 + 10);
                      const portYs = pts.map((p) => 110 - (p.portfolio / 150) * 100);
                      const kseYs = pts.map((p) =>
                        p.kse100 != null ? 110 - (p.kse100 / 150) * 100 : 110
                      );
                      const line = (ys: number[]) =>
                        ys.map((y, i) => `${i === 0 ? "M" : "L"}${xs[i]},${y}`).join(" ");
                      return (
                        <>
                          <path d={line(portYs)} fill="none" stroke="#10b981" strokeWidth={2} />
                          <path d={line(kseYs)} fill="none" stroke="#71717a" strokeWidth={1.5} strokeDasharray="4" />
                        </>
                      );
                    })()}
                </svg>
                <div className="mt-2 flex gap-4 text-xs text-zinc-500">
                  <span className="text-emerald-600">— Portfolio</span>
                  <span>— KSE-100</span>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 text-left dark:border-zinc-800">
                    <th className="px-4 py-3">Symbol</th>
                    <th className="px-4 py-3"><MetricTooltip metricId="quantity">Qty</MetricTooltip></th>
                    <th className="px-4 py-3"><MetricTooltip metricId="avg_cost">Avg cost</MetricTooltip></th>
                    <th className="px-4 py-3"><MetricTooltip metricId="ltp">LTP</MetricTooltip></th>
                    <th className="px-4 py-3"><MetricTooltip metricId="pnl">P&L</MetricTooltip></th>
                    <th className="px-4 py-3"><MetricTooltip metricId="weight">Weight</MetricTooltip></th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {data.holdings.map((h) => (
                    <tr key={h.id} className="border-b border-zinc-100 dark:border-zinc-900">
                      <td className="px-4 py-2">
                        <Link href={`/ticker/${h.symbol}`} className="font-medium hover:underline">
                          {h.symbol}
                        </Link>
                      </td>
                      <td className="px-4 py-2 tabular-nums">{h.quantity}</td>
                      <td className="px-4 py-2 tabular-nums">{h.avg_buy_price.toFixed(2)}</td>
                      <td className="px-4 py-2 tabular-nums">{h.ltp?.toFixed(2) ?? "—"}</td>
                      <td
                        className={`px-4 py-2 tabular-nums ${(h.unrealized_pnl_pct ?? 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}
                      >
                        {h.unrealized_pnl_pct?.toFixed(2) ?? "—"}%
                      </td>
                      <td className="px-4 py-2 tabular-nums">{h.weight_pct?.toFixed(1) ?? "—"}%</td>
                      <td className="px-4 py-2">
                        <button
                          type="button"
                          onClick={() => removeHolding.mutate(h.id)}
                          className="text-xs text-rose-600 hover:underline"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {showForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 dark:bg-zinc-950">
              <h2 className="text-lg font-medium">Add holding</h2>
              <div className="mt-4 space-y-3">
                {(["symbol", "quantity", "avg_buy_price"] as const).map((field) => (
                  <input
                    key={field}
                    className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                    placeholder={field.replace("_", " ")}
                    value={form[field]}
                    onChange={(e) => setForm((f) => ({ ...f, [field]: e.target.value }))}
                  />
                ))}
                <input
                  type="date"
                  className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                  value={form.purchase_date}
                  onChange={(e) => setForm((f) => ({ ...f, purchase_date: e.target.value }))}
                />
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <button type="button" onClick={() => setShowForm(false)} className="rounded-lg px-4 py-2 text-sm">
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => addHolding.mutate()}
                  className="rounded-lg bg-zinc-900 px-4 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
                >
                  Save
                </button>
              </div>
            </div>
          </div>
        )}
        </>
      )}
    </AppShell>
  );
}
