"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Suspense, useEffect, useMemo, useState } from "react";
import { MetricTooltip } from "@/components/metric-tooltip";
import { AppShell } from "@/components/app-shell";
import { SkeletonCard } from "@/components/movers-table";
import { useApi } from "@/lib/use-api";
import type { ScreenerFilters, ScreenerPresetListResponse, ScreenerResponse } from "@/lib/types";

const SECTOR_OPTIONS = [
  "Commercial Banks",
  "Cement",
  "Chemical",
  "Oil & Gas Exploration Companies",
  "Oil & Gas Marketing Companies",
  "Power Generation & Distribution",
  "Technology & Communication",
  "Textile Composite",
  "Food & Personal Care Products",
];

const BOARD_OPTIONS = ["REG", "TFC", "ODT", "BATS"];
const INDEX_OPTIONS = ["KSE100", "KSE30", "KMI30", "KMIALL"];

function countFilterGroups(f: ScreenerFilters): number {
  let n = 0;
  if (f.sectors?.length || f.boards?.length || f.index_membership?.length) n++;
  if (f.market_cap_min_bn != null || f.market_cap_max_bn != null) n++;
  if (
    f.pe_min != null ||
    f.pe_max != null ||
    f.pb_min != null ||
    f.pb_max != null ||
    f.dividend_yield_min != null ||
    f.dividend_yield_max != null
  )
    n++;
  if (f.roe_min != null || f.roa_min != null || f.net_margin_min != null) n++;
  if (f.debt_to_equity_max != null || f.current_ratio_min != null) n++;
  if (
    f.return_1m_min != null ||
    f.return_1m_max != null ||
    f.return_3m_min != null ||
    f.return_3m_max != null ||
    f.beta_min != null ||
    f.beta_max != null ||
    f.avg_volume_30d_min != null ||
    f.near_52w_high_pct != null
  )
    n++;
  if (
    f.net_insider_buy_30d != null ||
    f.pledged_shares_below_pct != null ||
    f.free_float_min != null ||
    f.foreign_pct_min != null
  )
    n++;
  if (f.sentiment_score_min != null || f.sentiment_momentum_positive != null) n++;
  return n;
}

function FilterNumber({
  label,
  metricId,
  value,
  onChange,
}: {
  label: string;
  metricId?: string;
  value?: number | null;
  onChange: (v: number | undefined) => void;
}) {
  return (
    <div>
      <label className="block text-xs text-zinc-500">
        {metricId ? <MetricTooltip metricId={metricId}>{label}</MetricTooltip> : label}
      </label>
      <input
        type="number"
        className="mt-1 w-full rounded-lg border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
      />
    </div>
  );
}

