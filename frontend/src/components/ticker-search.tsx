"use client";

import { useQuery } from "@tanstack/react-query";
import { Command } from "cmdk";
import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";
import type { TickerListResponse } from "@/lib/types";

export function TickerSearch() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const router = useRouter();

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const { data } = useQuery({
    queryKey: ["tickers-search", search],
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: "20" });
      if (search) params.set("search", search);
      const res = await fetch(`${API_BASE}/tickers?${params}`);
      if (!res.ok) throw new Error("Failed to load tickers");
      return res.json() as Promise<TickerListResponse>;
    },
    enabled: open,
  });

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-600 dark:border-zinc-700 dark:text-zinc-300"
      >
        <Search className="h-4 w-4" />
        Search tickers
        <kbd className="ml-6 rounded border px-1.5 text-xs">⌘K</kbd>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-[12vh]">
          <div className="w-full max-w-xl overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-2xl dark:border-zinc-700 dark:bg-zinc-950">
            <Command shouldFilter={false}>
              <div className="flex items-center border-b border-zinc-200 px-3 dark:border-zinc-800">
                <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                <Command.Input
                  value={search}
                  onValueChange={setSearch}
                  placeholder="Search symbol or company..."
                  className="h-12 w-full bg-transparent text-sm outline-none"
                />
              </div>
              <Command.List className="max-h-80 overflow-auto p-2">
                <Command.Empty className="p-4 text-sm text-zinc-500">No tickers found.</Command.Empty>
                {data?.items.map((item) => (
                  <Command.Item
                    key={item.symbol}
                    value={item.symbol}
                    onSelect={() => {
                      setOpen(false);
                      router.push(`/ticker/${item.symbol}`);
                    }}
                    className="flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-sm aria-selected:bg-zinc-100 dark:aria-selected:bg-zinc-900"
                  >
                    <div>
                      <div className="font-medium">{item.symbol}</div>
                      <div className="text-xs text-zinc-500">{item.name}</div>
                    </div>
                    <div className="text-right text-xs">
                      <div>{item.ltp != null ? `Rs ${item.ltp.toFixed(2)}` : "—"}</div>
                      <div className={item.change_pct && item.change_pct >= 0 ? "text-emerald-600" : "text-rose-600"}>
                        {item.change_pct != null ? `${item.change_pct.toFixed(2)}%` : ""}
                      </div>
                    </div>
                  </Command.Item>
                ))}
              </Command.List>
            </Command>
            <button
              type="button"
              className="w-full border-t border-zinc-200 py-2 text-xs text-zinc-500 dark:border-zinc-800"
              onClick={() => setOpen(false)}
            >
              Esc to close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
