"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download } from "lucide-react";
import { useMemo, useState } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import type { SectorCompanyRow, SectorDetailResponse, SectorStatsItem } from "@/lib/types";
import { cn, formatNumber, formatPct } from "@/lib/utils";

type RangeKey = "1d" | "1w" | "1m" | "ytd";

const RANGE_LABELS: Record<RangeKey, string> = {
  "1d": "1D",
  "1w": "1W",
  "1m": "1M",
  ytd: "YTD",
};

type SortKey =
  | "symbol"
  | "ltp"
  | "change_pct"
  | "market_cap"
  | "pe_ttm"
  | "eps_ttm"
  | "dividend_yield"
  | "roe"
  | "roa"
  | "debt_to_equity"
  | "beta"
  | "return_range"
  | "revenue"
  | "pat";

function sectorReturn(stats: SectorStatsItem | null | undefined, range: RangeKey): number | null {
  if (!stats) return null;
  if (range === "1d") return stats.return_1d ?? null;
  if (range === "1w") return stats.return_1w ?? null;
  if (range === "1m") return stats.return_1m ?? null;
  return stats.return_ytd ?? null;
}

function formatBn(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value / 1_000_000_000).toFixed(2)} B`;
}

function formatMn(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value / 1_000_000).toFixed(1)} M`;
}

function sortValue(row: SectorCompanyRow, key: SortKey): number | string {
  if (key === "symbol") return row.symbol;
  if (key === "revenue") return row.financials.revenue ?? -Infinity;
  if (key === "pat") return row.financials.pat ?? -Infinity;
  return (row[key] as number | null | undefined) ?? -Infinity;
}