function ScreenerContent() {
  const searchParams = useSearchParams();
  const sectorParam = searchParams.get("sectors");
  const { get, post, postBlob, del, isSignedIn } = useApi();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ScreenerFilters>(() =>
    sectorParam ? { sectors: [sectorParam] } : {},
  );
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("symbol");
  const [presetName, setPresetName] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (sectorParam) {
      setFilters((f) => ({ ...f, sectors: [sectorParam] }));
    }
  }, [sectorParam]);

  const groups = useMemo(() => countFilterGroups(filters), [filters]);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["screener", filters, page, sortBy],
    queryFn: () =>
      post<ScreenerResponse>("/screener", {
        filters,
        page,
        page_size: 50,
        sort_by: sortBy,
        sort_dir: "asc",
      }),
    retry: false,
  });

  const presetsQuery = useQuery({
    queryKey: ["screener-presets", isSignedIn],
    queryFn: () => get<ScreenerPresetListResponse>("/screener/presets"),
    enabled: isSignedIn,
    retry: false,
  });

  const savePreset = useMutation({
    mutationFn: (name: string) => post("/screener/presets", { name, filters }),
    onSuccess: () => {
      setPresetName("");
      queryClient.invalidateQueries({ queryKey: ["screener-presets"] });
    },
  });

  const deletePreset = useMutation({
    mutationFn: (id: number) => del(`/screener/presets/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["screener-presets"] }),
  });

  const exportCsv = async () => {
    setExporting(true);
    try {
      const blob = await postBlob("/screener/export", {
        filters,
        page: 1,
        page_size: 5000,
        sort_by: sortBy,
        sort_dir: "asc",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "screener_results.csv";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  const setNum = (key: keyof ScreenerFilters, v: number | undefined) =>
    setFilters((f) => ({ ...f, [key]: v }));

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Stock Screener</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Filter the PSX universe by valuation, profitability, momentum, and more.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-4 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          {!isSignedIn ? (
            <p className="text-sm text-zinc-500">Sign in to save and load screener presets.</p>
          ) : (
            <section>
              <h2 className="mb-2 text-sm font-medium">Presets</h2>
              {presetsQuery.data && presetsQuery.data.items.length > 0 && (
                <ul className="mb-2 space-y-1">
                  {presetsQuery.data.items.map((p) => (
                    <li key={p.id} className="flex items-center justify-between gap-2 text-sm">
                      <button
                        type="button"
                        className="truncate text-left hover:underline"
                        onClick={() => setFilters(p.filters)}
                      >
                        {p.name}
                      </button>
                      <button
                        type="button"
                        className="shrink-0 text-xs text-rose-600"
                        onClick={() => deletePreset.mutate(p.id)}
                      >
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <div className="flex gap-1">
                <input
                  className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-2 py-1.5 text-sm dark:border-zinc-700"
                  placeholder="Preset name"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                />
                <button
                  type="button"
                  disabled={!presetName.trim()}
                  onClick={() => savePreset.mutate(presetName.trim())}
                  className="rounded-lg border px-2 py-1 text-xs disabled:opacity-50"
                >
                  Save
                </button>
              </div>
            </section>
          )}

          <section>
            <h2 className="mb-2 text-sm font-medium">Sector</h2>
            <select
              className="w-full rounded-lg border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
              value={filters.sectors?.[0] ?? ""}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  sectors: e.target.value ? [e.target.value] : undefined,
                }))
              }
            >
              <option value="">Any sector</option>
              {SECTOR_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </section>

          <section>
            <h2 className="mb-2 text-sm font-medium">Board</h2>
            <select
              className="w-full rounded-lg border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
              value={filters.boards?.[0] ?? ""}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  boards: e.target.value ? [e.target.value] : undefined,
                }))
              }
            >
              <option value="">Any board</option>
              {BOARD_OPTIONS.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </section>

          <section>
            <h2 className="mb-2 text-sm font-medium">Index</h2>
            <select
              className="w-full rounded-lg border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
              value={filters.index_membership?.[0] ?? ""}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  index_membership: e.target.value ? [e.target.value] : undefined,
                }))
              }
            >
              <option value="">Any index</option>
              {INDEX_OPTIONS.map((idx) => (
                <option key={idx} value={idx}>
                  {idx}
                </option>
              ))}
            </select>
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-medium"><MetricTooltip metricId="market_cap">Market cap (Bn PKR)</MetricTooltip></h2>
            <FilterNumber label="Min" value={filters.market_cap_min_bn} onChange={(v) => setNum("market_cap_min_bn", v)} />
            <FilterNumber label="Max" value={filters.market_cap_max_bn} onChange={(v) => setNum("market_cap_max_bn", v)} />
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-medium">Valuation</h2>
            <FilterNumber label="P/E min" metricId="pe_ttm" value={filters.pe_min} onChange={(v) => setNum("pe_min", v)} />
            <FilterNumber label="P/E max" metricId="pe_ttm" value={filters.pe_max} onChange={(v) => setNum("pe_max", v)} />
            <FilterNumber label="P/B min" metricId="pb" value={filters.pb_min} onChange={(v) => setNum("pb_min", v)} />
            <FilterNumber label="P/B max" metricId="pb" value={filters.pb_max} onChange={(v) => setNum("pb_max", v)} />
            <FilterNumber label="Div yield min %" metricId="dividend_yield" value={filters.dividend_yield_min} onChange={(v) => setNum("dividend_yield_min", v)} />
            <FilterNumber label="Div yield max %" metricId="dividend_yield" value={filters.dividend_yield_max} onChange={(v) => setNum("dividend_yield_max", v)} />
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-medium">Profitability</h2>
            <FilterNumber label="ROE min %" metricId="roe" value={filters.roe_min} onChange={(v) => setNum("roe_min", v)} />
            <FilterNumber label="ROA min %" metricId="roa" value={filters.roa_min} onChange={(v) => setNum("roa_min", v)} />
            <FilterNumber label="Net margin min %" metricId="net_margin" value={filters.net_margin_min} onChange={(v) => setNum("net_margin_min", v)} />
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-medium">Leverage & liquidity</h2>
            <FilterNumber label="D/E max" metricId="debt_to_equity" value={filters.debt_to_equity_max} onChange={(v) => setNum("debt_to_equity_max", v)} />
            <FilterNumber label="Current ratio min" metricId="current_ratio" value={filters.current_ratio_min} onChange={(v) => setNum("current_ratio_min", v)} />
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-medium">Momentum</h2>
            <FilterNumber label="Return 1M min %" metricId="return_1m" value={filters.return_1m_min} onChange={(v) => setNum("return_1m_min", v)} />
            <FilterNumber label="Return 1M max %" metricId="return_1m" value={filters.return_1m_max} onChange={(v) => setNum("return_1m_max", v)} />
            <FilterNumber label="Return 3M min %" metricId="return_3m" value={filters.return_3m_min} onChange={(v) => setNum("return_3m_min", v)} />
            <FilterNumber label="Beta min" metricId="beta" value={filters.beta_min} onChange={(v) => setNum("beta_min", v)} />
            <FilterNumber label="Beta max" metricId="beta" value={filters.beta_max} onChange={(v) => setNum("beta_max", v)} />
            <FilterNumber label="Avg volume 30d min" metricId="avg_volume_30d" value={filters.avg_volume_30d_min} onChange={(v) => setNum("avg_volume_30d_min", v)} />
            <FilterNumber label="Near 52W high %" metricId="fifty_two_week_high" value={filters.near_52w_high_pct} onChange={(v) => setNum("near_52w_high_pct", v)} />
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-medium">Ownership</h2>
            <FilterNumber label="Free float min %" metricId="free_float" value={filters.free_float_min} onChange={(v) => setNum("free_float_min", v)} />
            <FilterNumber label="Foreign % min" metricId="foreign_pct" value={filters.foreign_pct_min} onChange={(v) => setNum("foreign_pct_min", v)} />
            <FilterNumber label="Pledged below %" metricId="pledged_shares" value={filters.pledged_shares_below_pct} onChange={(v) => setNum("pledged_shares_below_pct", v)} />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={!!filters.net_insider_buy_30d}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    net_insider_buy_30d: e.target.checked ? true : undefined,
                  }))
                }
              />
              <MetricTooltip metricId="net_insider_buy">Net insider buy (30d)</MetricTooltip>
            </label>
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-medium">Sentiment</h2>
            <FilterNumber label="Min score" value={filters.sentiment_score_min} onChange={(v) => setNum("sentiment_score_min", v)} />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={!!filters.sentiment_momentum_positive}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    sentiment_momentum_positive: e.target.checked ? true : undefined,
                  }))
                }
              />
              Positive momentum
            </label>
          </section>

          <button
            type="button"
            onClick={() => refetch()}
            className="w-full rounded-lg bg-zinc-900 py-2 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            Run screener ({groups} filter groups)
          </button>
        </aside>

        <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
            <span className="text-sm text-zinc-500">
              {data ? `${data.total} results` : "—"}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={exporting || !isSignedIn}
                onClick={() => void exportCsv()}
                className="rounded-lg border border-zinc-200 px-3 py-1 text-sm disabled:opacity-50 dark:border-zinc-700"
              >
                {exporting ? "Exporting…" : "Export CSV"}
              </button>
              <select
                className="rounded-lg border border-zinc-200 bg-transparent px-2 py-1 text-sm dark:border-zinc-700"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="symbol">Symbol</option>
                <option value="roe">ROE</option>
                <option value="pe_ttm">P/E</option>
                <option value="dividend_yield">Div yield</option>
                <option value="market_cap">Market cap</option>
                <option value="beta">Beta</option>
              </select>
            </div>
          </div>

          {isLoading && <SkeletonCard />}
          {error && (
            <p className="p-4 text-sm text-rose-600">
              {(error as Error).message || "Screener request failed"}
            </p>
          )}

          {data && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 text-left text-zinc-500 dark:border-zinc-800">
                    <th className="px-4 py-2">Symbol</th>
                    <th className="px-4 py-2">Sector</th>
                    <th className="px-4 py-2"><MetricTooltip metricId="ltp">LTP</MetricTooltip></th>
                    <th className="px-4 py-2"><MetricTooltip metricId="pe_ttm">P/E</MetricTooltip></th>
                    <th className="px-4 py-2"><MetricTooltip metricId="roe">ROE</MetricTooltip></th>
                    <th className="px-4 py-2"><MetricTooltip metricId="debt_to_equity">D/E</MetricTooltip></th>
                    <th className="px-4 py-2"><MetricTooltip metricId="dividend_yield">Div %</MetricTooltip></th>
                    <th className="px-4 py-2"><MetricTooltip metricId="beta">Beta</MetricTooltip></th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row) => (
                    <tr
                      key={row.symbol}
                      className="border-b border-zinc-100 hover:bg-zinc-50 dark:border-zinc-900 dark:hover:bg-zinc-900/50"
                    >
                      <td className="px-4 py-2">
                        <Link href={`/ticker/${row.symbol}`} className="font-medium hover:underline">
                          {row.symbol}
                        </Link>
                      </td>
                      <td className="px-4 py-2 text-zinc-500">{row.sector}</td>
                      <td className="px-4 py-2 tabular-nums">{row.ltp?.toFixed(2) ?? "—"}</td>
                      <td className="px-4 py-2 tabular-nums">{row.pe_ttm?.toFixed(1) ?? "—"}</td>
                      <td className="px-4 py-2 tabular-nums">{row.roe?.toFixed(1) ?? "—"}</td>
                      <td className="px-4 py-2 tabular-nums">{row.debt_to_equity?.toFixed(2) ?? "—"}</td>
                      <td className="px-4 py-2 tabular-nums">{row.dividend_yield?.toFixed(2) ?? "—"}</td>
                      <td className="px-4 py-2 tabular-nums">{row.beta?.toFixed(2) ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data && data.total > data.page_size && (
            <div className="flex justify-center gap-2 border-t border-zinc-200 p-4 dark:border-zinc-800">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-lg border px-3 py-1 text-sm disabled:opacity-50"
              >
                Prev
              </button>
              <span className="py-1 text-sm text-zinc-500">Page {page}</span>
              <button
                type="button"
                disabled={page * data.page_size >= data.total}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border px-3 py-1 text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

export default function ScreenerPage() {
  return (
    <Suspense fallback={<AppShell><SkeletonCard /></AppShell>}>
      <ScreenerContent />
    </Suspense>
  );
}
