"use client";

import { useQuery } from "@tanstack/react-query";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import type { CreditRatingsResponse, GovernanceResponse } from "@/lib/types";

export function GovernanceTab({ symbol }: { symbol: string }) {
  const { data: governance, isLoading: govLoading } = useQuery({
    queryKey: ["governance", symbol],
    queryFn: () => apiGet<GovernanceResponse>(`/ticker/${symbol}/governance`),
  });

  const { data: ratings, isLoading: ratingsLoading } = useQuery({
    queryKey: ["credit-ratings", symbol],
    queryFn: () => apiGet<CreditRatingsResponse>(`/ticker/${symbol}/credit-ratings`),
  });

  if (govLoading || ratingsLoading) return <SkeletonCard />;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Board of Directors</h2>
          {governance?.board_change_30d && (
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              Board change in last 30 days
            </span>
          )}
        </div>
        {!governance?.board?.length ? (
          <p className="text-sm text-zinc-500">No board data available.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800">
                  <th className="py-2 pr-4">Name</th>
                  <th className="py-2 pr-4">Role</th>
                  <th className="py-2">Appointed</th>
                </tr>
              </thead>
              <tbody>
                {governance.board.map((m) => (
                  <tr key={`${m.name}-${m.role}`} className="border-b border-zinc-100 dark:border-zinc-900">
                    <td className="py-2 pr-4 font-medium">{m.name}</td>
                    <td className="py-2 pr-4 text-zinc-600 dark:text-zinc-400">{m.role}</td>
                    <td className="py-2 tabular-nums">
                      {m.appointment_date
                        ? new Date(m.appointment_date).toLocaleDateString("en-PK")
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {!!governance?.director_changes?.length && (
        <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
          <h2 className="mb-4 text-lg font-semibold">Recent Director Changes</h2>
          <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {governance.director_changes.map((m) => (
              <li key={`${m.name}-chg`} className="py-2 text-sm">
                <span className="font-medium">{m.name}</span> — {m.role}
                {m.resignation_date && (
                  <span className="text-zinc-500">
                    {" "}
                    (resigned {new Date(m.resignation_date).toLocaleDateString("en-PK")})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="mb-4 text-lg font-semibold">Credit Ratings</h2>
        {!ratings?.ratings?.length ? (
          <p className="text-sm text-zinc-500">No credit ratings on file.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800">
                  <th className="py-2 pr-4">Agency</th>
                  <th className="py-2 pr-4">Rating</th>
                  <th className="py-2 pr-4">Outlook</th>
                  <th className="py-2">Effective</th>
                </tr>
              </thead>
              <tbody>
                {ratings.ratings.map((r) => (
                  <tr key={`${r.agency}-${r.effective_date}`} className="border-b border-zinc-100 dark:border-zinc-900">
                    <td className="py-2 pr-4">{r.agency}</td>
                    <td className="py-2 pr-4 font-medium">{r.rating}</td>
                    <td className="py-2 pr-4 capitalize">{r.outlook ?? "—"}</td>
                    <td className="py-2 tabular-nums">
                      {new Date(r.effective_date).toLocaleDateString("en-PK")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {!!governance?.filings?.length && (
        <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
          <h2 className="mb-4 text-lg font-semibold">SECP Filings</h2>
          <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {governance.filings.map((f) => (
              <li key={`${f.form_type}-${f.filed_at}`} className="flex items-center justify-between py-2 text-sm">
                <span>
                  <span className="font-medium">{f.form_type}</span>
                  <span className="ml-2 text-zinc-500">
                    {new Date(f.filed_at).toLocaleDateString("en-PK")}
                  </span>
                </span>
                {f.raw_url && (
                  <a
                    href={f.raw_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sky-600 hover:underline dark:text-sky-400"
                  >
                    PDF
                  </a>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {!!governance?.ccg_checklist?.length && (
        <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
          <h2 className="mb-4 text-lg font-semibold">CCG Checklist</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {governance.ccg_checklist.map((item) => (
              <div
                key={item.item}
                className={`rounded-lg px-3 py-2 text-sm ${
                  item.filed
                    ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                    : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800"
                }`}
              >
                {item.filed ? "✓" : "○"} {item.item}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
