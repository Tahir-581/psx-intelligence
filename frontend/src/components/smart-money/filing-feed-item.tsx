import Link from "next/link";
import { FilingBadge } from "@/components/smart-money/filing-badge";
import { InvestorAvatar } from "@/components/smart-money/investor-avatar";
import { TickerPill } from "@/components/smart-money/ticker-pill";
import type { SecFiling } from "@/lib/smart-money-types";
import { formatCurrency, formatShortDate } from "@/lib/smart-money-utils";

export function FilingFeedItem({ filing, isNew }: { filing: SecFiling; isNew?: boolean }) {
  const profileHref = filing.investorCik
    ? `/smart-money/investor/${filing.investorCik}`
    : "/smart-money/investors";

  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        isNew
          ? "border-blue-200 bg-blue-50/50 dark:border-blue-900 dark:bg-blue-950/20"
          : "border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <InvestorAvatar initials={filing.avatarInitials} color={filing.avatarColor} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Link href={profileHref} className="text-sm font-medium hover:underline">
                {filing.investorName}
              </Link>
              <FilingBadge formType={filing.formType} />
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
              {filing.ticker ? <TickerPill ticker={filing.ticker} /> : null}
              {filing.companyName ? <span>{filing.companyName}</span> : null}
              <span>{formatShortDate(filing.filedAt)}</span>
            </div>
          </div>
        </div>
        <div className="text-right text-sm font-medium tabular-nums">
          {filing.amount != null
            ? formatCurrency(filing.amount)
            : filing.aum != null
              ? formatCurrency(filing.aum)
              : "—"}
        </div>
      </div>
    </div>
  );
}
