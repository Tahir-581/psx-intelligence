"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { FilterChips } from "@/components/smart-money/filter-chips";
import { InvestorAvatar } from "@/components/smart-money/investor-avatar";
import { TickerPill } from "@/components/smart-money/ticker-pill";
import { apiGet } from "@/lib/api";
import type { InvestmentsResponse } from "@/lib/smart-money-types";
import { formatCurrency, formatPct, formatShortDate } from "@/lib/smart-money-utils";

const ACTION_FILTERS = [
  { label: "All", value: "all" },
  { label: "New", value: "new" },
  { label: "Increased", value: "increased" },
  { label: "Reduced", value: "reduced" },
];

export default function SmartMoneyInvestmentsPage() {
  const [action, setAction] = useState("all");
  const [page, setPage] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ["smart-money", "investments", action, page],
    queryFn: () =>
      apiGet<InvestmentsResponse>(
        `/smart-money/investments?action=${action}&page=${page + 1}&limit=50`,
      ),
    refetchInterval: 120_000,
  });

  const investments = data?.investments ?? [];
  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / 50));

  return (
    <div>
      <h2 className="mb-3 text-sm font-medium">Quarter-over-quarter position changes</h2>
      <FilterChips options={ACTION_FILTERS} selected={action} onChange={(v) => { setAction(v); setPage(0); }} />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-800" />
          ))}
        </div>
      ) : investments.length === 0 ? (
        <p className="py-8 text-center text-sm text-zinc-500">No position changes found.</p>
      ) : (
        <div className="space-y-2">
          {investments.map((row) => (
            <div
              key={row.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-900"
            >
              <div className="flex min-w-0 items-center gap-2">
                <InvestorAvatar initials={row.avatarInitials} color={row.avatarColor} />
                <div>
                  <Link
                    href={row.investorCik ? `/smart-money/investor/${row.investorCik}` : "#"}
                    className="text-sm font-medium hover:underline"
                  >
                    {row.investorName}
                  </Link>
                  <div className="mt-0.5 flex items-center gap-2 text-xs text-zinc-500">
                    {row.ticker ? <TickerPill ticker={row.ticker} /> : null}
                    <span>{row.companyName}</span>
                  </div>
                </div>
              </div>
              <div className="text-right text-sm">
                <div className="font-medium tabular-nums">{formatCurrency(row.amount ?? 0)}</div>
                <div className="text-xs text-zinc-500">
                  {row.action === "new" ? "New" : row.action === "increased" ? "▲" : "▼"}{" "}
                  {row.portfolioPct != null ? formatPct(row.portfolioPct) : ""} · {formatShortDate(row.filedAt)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 ? (
        <div className="mt-4 flex justify-center gap-2">
          <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)} className="rounded border px-3 py-1 text-xs disabled:opacity-40">Previous</button>
          <button type="button" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)} className="rounded border px-3 py-1 text-xs disabled:opacity-40">Next</button>
        </div>
      ) : null}
    </div>
  );
}
