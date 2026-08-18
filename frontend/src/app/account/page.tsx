"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { SkeletonCard } from "@/components/movers-table";
import { useApi } from "@/lib/use-api";
import type { ApiKeyCreateResponse, ApiKeyListResponse } from "@/lib/types";

export default function AccountPage() {
  const { isSignedIn, isLoaded } = useAuth();
  const { get, post, del } = useApi();
  const queryClient = useQueryClient();
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [revealedKey, setRevealedKey] = useState<string | null>(null);

  const keysQuery = useQuery({
    queryKey: ["api-keys", isSignedIn],
    queryFn: () => get<ApiKeyListResponse>("/api-keys"),
    enabled: isSignedIn,
    retry: false,
  });

  const createKey = useMutation({
    mutationFn: (label: string) => post<ApiKeyCreateResponse>("/api-keys", { label }),
    onSuccess: (data) => {
      setRevealedKey(data.key);
      setNewKeyLabel("");
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const revokeKey = useMutation({
    mutationFn: (id: number) => del<void>(`/api-keys/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  if (!isLoaded) {
    return (
      <AppShell>
        <SkeletonCard />
      </AppShell>
    );
  }

  if (!isSignedIn) {
    return (
      <AppShell>
        <p className="text-center text-zinc-500">Sign in to manage your account.</p>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-lg space-y-6">
        <h1 className="text-2xl font-bold">Account</h1>

        <section className="rounded-xl border border-zinc-200 p-6 dark:border-zinc-800">
          <h2 className="font-semibold">API Keys</h2>
          <p className="mt-2 text-sm text-zinc-500">
            Generate keys for programmatic API access.
          </p>

          {keysQuery.isLoading && <SkeletonCard />}

          {keysQuery.data && (
            <ul className="mt-4 space-y-2">
              {keysQuery.data.items.length === 0 ? (
                <li className="text-sm text-zinc-500">No API keys yet.</li>
              ) : (
                keysQuery.data.items.map((k) => (
                  <li
                    key={k.id}
                    className="flex items-center justify-between rounded-lg border border-zinc-100 px-3 py-2 text-sm dark:border-zinc-800"
                  >
                    <div>
                      <span className="font-medium">{k.label}</span>
                      <span className="ml-2 font-mono text-xs text-zinc-500">{k.key_prefix}…</span>
                      <p className="text-xs text-zinc-400">
                        Created {new Date(k.created_at).toLocaleDateString("en-PK")}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => revokeKey.mutate(k.id)}
                      className="text-xs text-rose-600 hover:underline"
                    >
                      Revoke
                    </button>
                  </li>
                ))
              )}
            </ul>
          )}

          <div className="mt-4 flex gap-2">
            <input
              className="flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              placeholder="Key label (e.g. My script)"
              value={newKeyLabel}
              onChange={(e) => setNewKeyLabel(e.target.value)}
            />
            <button
              type="button"
              disabled={!newKeyLabel.trim() || createKey.isPending}
              onClick={() => createKey.mutate(newKeyLabel.trim())}
              className="rounded-lg bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
            >
              Generate
            </button>
          </div>

          {revealedKey && (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/40">
              <p className="font-medium text-amber-800 dark:text-amber-200">
                Copy your key now — it won&apos;t be shown again.
              </p>
              <code className="mt-2 block break-all font-mono text-xs">{revealedKey}</code>
              <button
                type="button"
                onClick={() => setRevealedKey(null)}
                className="mt-2 text-xs text-zinc-500 hover:underline"
              >
                Dismiss
              </button>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
