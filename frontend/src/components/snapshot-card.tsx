"use client";

import { useEffect, useState } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { WS_BASE } from "@/lib/api";
import type { SnapshotResponse } from "@/lib/types";
import { cn, formatNumber, formatPct } from "@/lib/utils";

export function SnapshotCard({
  snapshot,
  live,
}: {
  snapshot: SnapshotResponse;
  live?: Partial<SnapshotResponse>;
}) {
  const data = { ...snapshot, ...live };
  const positive = data.change_pct >= 0;
  const rangeLow = data.fifty_two_week_low ?? data.low ?? data.ltp;
  const rangeHigh = data.fifty_two_week_high ?? data.high ?? data.ltp;
  const rangePct =
    rangeHigh > rangeLow ? ((data.ltp - rangeLow) / (rangeHigh - rangeLow)) * 100 : 50;

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold">{data.symbol}</h1>
            <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs dark:bg-zinc-800">{data.sector}</span>
            <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs dark:bg-zinc-800">{data.board}</span>
            {data.trading_halt && (
              <span className="rounded bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700 dark:bg-rose-950 dark:text-rose-300">
                Trading Halt
              </span>
            )}
            {data.circuit_breaker && (
              <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                Circuit Breaker
              </span>
            )}
            {data.board_change_30d && (
              <span className="rounded bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-800 dark:bg-sky-950 dark:text-sky-300">
                Board Change
              </span>
            )}
          </div>
          <p className="text-sm text-zinc-500">{data.name}</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-semibold tabular-nums">Rs {formatNumber(data.ltp)}</div>
          <div className={cn("text-sm font-medium", positive ? "text-emerald-600" : "text-rose-600")}>
            {positive ? "+" : ""}
            {formatNumber(data.change)} ({formatPct(data.change_pct)})
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 text-sm md:grid-cols-4 lg:grid-cols-4">
        <Stat metricId="market_cap" label="Market Cap" value={data.market_cap ? `${(data.market_cap / 1e9).toFixed(2)}B` : "—"} />
        <Stat metricId="volume" label="Volume" value={data.volume?.toLocaleString() ?? "—"} />
        <Stat metricId="vwap" label="VWAP" value={data.vwap != null ? `Rs ${formatNumber(data.vwap)}` : "—"} />
        <Stat metricId="avg_volume_30d" label="Avg Vol 30d" value={data.avg_volume_30d ? Math.round(data.avg_volume_30d).toLocaleString() : "—"} />
        <Stat metricId="shares_outstanding" label="Shares Out" value={data.shares_outstanding?.toLocaleString() ?? "—"} />
        <Stat metricId="pe_ttm" label="P/E TTM" value={data.pe_ttm != null ? formatNumber(data.pe_ttm) : "—"} />
        <Stat metricId="eps_ttm" label="EPS TTM" value={data.eps_ttm != null ? formatNumber(data.eps_ttm) : "—"} />
        <Stat metricId="dividend_yield" label="Div Yield" value={data.dividend_yield != null ? formatPct(data.dividend_yield) : "—"} />
        <Stat metricId="free_float" label="Free Float" value={data.free_float_pct != null ? formatPct(data.free_float_pct) : "—"} />
        <Stat metricId="beta" label="Beta" value={data.beta != null ? formatNumber(data.beta) : "—"} />
        <Stat metricId="return_1m" label="Sector 1M" value={data.sector_return_1m != null ? formatPct(data.sector_return_1m) : "—"} />
      </div>

      {data.next_dividend_ex_date && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm dark:border-emerald-900 dark:bg-emerald-950">
          Next <MetricTooltip metricId="ex_date">ex-dividend</MetricTooltip>: <span className="font-medium">{data.next_dividend_ex_date}</span>
        </div>
      )}

      <div className="mt-4">
        <div className="mb-1 flex justify-between text-xs text-zinc-500">
          <span><MetricTooltip metricId="fifty_two_week_low">52W Low</MetricTooltip> {formatNumber(rangeLow)}</span>
          <span><MetricTooltip metricId="fifty_two_week_high">52W High</MetricTooltip> {formatNumber(rangeHigh)}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
          <div className="h-full rounded-full bg-sky-500" style={{ width: `${Math.min(100, Math.max(0, rangePct))}%` }} />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, metricId }: { label: string; value: string; metricId: string }) {
  return (
    <div>
      <div className="text-xs text-zinc-500">
        <MetricTooltip metricId={metricId}>{label}</MetricTooltip>
      </div>
      <div className="font-medium tabular-nums">{value}</div>
    </div>
  );
}

export function useLiveSnapshot(symbol: string, initial: SnapshotResponse) {
  const [live, setLive] = useState<Partial<SnapshotResponse>>({});

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/prices/${symbol}`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as {
          ltp: number;
          change: number;
          change_pct: number;
          volume?: number;
        };
        setLive({
          ltp: data.ltp,
          change: data.change,
          change_pct: data.change_pct,
          volume: data.volume,
        });
      } catch {
        /* ignore malformed ticks */
      }
    };
    return () => ws.close();
  }, [symbol]);

  return { ...initial, ...live };
}
