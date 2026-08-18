"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SkeletonCard } from "@/components/movers-table";
import { useApi } from "@/lib/use-api";
import type { AiSummaryResponse } from "@/lib/types";

export function AiSummaryCard({ symbol }: { symbol: string }) {
  const { get, post, isSignedIn } = useApi();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["summary", symbol, isSignedIn],
    queryFn: () => get<AiSummaryResponse>(`/ticker/${symbol}/summary`),
    enabled: isSignedIn,
    retry: false,
  });

  const refreshMutation = useMutation({
    mutationFn: () => post<AiSummaryResponse>(`/ticker/${symbol}/summary/refresh`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["summary", symbol] }),
  });

  if (isLoading && isSignedIn) return <SkeletonCard />;

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">AI Company Brief</h2>
        {isSignedIn && (
          <button
            type="button"
            disabled={refreshMutation.isPending}
            onClick={() => refreshMutation.mutate()}
            className="rounded-lg border border-zinc-200 px-3 py-1 text-xs font-medium hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
          >
            {refreshMutation.isPending ? "Refreshing…" : "Refresh summary"}
          </button>
        )}
      </div>
      {!isSignedIn ? (
        <p className="text-sm text-zinc-500">Sign in to view the AI company brief.</p>
      ) : (
        <>
          <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
            {data?.content ?? "Weekly AI-generated summary will appear here once available."}
          </p>
          {refreshMutation.isError && (
            <p className="mt-2 text-xs text-rose-600">
              Refresh failed — limited to once per 24 hours per ticker.
            </p>
          )}
          {data?.generated_at && (
            <p className="mt-2 text-xs text-zinc-500">
              Updated {new Date(data.generated_at).toLocaleDateString("en-PK")}
            </p>
          )}
        </>
      )}
    </section>
  );
}
