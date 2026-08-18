export function TickerPill({ ticker }: { ticker: string }) {
  return (
    <span className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[11px] font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
      {ticker}
    </span>
  );
}
