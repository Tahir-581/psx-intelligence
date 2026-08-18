"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { SkeletonCard } from "@/components/movers-table";
import { useApi } from "@/lib/use-api";
import type { NewsKeywordsResponse, SentimentSeriesResponse } from "@/lib/types";
import { apiGet } from "@/lib/api";

function SentimentGauge({ score }: { score: number }) {
  const pct = ((score + 1) / 2) * 100;
  const color =
    score >= 0.15 ? "bg-emerald-500" : score <= -0.15 ? "bg-rose-500" : "bg-zinc-400";
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-zinc-500">
        <span>Bearish</span>
        <span className="font-medium tabular-nums">{score.toFixed(2)}</span>
        <span>Bullish</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function SentimentTab({ symbol }: { symbol: string }) {
  const { get, isSignedIn } = useApi();
  const { data, isLoading } = useQuery({
    queryKey: ["sentiment", symbol, isSignedIn],
    queryFn: () => get<SentimentSeriesResponse>(`/ticker/${symbol}/sentiment?days=90`),
    enabled: isSignedIn,
    retry: false,
  });

  const { data: priceSeries } = useQuery({
    queryKey: ["prices-sentiment", symbol],
    queryFn: () => apiGet<{ bars: { time: string; close: number }[] }>(`/ticker/${symbol}/prices?adjusted=true`),
  });

  const { data: keywords } = useQuery({
    queryKey: ["sentiment-keywords", symbol, isSignedIn],
    queryFn: () => get<NewsKeywordsResponse>(`/ticker/${symbol}/news/keywords`),
    enabled: isSignedIn,
    retry: false,
  });

  const sourceCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    if (!data) return counts;
    for (const [source, points] of Object.entries(data.by_source)) {
      counts[source] = points.reduce((s, p) => s + p.post_count, 0);
    }
    return counts;
  }, [data]);

  const divergence = useMemo(() => {
    if (!data?.current_score || !priceSeries?.bars?.length) return null;
    const recent = priceSeries.bars.slice(-5);
    const priceChange =
      recent.length >= 2
        ? ((recent[recent.length - 1].close - recent[0].close) / recent[0].close) * 100
        : 0;
    const sentimentUp = data.current_score > 0;
    const priceUp = priceChange > 0;
    if (sentimentUp !== priceUp && Math.abs(priceChange) > 1 && Math.abs(data.current_score) > 0.1) {
      return { priceChange, sentiment: data.current_score };
    }
    return null;
  }, [data, priceSeries]);

  if (isLoading && isSignedIn) return <SkeletonCard />;

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-4 text-lg font-semibold">Sentiment</h2>
      {!isSignedIn ? (
        <p className="text-sm text-zinc-500">Sign in to view sentiment analysis.</p>
      ) : (
        <div className="space-y-6">
          {data?.current_score != null && <SentimentGauge score={data.current_score} />}
          {data?.momentum_3d != null && (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              3-day momentum:{" "}
              <span className={data.momentum_3d >= 0 ? "text-emerald-600" : "text-rose-600"}>
                {data.momentum_3d >= 0 ? "+" : ""}
                {data.momentum_3d.toFixed(3)}
              </span>
            </p>
          )}

          {divergence && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm dark:border-amber-900 dark:bg-amber-950">
              <span className="font-medium">Divergence detected: </span>
              Sentiment {divergence.sentiment.toFixed(2)} vs price {divergence.priceChange.toFixed(2)}% (5d)
            </div>
          )}

          <div>
            <h3 className="mb-2 text-sm font-medium">Price vs Sentiment (dual-axis)</h3>
            <div className="relative h-32 rounded-lg border border-zinc-200 dark:border-zinc-800">
              {data?.aggregate?.length ? (
                <div className="flex h-full items-end gap-0.5 p-2">
                  {data.aggregate.map((p, i) => {
                    const priceBar = priceSeries?.bars[i];
                    const sentH = ((p.score + 1) / 2) * 100;
                    const priceH = priceBar ? 50 : 0;
                    return (
                      <div key={p.time} className="relative flex flex-1 flex-col justify-end gap-0.5" style={{ height: "100%" }}>
                        <div
                          className="rounded-t bg-sky-500/60"
                          style={{ height: `${Math.max(4, sentH * 0.8)}%` }}
                          title={`Sentiment: ${p.score.toFixed(2)}`}
                        />
                        {priceBar && (
                          <div
                            className="rounded-t bg-emerald-500/40"
                            style={{ height: `${Math.max(4, priceH)}%` }}
                            title={`Price: ${priceBar.close}`}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="flex h-full items-center justify-center text-sm text-zinc-500">
                  Dual-axis chart — awaiting data
                </p>
              )}
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-medium">90-day trend</h3>
            {data?.aggregate?.length ? (
              <div className="flex h-24 items-end gap-0.5">
                {data.aggregate.map((p) => {
                  const h = ((p.score + 1) / 2) * 100;
                  return (
                    <div
                      key={p.time}
                      title={`${p.time}: ${p.score.toFixed(2)}`}
                      className="flex-1 rounded-t bg-sky-500/70"
                      style={{ height: `${Math.max(4, h)}%` }}
                    />
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-zinc-500">No sentiment data yet.</p>
            )}
          </div>

          <div>
            <h3 className="mb-2 text-sm font-medium">Mention volume by source (30d)</h3>
            <div className="flex flex-wrap gap-3">
              {Object.entries(sourceCounts).map(([source, count]) => (
                <div key={source} className="rounded-lg bg-zinc-100 px-3 py-2 text-sm dark:bg-zinc-800">
                  <span className="capitalize">{source}</span>: {count}
                </div>
              ))}
            </div>
          </div>

          {keywords?.keywords?.length ? (
            <div>
              <h3 className="mb-2 text-sm font-medium">Keyword cloud</h3>
              <div className="flex flex-wrap gap-2">
                {keywords.keywords.map((kw) => (
                  <span
                    key={kw.word}
                    className="rounded-full bg-indigo-100 px-2 py-1 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300"
                    style={{ fontSize: `${Math.min(18, 10 + kw.weight * 2)}px` }}
                  >
                    {kw.word}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
