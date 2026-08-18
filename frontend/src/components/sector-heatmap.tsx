"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { SectorDetailPanel } from "@/components/sector-detail-panel";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import type { SectorStatsResponse } from "@/lib/types";
import { formatPct } from "@/lib/utils";

type RangeKey = "1d" | "1w" | "1m" | "ytd";

const RANGES: { id: RangeKey; label: string }[] = [
  { id: "1d", label: "1D" },
  { id: "1w", label: "1W" },
  { id: "1m", label: "1M" },
  { id: "ytd", label: "YTD" },
];

function returnForRange(
  sector: SectorStatsResponse["sectors"][0],
  range: RangeKey,
): number | null {
  if (range === "1d") return sector.return_1d ?? null;
  if (range === "1w") return sector.return_1w ?? null;
  if (range === "1m") return sector.return_1m ?? null;
  return sector.return_ytd ?? null;
}

function heatColor(pct: number | null): string {
  if (pct == null) return "bg-zinc-200 dark:bg-zinc-800";
  if (pct > 2) return "bg-emerald-500";
  if (pct > 0) return "bg-emerald-300 dark:bg-emerald-700";
  if (pct < -2) return "bg-rose-500";
  if (pct < 0) return "bg-rose-300 dark:bg-rose-700";
  return "bg-zinc-300 dark:bg-zinc-700";
}

export function SectorHeatmap() {
  const [range, setRange] = useState<RangeKey>("1d");
  const [selectedSector, setSelectedSector] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["sector-stats", range],
    queryFn: () => apiGet<SectorStatsResponse>(`/market/sectors?range=${range}`),
    refetchInterval: 300_000,
  });

  if (isLoading) return <SkeletonCard />;

  const sectors = data?.sectors ?? [];
  const maxCap = Math.max(...sectors.map((s) => s.total_market_cap ?? 0), 1);

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">Sector Heatmap</h2>
          <p className="text-sm text-zinc-500">
            {selectedSector
              ? "Company financials for selected sector"
              : "Sized by market cap, colored by return"}
          </p>
        </div>
        <div className="flex gap-2">
          {RANGES.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => setRange(r.id)}
              className={`rounded-md px-3 py-1 text-xs ${
                range === r.id
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "bg-zinc-100 text-zinc-700 dark:bg-zinc-800"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {selectedSector ? (
        <SectorDetailPanel
          sector={selectedSector}
          range={range}
          onBack={() => setSelectedSector(null)}
        />
      ) : !sectors.length ? (
        <p className="text-sm text-zinc-500">Sector stats not populated yet. Run refresh_sector_stats.</p>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {sectors.map((sector) => {
            const ret = returnForRange(sector, range);
            const flex = Math.max(1, Math.round(((sector.total_market_cap ?? 0) / maxCap) * 3));
            return (
              <button
                key={sector.sector}
                type="button"
                onClick={() => setSelectedSector(sector.sector)}
                className={`rounded-lg p-3 text-left text-white transition hover:opacity-90 ${heatColor(ret)}`}
                style={{ gridRow: `span ${flex}` }}
              >
                <div className="text-xs font-medium opacity-90 line-clamp-2">{sector.sector}</div>
                <div className="mt-1 text-lg font-semibold tabular-nums">
                  {ret != null ? formatPct(ret) : "—"}
                </div>
                <div className="text-[10px] opacity-80">{sector.company_count} cos</div>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
