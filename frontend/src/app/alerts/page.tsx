"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { AppShell } from "@/components/app-shell";
import { SkeletonCard } from "@/components/movers-table";
import { useApi } from "@/lib/use-api";
import type { AlertItem } from "@/lib/types";

export default function AlertsPage() {
  const { get, post, del, isSignedIn } = useApi();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    symbol: "",
    alert_type: "price_above",
    threshold: "",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["alerts", isSignedIn],
    queryFn: () => get<{ items: AlertItem[] }>("/alerts"),
    enabled: isSignedIn,
    retry: false,
  });

  const createAlert = useMutation({
    mutationFn: () =>
      post<AlertItem>("/alerts", {
        symbol: form.symbol.toUpperCase(),
        alert_type: form.alert_type,
        params_json: { threshold: Number(form.threshold) },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const removeAlert = useMutation({
    mutationFn: (id: number) => del<void>(`/alerts/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <AppShell>
      {!isSignedIn ? (
        <p className="rounded-xl border border-zinc-200 bg-white p-6 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950">
          Sign in to manage alerts.
        </p>
      ) : (
        <>
        <div className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>
          <p className="mt-1 text-sm text-zinc-500">Price and event alerts with email + in-app delivery.</p>
        </div>

        <div className="mb-6 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          <h2 className="mb-3 text-sm font-medium">Create alert</h2>
          <div className="flex flex-wrap gap-2">
            <input
              className="rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              placeholder="Symbol"
              value={form.symbol}
              onChange={(e) => setForm((f) => ({ ...f, symbol: e.target.value }))}
            />
            <select
              className="rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              value={form.alert_type}
              onChange={(e) => setForm((f) => ({ ...f, alert_type: e.target.value }))}
            >
              <option value="price_above">Price above</option>
              <option value="price_below">Price below</option>
              <option value="pct_change_day">Daily % change</option>
              <option value="new_52w_high">New 52W high</option>
              <option value="dividend_announced">Dividend announced</option>
              <option value="insider_trade">Insider trade</option>
            </select>
            <input
              type="number"
              className="rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              placeholder="Threshold"
              value={form.threshold}
              onChange={(e) => setForm((f) => ({ ...f, threshold: e.target.value }))}
            />
            <button
              type="button"
              onClick={() => createAlert.mutate()}
              className="rounded-lg bg-zinc-900 px-4 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
            >
              Create
            </button>
          </div>
          <p className="mt-2 text-xs text-zinc-500">
            <MetricTooltip metricId="change_pct">Daily % change</MetricTooltip>
            {" · "}
            <MetricTooltip metricId="fifty_two_week_high">New 52W high</MetricTooltip>
          </p>
        </div>

        {isLoading && <SkeletonCard />}

        {data && (
          <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-left dark:border-zinc-800">
                  <th className="px-4 py-3">Symbol</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Params</th>
                  <th className="px-4 py-3">Active</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                      No alerts yet. Create one above.
                    </td>
                  </tr>
                ) : (
                  data.items.map((a) => (
                    <tr key={a.id} className="border-b border-zinc-100 dark:border-zinc-900">
                      <td className="px-4 py-2">{a.symbol ?? "—"}</td>
                      <td className="px-4 py-2">{a.alert_type}</td>
                      <td className="px-4 py-2 text-xs text-zinc-500">
                        {JSON.stringify(a.params_json)}
                      </td>
                      <td className="px-4 py-2">{a.is_active ? "Yes" : "No"}</td>
                      <td className="px-4 py-2">
                        <button
                          type="button"
                          onClick={() => removeAlert.mutate(a.id)}
                          className="text-xs text-rose-600 hover:underline"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
        </>
      )}
    </AppShell>
  );
}
