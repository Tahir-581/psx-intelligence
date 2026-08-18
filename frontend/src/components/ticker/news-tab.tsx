"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { SkeletonCard } from "@/components/movers-table";
import { apiGet } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import type { NewsKeywordsResponse, NewsListResponse, NewsVolumeResponse } from "@/lib/types";

const SOURCES = [
  { id: "", label: "All Sources" },
  { id: "business_recorder", label: "Business Recorder" },
  { id: "dawn", label: "Dawn" },
  { id: "profit", label: "Profit" },
  { id: "psx_press", label: "PSX Press" },
  { id: "tribune", label: "Tribune" },
  { id: "pakistan_today", label: "Pakistan Today" },
  { id: "brecorder_web", label: "BR Web" },
];

const TOPICS = [
  { id: "", label: "All Topics" },
  { id: "earnings", label: "Earnings" },
  { id: "dividend", label: "Dividend" },
  { id: "expansion", label: "Expansion" },
  { id: "litigation", label: "Litigation" },
  { id: "macro", label: "Macro" },
  { id: "regulatory", label: "Regulatory" },
];

function badgeClass(badge: string) {
  if (badge === "bullish") return "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300";
  if (badge === "bearish") return "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300";
  return "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400";
}

export function NewsTab({ symbol }: { symbol: string }) {
  const [source, setSource] = useState("");
  const [topic, setTopic] = useState("");
  const { get, isSignedIn } = useApi();

  const { data, isLoading } = useQuery({
    queryKey: ["news", symbol, source, topic, isSignedIn],
    queryFn: () => {
      const params = new URLSearchParams();
      if (source) params.set("source", source);
      if (topic) params.set("topic", topic);
      const qs = params.toString() ? `?${params}` : "";
      return get<NewsListResponse>(`/ticker/${symbol}/news${qs}`);
    },
  });

  const { data: volume } = useQuery({
    queryKey: ["news-volume", symbol],
    queryFn: () => apiGet<NewsVolumeResponse>(`/ticker/${symbol}/news/volume?days=30`),
  });

  const { data: keywords } = useQuery({
    queryKey: ["news-keywords", symbol, isSignedIn],
    queryFn: () => get<NewsKeywordsResponse>(`/ticker/${symbol}/news/keywords`),
    enabled: isSignedIn,
    retry: false,
  });

  if (isLoading) return <SkeletonCard />;

  const items = data?.items ?? [];
  const maxVol = Math.max(...(volume?.points.map((p) => p.count) ?? [1]), 1);

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="mb-4 text-lg font-semibold">News</h2>

      {volume?.points?.length ? (
        <div className="mb-6">
          <h3 className="mb-2 text-sm font-medium text-zinc-500">News volume (30d)</h3>
          <div className="flex h-16 items-end gap-0.5">
            {volume.points.map((p) => (
              <div
                key={p.date}
                className="flex-1 rounded-t bg-sky-500/70"
                style={{ height: `${(p.count / maxVol) * 100}%`, minHeight: 2 }}
                title={`${p.date}: ${p.count} articles`}
              />
            ))}
          </div>
        </div>
      ) : null}

      <div className="mb-3 flex flex-wrap gap-2">
        {SOURCES.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setSource(s.id)}
            className={`rounded-full px-3 py-1 text-xs ${
              source === s.id
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        {TOPICS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTopic(t.id)}
            className={`rounded-full px-3 py-1 text-xs ${
              topic === t.id
                ? "bg-sky-600 text-white"
                : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isSignedIn && keywords?.keywords?.length ? (
        <div className="mb-4 flex flex-wrap gap-2">
          {keywords.keywords.slice(0, 20).map((kw) => (
            <span
              key={kw.word}
              className="rounded-full bg-zinc-100 px-2 py-1 text-xs dark:bg-zinc-800"
              style={{ fontSize: `${Math.min(14, 10 + kw.weight)}px` }}
            >
              {kw.word}
            </span>
          ))}
        </div>
      ) : null}

      {!items.length ? (
        <p className="text-sm text-zinc-500">No linked news articles.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {items.map((item) => (
            <li key={item.id} className="py-3">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                <span className="rounded bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">{item.source}</span>
                <time dateTime={item.published_at}>
                  {new Date(item.published_at).toLocaleDateString("en-PK")}
                </time>
                {item.topic_tag && (
                  <span className="rounded bg-sky-100 px-2 py-0.5 text-sky-700 dark:bg-sky-950 dark:text-sky-300">
                    {item.topic_tag}
                  </span>
                )}
                {item.sentiment_badge && (
                  <span className={`rounded px-2 py-0.5 capitalize ${badgeClass(item.sentiment_badge)}`}>
                    {item.sentiment_badge}
                  </span>
                )}
              </div>
              <a
                href={item.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium hover:underline"
              >
                {item.headline}
              </a>
              {item.ai_summary && (
                <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{item.ai_summary}</p>
              )}
              {item.excerpt && !item.ai_summary && (
                <p className="mt-1 text-sm text-zinc-500 line-clamp-2">{item.excerpt}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