function exportCsv(companies: SectorCompanyRow[], sector: string, range: RangeKey) {
  const headers = [
    "symbol",
    "name",
    "ltp",
    "change_pct",
    "market_cap",
    "pe_ttm",
    "eps_ttm",
    "dividend_yield",
    "roe",
    "roa",
    "gross_margin",
    "ebitda_margin",
    "net_margin",
    "debt_to_equity",
    "current_ratio",
    "beta",
    `return_${range}`,
    "revenue",
    "gross_profit",
    "ebitda",
    "pat",
    "total_assets",
    "total_equity",
    "total_debt",
    "ocf",
    "capex",
    "period_end",
  ];
  const rows = companies.map((c) => [
    c.symbol,
    c.name,
    c.ltp ?? "",
    c.change_pct ?? "",
    c.market_cap ?? "",
    c.pe_ttm ?? "",
    c.eps_ttm ?? "",
    c.dividend_yield ?? "",
    c.roe ?? "",
    c.roa ?? "",
    c.gross_margin ?? "",
    c.ebitda_margin ?? "",
    c.net_margin ?? "",
    c.debt_to_equity ?? "",
    c.current_ratio ?? "",
    c.beta ?? "",
    c.return_range ?? "",
    c.financials.revenue ?? "",
    c.financials.gross_profit ?? "",
    c.financials.ebitda ?? "",
    c.financials.pat ?? "",
    c.financials.total_assets ?? "",
    c.financials.total_equity ?? "",
    c.financials.total_debt ?? "",
    c.financials.ocf ?? "",
    c.financials.capex ?? "",
    c.financials.period_end ?? "",
  ]);
  const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${sector.replace(/\s+/g, "_")}-${range}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function Th({
  label,
  metricId,
  sortKey,
  active,
  dir,
  onSort,
  className,
}: {
  label: string;
  metricId?: string;
  sortKey: SortKey;
  active: boolean;
  dir: "asc" | "desc";
  onSort: (key: SortKey) => void;
  className?: string;
}) {
  return (
    <th
      className={cn(
        "cursor-pointer whitespace-nowrap px-3 py-2 font-medium hover:text-zinc-900 dark:hover:text-zinc-100",
        className,
      )}
      onClick={() => onSort(sortKey)}
    >
      <MetricTooltip metricId={metricId}>{label}</MetricTooltip>
      {active ? (dir === "asc" ? " ↑" : " ↓") : ""}
    </th>
  );
}

function MetricHeader({ label, metricId, className }: { label: string; metricId: string; className?: string }) {
  return (
    <th className={cn("whitespace-nowrap px-3 py-2 font-medium", className)}>
      <MetricTooltip metricId={metricId}>{label}</MetricTooltip>
    </th>
  );
}

export function SectorDetailPanel({
  sector,
  range,
  onBack,
}: {
  sector: string;
  range: RangeKey;
  onBack: () => void;
}) {
  const [sortBy, setSortBy] = useState<SortKey>("market_cap");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const { data, isLoading, error } = useQuery({
    queryKey: ["sector-detail", sector, range],
    queryFn: () =>
      apiGet<SectorDetailResponse>(
        `/market/sectors/${encodeURIComponent(sector)}/detail?range=${range}`,
      ),
    refetchInterval: 300_000,
  });

  const sorted = useMemo(() => {
    const items = [...(data?.companies ?? [])];
    items.sort((a, b) => {
      const av = sortValue(a, sortBy);
      const bv = sortValue(b, sortBy);
      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      const an = av as number;
      const bn = bv as number;
      return sortDir === "asc" ? an - bn : bn - an;
    });
    return items;
  }, [data?.companies, sortBy, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("desc");
    }
  };

  const ret = sectorReturn(data?.stats, range);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <div>
            <h2 className="text-lg font-semibold">{sector}</h2>
            <p className="text-sm text-zinc-500">
              {data?.companies.length ?? 0} companies · {RANGE_LABELS[range]} return{" "}
              {ret != null ? formatPct(ret) : "—"}
            </p>
          </div>
        </div>
        {sorted.length > 0 && (
          <button
            type="button"
            onClick={() => exportCsv(sorted, sector, range)}
            className="flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        )}
      </div>

      {data?.stats && (
        <div className="mb-4 grid grid-cols-2 gap-2 text-center text-sm sm:grid-cols-4">
          <div className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
            <div className="font-semibold tabular-nums">{formatBn(data.stats.total_market_cap)}</div>
            <div className="text-zinc-500">
              <MetricTooltip metricId="market_cap">Total Mkt Cap</MetricTooltip>
            </div>
          </div>
          <div className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
            <div className="font-semibold tabular-nums">
              {data.stats.median_pe != null ? formatNumber(data.stats.median_pe, 1) : "—"}
            </div>
            <div className="text-zinc-500">
              <MetricTooltip metricId="median_pe">Median P/E</MetricTooltip>
            </div>
          </div>
          <div className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
            <div className="font-semibold tabular-nums">
              {data.stats.median_dividend_yield != null
                ? `${formatNumber(data.stats.median_dividend_yield, 2)}%`
                : "—"}
            </div>
            <div className="text-zinc-500">
              <MetricTooltip metricId="median_dividend_yield">Median Div %</MetricTooltip>
            </div>
          </div>
          <div className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
            <div className="text-xs font-medium">
              {data.stats.top_gainer_symbol && (
                <span className="text-emerald-600">{data.stats.top_gainer_symbol}</span>
              )}
              {data.stats.top_gainer_symbol && data.stats.top_loser_symbol && " / "}
              {data.stats.top_loser_symbol && (
                <span className="text-rose-600">{data.stats.top_loser_symbol}</span>
              )}
              {!data.stats.top_gainer_symbol && !data.stats.top_loser_symbol && "—"}
            </div>
            <div className="text-zinc-500">
              <MetricTooltip metricId="top_gainer_loser">Top gainer / loser</MetricTooltip>
            </div>
          </div>
        </div>
      )}

      {isLoading && <SkeletonCard />}
      {error && (
        <p className="text-sm text-rose-600">
          {(error as Error).message || "Failed to load sector detail"}
        </p>
      )}

      {!isLoading && data && data.companies.length === 0 && (
        <p className="text-sm text-zinc-500">No companies found in this sector.</p>
      )}

      {sorted.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-zinc-200 bg-zinc-50 text-left text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/50">
                <Th
                  label="Symbol"
                  sortKey="symbol"
                  active={sortBy === "symbol"}
                  dir={sortDir}
                  onSort={handleSort}
                  className="sticky left-0 z-10 bg-zinc-50 dark:bg-zinc-900/50"
                />
                <th className="sticky left-[4.5rem] z-10 whitespace-nowrap bg-zinc-50 px-3 py-2 font-medium dark:bg-zinc-900/50">
                  Name
                </th>
                <Th label="LTP" metricId="ltp" sortKey="ltp" active={sortBy === "ltp"} dir={sortDir} onSort={handleSort} />
                <Th
                  label="Chg %"
                  metricId="change_pct"
                  sortKey="change_pct"
                  active={sortBy === "change_pct"}
                  dir={sortDir}
                  onSort={handleSort}
                />
                <Th
                  label="Mkt Cap"
                  metricId="market_cap"
                  sortKey="market_cap"
                  active={sortBy === "market_cap"}
                  dir={sortDir}
                  onSort={handleSort}
                />
                <Th label="P/E" metricId="pe_ttm" sortKey="pe_ttm" active={sortBy === "pe_ttm"} dir={sortDir} onSort={handleSort} />
                <Th label="EPS" metricId="eps_ttm" sortKey="eps_ttm" active={sortBy === "eps_ttm"} dir={sortDir} onSort={handleSort} />
                <Th
                  label="Div %"
                  metricId="dividend_yield"
                  sortKey="dividend_yield"
                  active={sortBy === "dividend_yield"}
                  dir={sortDir}
                  onSort={handleSort}
                />
                <Th label="ROE" metricId="roe" sortKey="roe" active={sortBy === "roe"} dir={sortDir} onSort={handleSort} />
                <Th label="ROA" metricId="roa" sortKey="roa" active={sortBy === "roa"} dir={sortDir} onSort={handleSort} />
                <Th
                  label="D/E"
                  metricId="debt_to_equity"
                  sortKey="debt_to_equity"
                  active={sortBy === "debt_to_equity"}
                  dir={sortDir}
                  onSort={handleSort}
                />
                <Th label="Beta" metricId="beta" sortKey="beta" active={sortBy === "beta"} dir={sortDir} onSort={handleSort} />
                <Th
                  label={`Ret ${RANGE_LABELS[range]}`}
                  metricId={range === "1d" ? "return_1d" : range === "1w" ? "return_1w" : range === "1m" ? "return_1m" : "return_ytd"}
                  sortKey="return_range"
                  active={sortBy === "return_range"}
                  dir={sortDir}
                  onSort={handleSort}
                />
                <Th
                  label="Revenue"
                  metricId="revenue"
                  sortKey="revenue"
                  active={sortBy === "revenue"}
                  dir={sortDir}
                  onSort={handleSort}
                />
                <MetricHeader label="Gross Profit" metricId="gross_profit" />
                <MetricHeader label="EBITDA" metricId="ebitda" />
                <Th label="PAT" metricId="pat" sortKey="pat" active={sortBy === "pat"} dir={sortDir} onSort={handleSort} />
                <MetricHeader label="Assets" metricId="total_assets" />
                <MetricHeader label="Equity" metricId="total_equity" />
                <MetricHeader label="Debt" metricId="total_debt" />
                <MetricHeader label="OCF" metricId="ocf" />
                <MetricHeader label="Capex" metricId="capex" />
                <MetricHeader label="Period" metricId="period_end" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr
                  key={row.symbol}
                  className="border-b border-zinc-100 hover:bg-zinc-50 dark:border-zinc-900 dark:hover:bg-zinc-900/50"
                >
                  <td className="sticky left-0 z-10 bg-white px-3 py-2 font-medium dark:bg-zinc-950">
                    <Link href={`/ticker/${row.symbol}`} className="hover:underline">
                      {row.symbol}
                    </Link>
                  </td>
                  <td className="sticky left-[4.5rem] z-10 max-w-[8rem] truncate bg-white px-3 py-2 text-zinc-500 dark:bg-zinc-950">
                    {row.name}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{formatNumber(row.ltp)}</td>
                  <td
                    className={cn(
                      "px-3 py-2 tabular-nums",
                      row.change_pct != null && row.change_pct >= 0
                        ? "text-emerald-600"
                        : "text-rose-600",
                    )}
                  >
                    {row.change_pct != null ? formatPct(row.change_pct) : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{formatBn(row.market_cap)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatNumber(row.pe_ttm, 1)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatNumber(row.eps_ttm, 2)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatNumber(row.dividend_yield, 2)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatNumber(row.roe, 1)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatNumber(row.roa, 1)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatNumber(row.debt_to_equity, 2)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatNumber(row.beta, 2)}</td>
                  <td
                    className={cn(
                      "px-3 py-2 tabular-nums",
                      row.return_range != null && row.return_range >= 0
                        ? "text-emerald-600"
                        : "text-rose-600",
                    )}
                  >
                    {row.return_range != null ? formatPct(row.return_range) : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{formatMn(row.financials.revenue)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatMn(row.financials.gross_profit)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatMn(row.financials.ebitda)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatMn(row.financials.pat)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatMn(row.financials.total_assets)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatMn(row.financials.total_equity)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatMn(row.financials.total_debt)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatMn(row.financials.ocf)}</td>
                  <td className="px-3 py-2 tabular-nums">{formatMn(row.financials.capex)}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-zinc-500">
                    {row.financials.period_end ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
