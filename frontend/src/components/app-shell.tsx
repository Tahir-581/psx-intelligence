"use client";



import Link from "next/link";

import { usePathname } from "next/navigation";

import { useQuery } from "@tanstack/react-query";

import {

  BarChart3,

  GitCompare,

  Home,

  Star,

  User,

} from "lucide-react";

import { MetricTooltip } from "@/components/metric-tooltip";
import { AuthHeader } from "@/components/auth-header";

import { NotificationBell } from "@/components/notification-bell";

import { MarketStatusBadge, ThemeToggle } from "@/components/theme-toggle";

import { TickerSearch } from "@/components/ticker-search";

import { apiGet } from "@/lib/api";

import type { MacroSeriesResponse } from "@/lib/types";

import { cn } from "@/lib/utils";



const NAV_LINKS = [

  { href: "/screener", label: "Screener" },

  { href: "/compare", label: "Compare" },

  { href: "/smart-money/feed", label: "Smart Money" },

  { href: "/portfolio", label: "Portfolio" },

  { href: "/watchlist", label: "Watchlist" },

  { href: "/alerts", label: "Alerts" },

];



const MOBILE_NAV = [

  { href: "/", label: "Home", icon: Home },

  { href: "/screener", label: "Screener", icon: BarChart3 },

  { href: "/compare", label: "Compare", icon: GitCompare },

  { href: "/watchlist", label: "Watchlist", icon: Star },

  { href: "/account", label: "Account", icon: User },

];



function latestMacroValue(data: MacroSeriesResponse | undefined): number | null {

  if (!data?.points?.length) return null;

  return data.points[data.points.length - 1].value;

}



export function AppShell({

  children,

  marketOpen,

  indexLevel,

  indexChangePct,

}: {

  children: React.ReactNode;

  marketOpen?: boolean;

  indexLevel?: number | null;

  indexChangePct?: number | null;

}) {

  const pathname = usePathname();



  const { data: sbp } = useQuery({

    queryKey: ["macro", "sbp_policy_rate"],

    queryFn: () => apiGet<MacroSeriesResponse>("/macro/sbp_policy_rate"),

    staleTime: 300_000,

  });



  const { data: pkrUsd } = useQuery({

    queryKey: ["macro", "pkr_usd"],

    queryFn: () => apiGet<MacroSeriesResponse>("/macro/pkr_usd"),

    staleTime: 300_000,

  });



  const sbpRate = latestMacroValue(sbp);

  const fxRate = latestMacroValue(pkrUsd);



  return (

    <div className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-black dark:text-zinc-100">

      <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/90 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/90">

        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-3">

          <div className="flex flex-wrap items-center gap-4 md:gap-6">

            <Link href="/" className="text-lg font-semibold tracking-tight">

              PSX Intelligence

            </Link>

            <nav className="hidden items-center gap-1 overflow-x-auto text-sm md:flex md:gap-2">

              {NAV_LINKS.map((link) => (

                <Link

                  key={link.href}

                  href={link.href}

                  className={cn(

                    "whitespace-nowrap rounded-lg px-2 py-1 md:px-3",

                    pathname === link.href

                      ? "bg-zinc-100 font-medium dark:bg-zinc-800"

                      : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"

                  )}

                >

                  {link.label}

                </Link>

              ))}

            </nav>

            <div className="hidden items-center gap-3 text-sm lg:flex">

              <span className="text-zinc-500"><MetricTooltip metricId="kse100">KSE-100</MetricTooltip></span>

              <span className="font-medium tabular-nums">

                {indexLevel != null

                  ? indexLevel.toLocaleString("en-PK", { maximumFractionDigits: 2 })

                  : "—"}

              </span>

              {indexChangePct != null && (

                <span className={indexChangePct >= 0 ? "text-emerald-600" : "text-rose-600"}>

                  {indexChangePct >= 0 ? "+" : ""}

                  {indexChangePct.toFixed(2)}%

                </span>

              )}

              {marketOpen != null && <MarketStatusBadge open={marketOpen} />}

              <span className="text-zinc-300 dark:text-zinc-700">|</span>

              <span className="text-zinc-500"><MetricTooltip metricId="sbp_rate">SBP</MetricTooltip></span>

              <span className="font-medium tabular-nums">

                {sbpRate != null ? `${sbpRate.toFixed(1)}%` : "—"}

              </span>

              <span className="text-zinc-500"><MetricTooltip metricId="pkr_usd">PKR/USD</MetricTooltip></span>

              <span className="font-medium tabular-nums">

                {fxRate != null ? fxRate.toFixed(2) : "—"}

              </span>

            </div>

          </div>

          <div className="flex items-center gap-3">

            <TickerSearch />

            <NotificationBell />

            <AuthHeader />

            <ThemeToggle />

          </div>

        </div>

      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 pb-20 md:pb-6">{children}</main>



      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-zinc-200 bg-white/95 backdrop-blur md:hidden dark:border-zinc-800 dark:bg-zinc-950/95">

        <div className="mx-auto flex max-w-7xl items-stretch justify-around px-2 py-1">

          {MOBILE_NAV.map(({ href, label, icon: Icon }) => {

            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);

            return (

              <Link

                key={href}

                href={href}

                className={cn(

                  "flex flex-1 flex-col items-center gap-0.5 rounded-lg px-1 py-2 text-[10px]",

                  active

                    ? "font-medium text-zinc-900 dark:text-zinc-100"

                    : "text-zinc-500 dark:text-zinc-400"

                )}

              >

                <Icon className="h-5 w-5" strokeWidth={active ? 2.25 : 1.75} />

                {label}

              </Link>

            );

          })}

        </div>

      </nav>

    </div>

  );

}

