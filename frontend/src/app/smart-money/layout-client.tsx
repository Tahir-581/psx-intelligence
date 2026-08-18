"use client";

import { AppShell } from "@/components/app-shell";
import { SmartMoneyNav } from "@/components/smart-money/smart-money-nav";

export function SmartMoneyLayoutClient({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <div>
        <div className="mb-4">
          <h1 className="text-2xl font-semibold tracking-tight">US Smart Money</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            SEC Form 13F institutional investors, hedge funds, and insider filings
          </p>
        </div>
        <SmartMoneyNav />
        {children}
      </div>
    </AppShell>
  );
}
