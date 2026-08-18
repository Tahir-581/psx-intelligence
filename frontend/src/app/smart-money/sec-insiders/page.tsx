"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import type { SecInsidersResponse } from "@/lib/smart-money-types";
import { formatCurrency, formatShortDate } from "@/lib/smart-money-utils";

export default function SecInsidersPage() {
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const { data, isLoading } = useQuery({
    queryKey: ["smart-money", "sec-insiders", debouncedQ, page],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page + 1), limit: "50" });
      if (debouncedQ) params.set("q", debouncedQ);
      return apiGet<SecInsidersResponse>(`/smart-money/sec-insiders?${params}`);
    },
  });

  const insiders = data?.insiders ?? [];

  return (
    <div>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-sm font-medium">US SEC Form 4 insider trades</h2>
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onBlur={() => setDebouncedQ(q.trim())}
          placeholder="Search insiders…"
          className="w-full max-w-xs rounded-lg border border-zinc-200 px-3 py-1.5 text-xs dark:border-zinc-700 dark:bg-zinc-900"
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-zinc-100 dark:bg-zinc-800" />
          ))}
        </div>
      ) : insiders.length === 0 ? (
        <p className="py-8 text-center text-sm text-zinc-500">
          No SEC insider data yet. Run <code className="text-xs">python -m scripts.ingest_sec_form4</code> to populate.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-500 dark:bg-zinc-900">
              <tr>
                <th className="px-3 py-2">Insider</th>
                <th className="px-3 py-2">Company</th>
                <th className="px-3 py-2">Action</th>
                <th className="px-3 py-2">Filed</th>
                <th className="px-3 py-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {insiders.map((row) => (
                <tr key={row.id} className="border-t border-zinc-100 dark:border-zinc-800">
                  <td className="px-3 py-2 font-medium">{row.name}</td>
                  <td className="px-3 py-2">
                    {row.ticker ? <span className="font-mono text-xs">{row.ticker}</span> : null}{" "}
                    {row.companyName}
                  </td>
                  <td className="px-3 py-2 capitalize">{row.action ?? "—"}</td>
                  <td className="px-3 py-2">{formatShortDate(row.filedAt)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {row.amount != null ? formatCurrency(row.amount) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
