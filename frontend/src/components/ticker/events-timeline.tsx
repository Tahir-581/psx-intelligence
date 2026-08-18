"use client";

import { useQuery } from "@tanstack/react-query";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import type { MaterialEventListResponse } from "@/lib/types";

function significanceColor(score: number): string {
  if (score >= 4) return "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300";
  if (score >= 3) return "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300";
  return "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400";
}

export function EventsTimeline({ symbol }: { symbol: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["events", symbol],
    queryFn: () => apiGet<MaterialEventListResponse>(`/ticker/${symbol}/events?min_significance=1`),
  });

  if (isLoading) return <SkeletonCard />;

  const items = data?.items ?? [];

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-4 text-lg font-semibold">Material Events</h2>
      {!items.length ? (
        <p className="text-sm text-zinc-500">No material events extracted yet.</p>
      ) : (
        <ol className="relative border-l border-zinc-200 pl-4 dark:border-zinc-700">
          {items.map((event) => (
            <li key={event.id} className="mb-4 ml-2">
              <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-zinc-400 dark:bg-zinc-600" />
              <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                <time dateTime={event.event_date}>
                  {new Date(event.event_date).toLocaleDateString("en-PK")}
                </time>
                <span className="rounded px-2 py-0.5 capitalize">{event.event_type.replace(/_/g, " ")}</span>
                <span className={`rounded px-2 py-0.5 font-medium ${significanceColor(event.significance_score)}`}>
                  {event.significance_score}/5
                </span>
              </div>
              <p className="mt-1 text-sm font-medium">{event.headline}</p>
              {event.summary && (
                <p className="mt-1 text-sm text-zinc-500 line-clamp-2">{event.summary}</p>
              )}
              {event.counterparty && (
                <p className="mt-1 text-xs text-zinc-500">Counterparty: {event.counterparty}</p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
