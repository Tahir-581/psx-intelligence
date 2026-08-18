"use client";

import { useQuery } from "@tanstack/react-query";
import { SkeletonCard } from "@/components/movers-table";
import { useApi } from "@/lib/use-api";
import type { SocialFeedResponse } from "@/lib/types";

export function SocialTab({ symbol }: { symbol: string }) {
  const { get, isSignedIn } = useApi();
  const { data, isLoading } = useQuery({
    queryKey: ["social", symbol, isSignedIn],
    queryFn: () => get<SocialFeedResponse>(`/ticker/${symbol}/social?days=30`),
    enabled: isSignedIn,
    retry: false,
  });

  if (isLoading && isSignedIn) return <SkeletonCard />;

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-4 text-lg font-semibold">Social Feed</h2>
      {!isSignedIn ? (
        <p className="text-sm text-zinc-500">Sign in to view the social feed.</p>
      ) : !data?.items?.length ? (
        <p className="text-sm text-zinc-500">No linked social posts in the last 30 days.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {data.items.map((post) => (
            <li key={post.id} className="py-3">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                <span className="rounded bg-zinc-100 px-2 py-0.5 capitalize dark:bg-zinc-800">
                  {post.source}
                </span>
                {post.author_handle && <span>@{post.author_handle}</span>}
                <time dateTime={post.posted_at}>
                  {new Date(post.posted_at).toLocaleDateString("en-PK")}
                </time>
              </div>
              <p className="text-sm">{post.text}</p>
              {post.url && (
                <a
                  href={post.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 inline-block text-xs text-sky-600 hover:underline dark:text-sky-400"
                >
                  View post →
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
