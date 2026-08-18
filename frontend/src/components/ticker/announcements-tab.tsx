"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import type { AnnouncementListResponse } from "@/lib/types";

const CATEGORIES = [
  { id: "", label: "All" },
  { id: "financial_result", label: "Financial Results" },
  { id: "dividend", label: "Dividends" },
  { id: "insider_trade", label: "Insider Trades" },
  { id: "board_meeting", label: "Board Meetings" },
  { id: "other", label: "Other" },
];

function formatCategory(cat: string) {
  return cat.replace(/_/g, " ");
}

export function AnnouncementsTab({ symbol }: { symbol: string }) {
  const [category, setCategory] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["announcements", symbol, category],
    queryFn: () => {
      const qs = category ? `?category=${category}` : "";
      return apiGet<AnnouncementListResponse>(`/ticker/${symbol}/announcements${qs}`);
    },
  });

  if (isLoading) return <SkeletonCard />;

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-4 text-lg font-semibold">Announcements</h2>
      <div className="mb-4 flex flex-wrap gap-2">
        {CATEGORIES.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => setCategory(c.id)}
            className={`rounded-full px-3 py-1 text-xs ${
              category === c.id
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>
      {!data?.items?.length ? (
        <p className="text-sm text-zinc-500">No announcements yet. Run the announcements backfill.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {data.items.map((item) => (
            <li key={item.id} className="flex flex-wrap items-start justify-between gap-2 py-3">
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                  <time dateTime={item.published_at}>
                    {new Date(item.published_at).toLocaleDateString("en-PK")}
                  </time>
                  <span className="rounded bg-zinc-100 px-2 py-0.5 capitalize dark:bg-zinc-800">
                    {formatCategory(item.category)}
                  </span>
                </div>
                <p className="text-sm font-medium">{item.title}</p>
              </div>
              {item.pdf_url && (
                <a
                  href={item.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 text-xs font-medium text-sky-600 hover:underline dark:text-sky-400"
                >
                  PDF
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
