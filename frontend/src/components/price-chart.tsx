"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type Time,
} from "lightweight-charts";
import type { ChartMarker, IndicatorPoint, PriceBar } from "@/lib/types";
import { MetricTooltip } from "@/components/metric-tooltip";
import { formatPct } from "@/lib/utils";

type RangeKey = "1W" | "1M" | "3M" | "6M" | "1Y" | "3Y" | "5Y" | "Max";
type ChartType = "candle" | "line" | "area";
type IndexOverlay = "KSE100" | "SECTOR" | null;

const RANGE_DAYS: Record<RangeKey, number | null> = {
  "1W": 7,
  "1M": 30,
  "3M": 90,
  "6M": 180,
  "1Y": 365,
  "3Y": 365 * 3,
  "5Y": 365 * 5,
  Max: null,
};

const SMA_OPTIONS = ["SMA20", "SMA50"] as const;
const SMA_COLORS: Record<string, string> = {
  SMA20: "#f59e0b",
  SMA50: "#8b5cf6",
  SMA200: "#ec4899",
};

export interface PriceChartConfig {
  chartType: ChartType;
  adjusted: boolean;
  indexOverlay: IndexOverlay;
  overlays: string[];
  showVolumeMa: boolean;
}

interface PriceChartProps {
  bars: PriceBar[];
  range: RangeKey;
  onRangeChange: (range: RangeKey) => void;
  overlayBars?: PriceBar[] | null;
  sector?: string;
  markers?: ChartMarker[];
  indicatorSeries?: Record<string, IndicatorPoint[]> | null;
  volumeMa?: IndicatorPoint[] | null;
  onConfigChange?: (config: PriceChartConfig) => void;
}

function toChartTime(time: string): Time {
  return (new Date(time).getTime() / 1000) as unknown as Time;
}

function filterByRange<T extends { time: string }>(items: T[], range: RangeKey): T[] {
  const days = RANGE_DAYS[range];
  if (!days) return items;
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  return items.filter((b) => new Date(b.time).getTime() >= cutoff);
}

