"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Suspense, useMemo, useState } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { AppShell } from "@/components/app-shell";
import { SkeletonCard } from "@/components/movers-table";
import { getMetricLabel } from "@/lib/metric-glossary";
import { apiGet } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { CompareResponse } from "@/lib/types";

const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444"];

function normalizeRatioValues(
  ratios: CompareResponse["ratios"],
  symbols: string[],
): { labels: string[]; series: { symbol: string; values: number[] }[] } {
  const labels = ratios.map((r) => r.ratio_code);
  const series = symbols.map((sym) => {
    const values = ratios.map((r) => {
      const raw = r.values[sym];
      if (raw == null || Number.isNaN(raw)) return 0;
      const all = symbols
        .map((s) => r.values[s])
        .filter((v): v is number => v != null && !Number.isNaN(v));
      if (all.length === 0) return 0;
      const min = Math.min(...all);
      const max = Math.max(...all);
      if (max === min) return 0.5;
      return (raw - min) / (max - min);
    });
    return { symbol: sym, values };
  });
  return { labels, series };
}

function CompareRadarChart({ data }: { data: CompareResponse }) {
  const { labels, series } = normalizeRatioValues(data.ratios, data.symbols);
  if (labels.length < 3) return null;

  const cx = 200;
  const cy = 200;
  const maxR = 140;
  const n = labels.length;

  const axisPoint = (i: number, scale: number) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    return {
      x: cx + Math.cos(angle) * maxR * scale,
      y: cy + Math.sin(angle) * maxR * scale,
    };
  };

  const polygonPath = (values: number[]) =>
    values
      .map((v, i) => {
        const p = axisPoint(i, v);
        return `${i === 0 ? "M" : "L"}${p.x},${p.y}`;
      })
      .join(" ") + " Z";

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-4 text-sm font-medium">Multi-metric radar</h2>
      <div className="flex flex-col items-center gap-4 lg:flex-row lg:items-start lg:justify-center">
        <svg viewBox="0 0 400 400" className="h-72 w-72 shrink-0">
          {[0.25, 0.5, 0.75, 1].map((scale) => (
            <polygon
              key={scale}
              points={Array.from({ length: n }, (_, i) => {
                const p = axisPoint(i, scale);
                return `${p.x},${p.y}`;
              }).join(" ")}
              fill="none"
              stroke="currentColor"
              strokeOpacity={0.12}
            />
          ))}
          {labels.map((label, i) => {
            const outer = axisPoint(i, 1);
            const labelPt = axisPoint(i, 1.12);
            return (
              <g key={label}>
                <line
                  x1={cx}
                  y1={cy}
                  x2={outer.x}
                  y2={outer.y}
                  stroke="currentColor"
                  strokeOpacity={0.15}
                />
                <text
                  x={labelPt.x}
                  y={labelPt.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={9}
                  fill="currentColor"
                  opacity={0.7}
                >
                  {label}
                </text>
              </g>
            );
          })}
          {series.map((s, idx) => (
            <path
              key={s.symbol}
              d={polygonPath(s.values)}
              fill={COLORS[idx % 4]}
              fillOpacity={0.15}
              stroke={COLORS[idx % 4]}
              strokeWidth={2}
            />
          ))}
        </svg>
        <ul className="flex flex-wrap justify-center gap-3 text-xs lg:flex-col">
          {series.map((s, idx) => (
            <li key={s.symbol} className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: COLORS[idx % 4] }}
              />
              <Link href={`/ticker/${s.symbol}`} className="font-medium hover:underline">
                {s.symbol}
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <p className="mt-2 text-center text-xs text-zinc-500">
        Values min–max normalized per metric for visual comparison.
      </p>
    </div>
  );
}

function CompareContent() {
  const searchParams = useSearchParams();
  const initial = searchParams.get("symbols") ?? "ENGRO,LUCK";
  const [input, setInput] = useState(initial);
  const { get, isSignedIn } = useApi();

  const symbols = useMemo(
    () =>
      input
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean),
    [input]
  );

  const { data, isLoading, error } = useQuery({
    queryKey: ["compare", symbols.join(","), isSignedIn],
    queryFn: () => {
      const fn = isSignedIn ? get : apiGet;
      return fn<CompareResponse>(`/compare?symbols=${symbols.join(",")}`);
    },
    enabled: symbols.length >= 2,
    retry: false,
  });

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Compare Tickers</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Compare up to 4 tickers. Normalized performance from common base date.
        </p>
      </div>

      <div className="mb-4 flex gap-2">
        <input
          className="flex-1 rounded-xl border border-zinc-200 bg-white px-4 py-2 text-sm dark:border-zinc-800 dark:bg-zinc-950"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="ENGRO,LUCK,HBL"
        />
      </div>

      {symbols.length < 2 && (
        <p className="text-sm text-zinc-500">Enter at least 2 comma-separated symbols.</p>
      )}

      {isLoading && <SkeletonCard />}
      {error && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/30">
          Compare failed — check symbol count (Free max 2) or symbol names.
        </p>
      )}

      {data && (
        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
            <h2 className="mb-4 text-sm font-medium">Normalized performance</h2>
            <div className="h-64 overflow-x-auto">
              <svg viewBox="0 0 800 200" className="h-full w-full min-w-[600px]">
                {data.series.map((s, idx) => {
                  const pts = s.points;
                  if (pts.length < 2) return null;
                  const xs = pts.map((_, i) => (i / (pts.length - 1)) * 780 + 10);
                  const ys = pts.map((p) => 190 - (p.value / 150) * 170);
                  const d = pts.map((_, i) => `${i === 0 ? "M" : "L"}${xs[i]},${ys[i]}`).join(" ");
                  return (
                    <g key={s.symbol}>
                      <path d={d} fill="none" stroke={COLORS[idx % 4]} strokeWidth={2} />
                      <text x={xs[xs.length - 1]} y={ys[ys.length - 1]! - 6} fontSize={10} fill={COLORS[idx % 4]}>
                        {s.symbol}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>

          <CompareRadarChart data={data} />

          <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-left dark:border-zinc-800">
                  <th className="px-4 py-3">Ratio</th>
                  {data.symbols.map((s) => (
                    <th key={s} className="px-4 py-3">
                      <Link href={`/ticker/${s}`} className="hover:underline">
                        {s}
                      </Link>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.ratios.map((r) => (
                  <tr key={r.ratio_code} className="border-b border-zinc-100 dark:border-zinc-900">
                    <td className="px-4 py-2 font-medium">
                      <MetricTooltip metricId={r.ratio_code}>{getMetricLabel(r.ratio_code)}</MetricTooltip>
                    </td>
                    {data.symbols.map((s) => (
                      <td key={s} className="px-4 py-2 tabular-nums">
                        {r.values[s]?.toFixed(2) ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<AppShell><SkeletonCard /></AppShell>}>
      <CompareContent />
    </Suspense>
  );
}
