"use client";

import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/use-api";
import type { NotificationListResponse } from "@/lib/types";

export function NotificationBell() {
  const { get, post, isSignedIn } = useApi();
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["notifications", isSignedIn],
    queryFn: () =>
      get<NotificationListResponse>("/notifications?unread_only=true&page_size=10"),
    enabled: isSignedIn,
    refetchInterval: 60_000,
  });

  const markAll = useMutation({
    mutationFn: () => post<void>("/notifications/read-all"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  if (!isSignedIn) return null;

  const unread = data?.unread_count ?? 0;

  return (
    <div className="relative group">
      <button
        type="button"
        className="relative rounded-lg p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800"
        aria-label="Notifications"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.6 6.6 0 00-5-6.517V4a2 2 0 10-4 0v.483A6.6 6.6 0 004 11v3.159c0 .538-.214 1.055-.595 1.436L2 17h5m8 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      <div className="invisible absolute right-0 z-50 mt-1 w-80 rounded-xl border border-zinc-200 bg-white opacity-0 shadow-lg transition-all group-hover:visible group-hover:opacity-100 dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-2 dark:border-zinc-800">
          <span className="text-sm font-medium">Notifications</span>
          {unread > 0 && (
            <button
              type="button"
              onClick={() => markAll.mutate()}
              className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
            >
              Mark all read
            </button>
          )}
        </div>
        <ul className="max-h-64 overflow-y-auto">
          {(data?.items ?? []).length === 0 ? (
            <li className="px-4 py-6 text-center text-sm text-zinc-500">No unread notifications</li>
          ) : (
            data?.items.map((n) => (
              <li key={n.id} className="border-b border-zinc-100 px-4 py-3 last:border-0 dark:border-zinc-900">
                {n.link_url ? (
                  <Link href={n.link_url} className="block hover:opacity-80">
                    <p className="text-sm font-medium">{n.title}</p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-zinc-500">{n.body}</p>
                  </Link>
                ) : (
                  <>
                    <p className="text-sm font-medium">{n.title}</p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-zinc-500">{n.body}</p>
                  </>
                )}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
