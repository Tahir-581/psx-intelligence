"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { SkeletonCard } from "@/components/movers-table";
import { API_BASE } from "@/lib/api";

import type { DataQualityReport, FailedTaskListResponse } from "@/lib/types";

interface ScraperHealthItem {
  scraper_name: string;
  last_success_at: string | null;
  last_run_at: string | null;
  records_ingested: number;
  error_message: string | null;
}

interface ParserReviewItem {
  id: number;
  source_type: string;
  source_url: string;
  symbol: string | null;
  confidence: number | null;
  status: string;
  raw_excerpt: string | null;
  created_at: string;
}

async function adminFetch<T>(path: string, key: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "X-Admin-Key": key,
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`Admin API error ${res.status}`);
  return res.json() as Promise<T>;
}

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [savedKey, setSavedKey] = useState("");

  const healthQuery = useQuery({
    queryKey: ["admin-health", savedKey],
    queryFn: () =>
      adminFetch<{ scrapers: ScraperHealthItem[] }>("/admin/scraper-health", savedKey),
    enabled: !!savedKey,
  });

  const reviewQuery = useQuery({
    queryKey: ["admin-review", savedKey],
    queryFn: () =>
      adminFetch<{ items: ParserReviewItem[] }>("/admin/parser-review", savedKey),
    enabled: !!savedKey,
  });

  const failedTasksQuery = useQuery({
    queryKey: ["admin-failed-tasks", savedKey],
    queryFn: () => adminFetch<FailedTaskListResponse>("/admin/failed-tasks", savedKey),
    enabled: !!savedKey,
  });

  const dataQualityQuery = useQuery({
    queryKey: ["admin-data-quality", savedKey],
    queryFn: () => adminFetch<DataQualityReport>("/admin/data-quality", savedKey),
    enabled: !!savedKey,
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      adminFetch(`/admin/parser-review/${id}`, savedKey, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => reviewQuery.refetch(),
  });

  return (
    <AppShell>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Admin</h1>
        <div className="flex gap-2">
          <input
            type="password"
            placeholder="Admin API key"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
          <button
            type="button"
            onClick={() => setSavedKey(adminKey)}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            Connect
          </button>
        </div>

        {healthQuery.isLoading && <SkeletonCard />}
        {healthQuery.data && (
          <section className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
            <h2 className="mb-3 font-semibold">Scraper Health</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-zinc-500">
                  <th className="py-2">Scraper</th>
                  <th>Last run</th>
                  <th>Records</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {healthQuery.data.scrapers.map((s) => (
                  <tr key={s.scraper_name} className="border-t border-zinc-100 dark:border-zinc-800">
                    <td className="py-2">{s.scraper_name}</td>
                    <td>{s.last_run_at ? new Date(s.last_run_at).toLocaleString() : "—"}</td>
                    <td>{s.records_ingested}</td>
                    <td className="max-w-xs truncate text-rose-600">{s.error_message ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {failedTasksQuery.data && (
          <section className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
            <h2 className="mb-3 font-semibold">Failed Celery Tasks</h2>
            {failedTasksQuery.data.items.length === 0 ? (
              <p className="text-sm text-zinc-500">No failed tasks recorded.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-zinc-500">
                      <th className="py-2">Task</th>
                      <th>Failed at</th>
                      <th>Retried</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {failedTasksQuery.data.items.map((t) => (
                      <tr key={t.id} className="border-t border-zinc-100 dark:border-zinc-800">
                        <td className="py-2">
                          <span className="font-medium">{t.task_name}</span>
                          <span className="ml-1 font-mono text-xs text-zinc-400">{t.task_id.slice(0, 8)}…</span>
                        </td>
                        <td>{new Date(t.failed_at).toLocaleString()}</td>
                        <td>{t.retried ? "Yes" : "No"}</td>
                        <td className="max-w-md truncate text-rose-600">{t.error_message ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {dataQualityQuery.data && (
          <section className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
            <h2 className="mb-3 font-semibold">Data Quality</h2>
            <dl className="grid gap-3 text-sm sm:grid-cols-3">
              <div className="rounded-lg border border-zinc-100 p-3 dark:border-zinc-800">
                <dt className="text-zinc-500">Active tickers</dt>
                <dd className="text-xl font-semibold tabular-nums">{dataQualityQuery.data.total_tickers}</dd>
              </div>
              <div className="rounded-lg border border-zinc-100 p-3 dark:border-zinc-800">
                <dt className="text-zinc-500">Missing financials</dt>
                <dd className="text-xl font-semibold tabular-nums text-amber-600">
                  {dataQualityQuery.data.tickers_missing_financials}
                </dd>
              </div>
              <div className="rounded-lg border border-zinc-100 p-3 dark:border-zinc-800">
                <dt className="text-zinc-500">Stale scrapers</dt>
                <dd className="text-xl font-semibold tabular-nums text-rose-600">
                  {dataQualityQuery.data.stale_scrapers.length}
                </dd>
              </div>
              <div className="rounded-lg border border-zinc-100 p-3 dark:border-zinc-800">
                <dt className="text-zinc-500">Stale indices</dt>
                <dd className="text-xl font-semibold tabular-nums text-rose-600">
                  {dataQualityQuery.data.stale_index_symbols.length}
                </dd>
              </div>
            </dl>
            {dataQualityQuery.data.stale_scrapers.length > 0 && (
              <ul className="mt-3 flex flex-wrap gap-2">
                {dataQualityQuery.data.stale_scrapers.map((s) => (
                  <li
                    key={s}
                    className="rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-xs text-rose-700 dark:border-rose-900 dark:bg-rose-950/40"
                  >
                    {s}
                  </li>
                ))}
              </ul>
            )}
            {dataQualityQuery.data.stale_index_symbols.length > 0 && (
              <ul className="mt-3 flex flex-wrap gap-2">
                {dataQualityQuery.data.stale_index_symbols.map((s) => (
                  <li
                    key={s}
                    className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/40"
                  >
                    {s}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {reviewQuery.data && (
          <section className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
            <h2 className="mb-3 font-semibold">Parser Review Queue</h2>
            <ul className="space-y-3">
              {reviewQuery.data.items.map((item) => (
                <li key={item.id} className="rounded-lg border border-zinc-100 p-3 dark:border-zinc-800">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium">{item.symbol ?? "—"}</span>
                    <span className="text-xs text-zinc-500">conf {item.confidence ?? "—"}</span>
                  </div>
                  <p className="mt-1 text-sm text-zinc-600 line-clamp-2">{item.raw_excerpt}</p>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={() => patchMutation.mutate({ id: item.id, status: "approved" })}
                      className="rounded bg-emerald-600 px-2 py-1 text-xs text-white"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => patchMutation.mutate({ id: item.id, status: "rejected" })}
                      className="rounded bg-rose-600 px-2 py-1 text-xs text-white"
                    >
                      Reject
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </AppShell>
  );
}
