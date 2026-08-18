import Link from "next/link";
import type { MoverItem } from "@/lib/types";
import { formatNumber, formatPct } from "@/lib/utils";

export function MoversTable({
  title,
  items,
  positive,
}: {
  title: string;
  items: MoverItem[];
  positive: boolean;
}) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="border-b border-zinc-200 px-4 py-3 font-medium dark:border-zinc-800">{title}</div>
      <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
        {items.length === 0 && (
          <div className="px-4 py-6 text-sm text-zinc-500">No data yet. Run the EOD scraper to populate movers.</div>
        )}
        {items.map((item) => (
          <Link
            key={item.symbol}
            href={`/ticker/${item.symbol}`}
            className="flex items-center justify-between px-4 py-3 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900"
          >
            <div>
              <div className="font-medium">{item.symbol}</div>
              <div className="text-xs text-zinc-500">{item.name}</div>
            </div>
            <div className="text-right">
              <div>Rs {formatNumber(item.ltp)}</div>
              <div className={positive ? "text-emerald-600" : "text-rose-600"}>{formatPct(item.change_pct)}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function SkeletonCard() {
  return <div className="h-40 animate-pulse rounded-xl bg-zinc-200 dark:bg-zinc-800" />;
}
