"use client";

import { useEffect, useState } from "react";
import {
  DEFAULT_ALERTS,
  loadAlerts,
  saveAlerts,
  type AlertRecord,
} from "@/lib/sec-alerts";

export default function SmartMoneyAlertsPage() {
  const [alerts, setAlerts] = useState<AlertRecord[]>(DEFAULT_ALERTS);

  useEffect(() => {
    setAlerts(loadAlerts());
  }, []);

  const toggle = (id: string) => {
    const next = alerts.map((a) => (a.id === id ? { ...a, active: !a.active } : a));
    setAlerts(next);
    saveAlerts(next);
  };

  return (
    <div>
      <h2 className="mb-2 text-sm font-medium">SEC filing alerts</h2>
      <p className="mb-4 text-xs text-zinc-500">
        Stored locally in your browser. Server-side alert delivery is not yet wired for SEC filings.
      </p>
      <div className="space-y-3">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className="flex items-start justify-between gap-4 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
          >
            <div>
              <div className="text-sm font-medium">{alert.name}</div>
              {alert.description ? (
                <p className="mt-1 text-xs text-zinc-500">{alert.description}</p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => toggle(alert.id)}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                alert.active
                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                  : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800"
              }`}
            >
              {alert.active ? "On" : "Off"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
