"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/smart-money/feed", label: "Feed" },
  { href: "/smart-money/investors", label: "Investors" },
  { href: "/smart-money/investments", label: "Investments" },
  { href: "/smart-money/sec-insiders", label: "SEC Insiders" },
  { href: "/smart-money/alerts", label: "Alerts" },
];

export function SmartMoneyNav() {
  const pathname = usePathname();
  return (
    <nav className="mb-6 flex flex-wrap gap-1 border-b border-zinc-200 pb-3 dark:border-zinc-800">
      {LINKS.map((link) => {
        const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "rounded-lg px-3 py-1.5 text-sm",
              active
                ? "bg-zinc-100 font-medium dark:bg-zinc-800"
                : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