export function PriceChart({
  bars,
  range,
  onRangeChange,
  overlayBars,
  sector,
  markers = [],
  indicatorSeries,
  volumeMa,
  onConfigChange,
}: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainRef = useRef<ISeriesApi<"Candlestick"> | ISeriesApi<"Line"> | ISeriesApi<"Area"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const volumeMaRef = useRef<ISeriesApi<"Line"> | null>(null);
  const indexOverlayRef = useRef<ISeriesApi<"Line"> | null>(null);
  const smaRefs = useRef<Map<string, ISeriesApi<"Line">>>(new Map());
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);

  const [chartType, setChartType] = useState<ChartType>("candle");
  const [adjusted, setAdjusted] = useState(true);
  const [indexOverlay, setIndexOverlay] = useState<IndexOverlay>(null);
  const [enabledSmas, setEnabledSmas] = useState<string[]>([]);
  const [showVolumeMa, setShowVolumeMa] = useState(false);
  const [returnCalc, setReturnCalc] = useState<{ t1: number; p1: number } | null>(null);
  const [returnResult, setReturnResult] = useState<string | null>(null);

  const filtered = filterByRange(bars, range);
  const filteredOverlay = filterByRange(overlayBars ?? [], range);
  const filteredVolumeMa = filterByRange(volumeMa ?? [], range);

  const emitConfig = useCallback(
    (overrides: Partial<PriceChartConfig> = {}) => {
      onConfigChange?.({
        chartType,
        adjusted,
        indexOverlay,
        overlays: enabledSmas,
        showVolumeMa,
        ...overrides,
      });
    },
    [chartType, adjusted, indexOverlay, enabledSmas, showVolumeMa, onConfigChange],
  );

  useEffect(() => {
    emitConfig();
  }, [emitConfig]);

  const toggleSma = (sma: string) => {
    setEnabledSmas((prev) => {
      const next = prev.includes(sma) ? prev.filter((s) => s !== sma) : [...prev, sma];
      emitConfig({ overlays: next });
      return next;
    });
  };

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#71717a",
      },
      grid: {
        vertLines: { color: "rgba(113,113,122,0.15)" },
        horzLines: { color: "rgba(113,113,122,0.15)" },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      height: 420,
    });
    const volume = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    const volumeMaLine = chart.addSeries(LineSeries, {
      color: "#a1a1aa",
      lineWidth: 1,
      priceScaleId: "volume",
    });
    const indexLine = chart.addSeries(LineSeries, {
      color: "#6366f1",
      lineWidth: 2,
      priceScaleId: "overlay",
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    chart.priceScale("overlay").applyOptions({ scaleMargins: { top: 0.1, bottom: 0.4 } });

    chartRef.current = chart;
    volumeRef.current = volume;
    volumeMaRef.current = volumeMaLine;
    indexOverlayRef.current = indexLine;

    const resize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
      mainRef.current = null;
      smaRefs.current.clear();
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    if (mainRef.current) {
      chart.removeSeries(mainRef.current);
      mainRef.current = null;
      markersRef.current = null;
    }

    let main: ISeriesApi<"Candlestick"> | ISeriesApi<"Line"> | ISeriesApi<"Area">;
    if (chartType === "candle") {
      main = chart.addSeries(CandlestickSeries, {
        upColor: "#10b981",
        downColor: "#ef4444",
        borderVisible: false,
        wickUpColor: "#10b981",
        wickDownColor: "#ef4444",
      });
    } else if (chartType === "line") {
      main = chart.addSeries(LineSeries, {
        color: "#0ea5e9",
        lineWidth: 2,
      });
    } else {
      main = chart.addSeries(AreaSeries, {
        lineColor: "#0ea5e9",
        topColor: "rgba(14,165,233,0.4)",
        bottomColor: "rgba(14,165,233,0.05)",
      });
    }
    mainRef.current = main;
    markersRef.current = createSeriesMarkers(main);

    for (const [, series] of smaRefs.current) {
      chart.removeSeries(series);
    }
    smaRefs.current.clear();
    for (const sma of enabledSmas) {
      const line = chart.addSeries(LineSeries, {
        color: SMA_COLORS[sma] ?? "#71717a",
        lineWidth: 1,
        priceScaleId: "right",
      });
      smaRefs.current.set(sma, line);
    }
  }, [chartType, enabledSmas]);

  useEffect(() => {
    if (!mainRef.current || !volumeRef.current) return;

    if (chartType === "candle") {
      (mainRef.current as ISeriesApi<"Candlestick">).setData(
        filtered.map((b) => ({
          time: toChartTime(b.time),
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
        })),
      );
    } else {
      (mainRef.current as ISeriesApi<"Line" | "Area">).setData(
        filtered.map((b) => ({
          time: toChartTime(b.time),
          value: b.close,
        })),
      );
    }

    volumeRef.current.setData(
      filtered.map((b) => ({
        time: toChartTime(b.time),
        value: b.volume,
        color: b.close >= b.open ? "rgba(16,185,129,0.5)" : "rgba(239,68,68,0.5)",
      })),
    );

    if (volumeMaRef.current) {
      if (showVolumeMa && filteredVolumeMa.length) {
        volumeMaRef.current.setData(
          filteredVolumeMa.map((p) => ({
            time: toChartTime(p.time),
            value: p.value,
          })),
        );
      } else {
        volumeMaRef.current.setData([]);
      }
    }

    if (indexOverlayRef.current) {
      if (indexOverlay && filteredOverlay.length) {
        indexOverlayRef.current.setData(
          filteredOverlay.map((b) => ({
            time: toChartTime(b.time),
            value: b.close,
          })),
        );
      } else {
        indexOverlayRef.current.setData([]);
      }
    }

    for (const [sma, series] of smaRefs.current) {
      const points = indicatorSeries?.[sma];
      if (points?.length) {
        const filteredPts = filterByRange(points, range);
        series.setData(
          filteredPts.map((p) => ({
            time: toChartTime(p.time),
            value: p.value,
          })),
        );
      } else {
        series.setData([]);
      }
    }

    const chartMarkers = markers
      .filter((m) => {
        const t = new Date(m.time).getTime();
        const min = filtered.length ? new Date(filtered[0].time).getTime() : 0;
        const max = filtered.length ? new Date(filtered[filtered.length - 1].time).getTime() : Infinity;
        return t >= min && t <= max;
      })
      .map((m) => ({
        time: toChartTime(m.time),
        position: "aboveBar" as const,
        color: m.kind === "dividend" ? "#10b981" : m.kind === "macro" ? "#6366f1" : "#f59e0b",
        shape: "circle" as const,
        text: m.label.slice(0, 16),
      }));
    markersRef.current?.setMarkers(chartMarkers);
    chartRef.current?.timeScale().fitContent();
  }, [
    filtered,
    filteredOverlay,
    filteredVolumeMa,
    markers,
    indexOverlay,
    showVolumeMa,
    indicatorSeries,
    chartType,
    range,
    enabledSmas,
  ]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    const handler = (param: { time?: Time; point?: { x: number; y: number } }) => {
      if (!param.time || !mainRef.current) return;
      const ts = typeof param.time === "number" ? param.time * 1000 : Number(param.time) * 1000;
      const bar = filtered.find((b) => Math.abs(new Date(b.time).getTime() - ts) < 86400000);
      if (!bar) return;
      const price = bar.close;
      if (!returnCalc) {
        setReturnCalc({ t1: ts, p1: price });
        setReturnResult(`Click end date (start: ${new Date(ts).toLocaleDateString("en-PK")} @ ${price.toFixed(2)})`);
      } else {
        const ret = ((price - returnCalc.p1) / returnCalc.p1) * 100;
        setReturnResult(
          `${new Date(returnCalc.t1).toLocaleDateString("en-PK")} → ${new Date(ts).toLocaleDateString("en-PK")}: ${formatPct(ret)}`,
        );
        setReturnCalc(null);
      }
    };

    chart.subscribeClick(handler);
    return () => chart.unsubscribeClick(handler);
  }, [filtered, returnCalc]);

  const ranges: RangeKey[] = ["1W", "1M", "3M", "6M", "1Y", "3Y", "5Y", "Max"];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {ranges.map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => onRangeChange(r)}
            className={`rounded-md px-3 py-1 text-xs ${
              range === r
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
            }`}
          >
            {r}
          </button>
        ))}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {(["candle", "line", "area"] as ChartType[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => {
                setChartType(t);
                emitConfig({ chartType: t });
              }}
              className={`rounded-md px-3 py-1 text-xs capitalize ${
                chartType === t
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "bg-zinc-100 text-zinc-700 dark:bg-zinc-800"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs">
        <label className="flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={adjusted}
            onChange={(e) => {
              setAdjusted(e.target.checked);
              emitConfig({ adjusted: e.target.checked });
            }}
            className="rounded"
          />
          <MetricTooltip metricId="adjusted">Adjusted</MetricTooltip>
        </label>
        {SMA_OPTIONS.map((sma) => (
          <label key={sma} className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={enabledSmas.includes(sma)}
              onChange={() => toggleSma(sma)}
              className="rounded"
            />
            <MetricTooltip metricId={sma.toLowerCase()}>{sma}</MetricTooltip>
          </label>
        ))}
        <label className="flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={showVolumeMa}
            onChange={(e) => {
              setShowVolumeMa(e.target.checked);
              emitConfig({ showVolumeMa: e.target.checked });
            }}
            className="rounded"
          />
          <MetricTooltip metricId="vol_ma">Vol MA</MetricTooltip>
        </label>
        <button
          type="button"
          onClick={() => {
            const next = indexOverlay === "KSE100" ? null : "KSE100";
            setIndexOverlay(next);
            emitConfig({ indexOverlay: next });
          }}
          className={`rounded-md px-2 py-1 ${
            indexOverlay === "KSE100" ? "bg-indigo-600 text-white" : "bg-zinc-100 dark:bg-zinc-800"
          }`}
        >
          <MetricTooltip metricId="kse100">KSE-100</MetricTooltip>
        </button>
        {sector && (
          <button
            type="button"
            onClick={() => {
              const next = indexOverlay === "SECTOR" ? null : "SECTOR";
              setIndexOverlay(next);
              emitConfig({ indexOverlay: next });
            }}
            className={`rounded-md px-2 py-1 ${
              indexOverlay === "SECTOR" ? "bg-indigo-600 text-white" : "bg-zinc-100 dark:bg-zinc-800"
            }`}
          >
            Sector
          </button>
        )}
        <button
          type="button"
          onClick={() => {
            setReturnCalc(null);
            setReturnResult("Click two points on chart to calculate return");
          }}
          className="rounded-md bg-zinc-100 px-2 py-1 dark:bg-zinc-800"
        >
          <MetricTooltip metricId="returns_tool">Returns</MetricTooltip>
        </button>
      </div>

      {returnResult && (
        <p className="text-xs text-zinc-600 dark:text-zinc-400">{returnResult}</p>
      )}

      <div ref={containerRef} className="w-full" />
    </div>
  );
}
