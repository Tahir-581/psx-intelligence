"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { SkeletonCard } from "@/components/movers-table";
import { useApi } from "@/lib/use-api";
import type { NotificationPrefsResponse } from "@/lib/types";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const arr = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
  return arr;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]!);
  return btoa(binary);
}

export default function NotificationsPage() {
  const { isSignedIn, isLoaded } = useAuth();
  const { get, patch, post } = useApi();
  const queryClient = useQueryClient();
  const [pushStatus, setPushStatus] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["notification-prefs", isSignedIn],
    queryFn: () => get<NotificationPrefsResponse>("/notifications/preferences"),
    enabled: isSignedIn,
  });

  const updatePrefs = useMutation({
    mutationFn: (body: Partial<NotificationPrefsResponse>) =>
      patch<NotificationPrefsResponse>("/notifications/preferences", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notification-prefs"] }),
  });

  const subscribePush = async () => {
    const vapidKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
    if (!vapidKey) {
      setPushStatus("Push notifications are not configured on this deployment.");
      return;
    }
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      setPushStatus("Push is not supported in this browser.");
      return;
    }

    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setPushStatus("Notification permission denied.");
        return;
      }

      const reg = await navigator.serviceWorker.ready;
      let sub = await reg.pushManager.getSubscription();
      if (!sub) {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidKey) as BufferSource,
        });
      }

      const p256dhKey = sub.getKey("p256dh");
      const authKey = sub.getKey("auth");
      if (!p256dhKey || !authKey) throw new Error("Invalid push subscription keys");

      await post<void>("/notifications/push-subscribe", {
        endpoint: sub.endpoint,
        p256dh: arrayBufferToBase64(p256dhKey),
        auth: arrayBufferToBase64(authKey),
      });

      await updatePrefs.mutateAsync({ push_enabled: true });
      setPushStatus("Push notifications enabled.");
    } catch {
      setPushStatus("Failed to enable push notifications.");
    }
  };

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
        <p className="text-center text-zinc-500">Sign in to manage notification preferences.</p>
      </AppShell>
    );
  }

  const toggle = (field: keyof NotificationPrefsResponse, value: boolean) => {
    updatePrefs.mutate({ [field]: value });
    if (field === "push_enabled" && value) void subscribePush();
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-lg space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Notification Preferences</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Choose how you receive alerts, digests, and market updates.
          </p>
        </div>

        {isLoading && <SkeletonCard />}

        {data && (
          <section className="space-y-4 rounded-xl border border-zinc-200 p-6 dark:border-zinc-800">
            {(
              [
                ["email_enabled", "Email notifications", "Price alerts and account updates via email."],
                ["push_enabled", "Push notifications", "Browser push for time-sensitive alerts."],
                ["digest_enabled", "Weekly digest", "Summary of watchlist and portfolio activity."],
                ["whatsapp_enabled", "WhatsApp", "Alerts via WhatsApp (requires phone number)."],
              ] as const
            ).map(([field, label, hint]) => (
              <label
                key={field}
                className="flex cursor-pointer items-start justify-between gap-4 border-b border-zinc-100 pb-4 last:border-0 last:pb-0 dark:border-zinc-900"
              >
                <div>
                  <span className="text-sm font-medium">{label}</span>
                  <p className="mt-0.5 text-xs text-zinc-500">{hint}</p>
                </div>
                <input
                  type="checkbox"
                  checked={!!data[field]}
                  onChange={(e) => toggle(field, e.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-zinc-300"
                />
              </label>
            ))}

            {data.whatsapp_enabled && (
              <div>
                <label className="block text-xs text-zinc-500">WhatsApp number</label>
                <input
                  type="tel"
                  className="mt-1 w-full rounded-lg border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
                  placeholder="+92..."
                  defaultValue={data.whatsapp_number ?? ""}
                  onBlur={(e) => {
                    const val = e.target.value.trim();
                    if (val !== (data.whatsapp_number ?? "")) {
                      updatePrefs.mutate({ whatsapp_number: val || null });
                    }
                  }}
                />
              </div>
            )}

            {pushStatus && <p className="text-xs text-zinc-500">{pushStatus}</p>}
          </section>
        )}
      </div>
    </AppShell>
  );
}
