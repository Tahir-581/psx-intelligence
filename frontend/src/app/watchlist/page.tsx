"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MetricTooltip } from "@/components/metric-tooltip";
import { AppShell } from "@/components/app-shell";
import { SkeletonCard } from "@/components/movers-table";
import { useApi } from "@/lib/use-api";
import type { WatchlistResponse } from "@/lib/types";

export default function WatchlistPage() {
  const { get, del, isSignedIn } = useApi();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["watchlist", isSignedIn],
    queryFn: () => get<WatchlistResponse>("/watchlist"),
    enabled: isSignedIn,
  });

  const remove = useMutation({
    mutationFn: (symbol: string) => del<WatchlistResponse>(`/watchlist/${symbol}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Watchlist</h1>
        <p className="mt-1 text-sm text-zinc-500">Track symbols with live quotes.</p>
      </div>

      {!isSignedIn && (
        <p className="rounded-xl border border-zinc-200 bg-white p-6 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950">
          Sign in to manage your watchlist. Add symbols from any ticker page.
        </p>
      )}

      {isLoading && <SkeletonCard />}

      {data && (
        <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left dark:border-zinc-800">
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3"><MetricTooltip metricId="ltp">LTP</MetricTooltip></th>
                <th className="px-4 py-3"><MetricTooltip metricId="change_pct">Change</MetricTooltip></th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                    Watchlist empty. Search a ticker and add it from the ticker page.
                  </td>
                </tr>
              ) : (
                data.items.map((item) => (
                  <tr key={item.symbol} className="border-b border-zinc-100 dark:border-zinc-900">
                    <td className="px-4 py-2">
                      <Link href={`/ticker/${item.symbol}`} className="font-medium hover:underline">
                        {item.symbol}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-zinc-500">{item.name ?? "—"}</td>
                    <td className="px-4 py-2 tabular-nums">{item.ltp?.toFixed(2) ?? "—"}</td>
                    <td
                      className={`px-4 py-2 tabular-nums ${(item.change_pct ?? 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}
                    >
                      {item.change_pct != null ? `${item.change_pct.toFixed(2)}%` : "—"}
                    </td>
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        onClick={() => remove.mutate(item.symbol)}
                        className="text-xs text-rose-600 hover:underline"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
