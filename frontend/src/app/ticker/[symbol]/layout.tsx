import type { Metadata } from "next";
import { API_BASE } from "@/lib/api";
import type { SnapshotResponse } from "@/lib/types";

type Props = {
  params: Promise<{ symbol: string }>;
  children: React.ReactNode;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { symbol } = await params;
  const sym = symbol.toUpperCase();

  try {
    const res = await fetch(`${API_BASE}/ticker/${encodeURIComponent(sym)}/snapshot`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) {
      return { title: `${sym} | PSX Intelligence` };
    }
    const snap = (await res.json()) as SnapshotResponse;
    const changeStr =
      snap.change_pct != null
        ? `${snap.change_pct >= 0 ? "+" : ""}${snap.change_pct.toFixed(2)}%`
        : "";
    const title = `${snap.name} (${sym})`;
    const description = `${snap.name} on PSX — LTP ${snap.ltp?.toFixed(2) ?? "—"} PKR${changeStr ? `, ${changeStr}` : ""}. Sector: ${snap.sector}.`;

    return {
      title,
      description,
      openGraph: {
        title,
        description,
        type: "website",
        siteName: "PSX Intelligence Platform",
      },
      twitter: {
        card: "summary",
        title,
        description,
      },
    };
  } catch {
    return {
      title: `${sym} | PSX Intelligence`,
      description: `Market data and analytics for ${sym} on the Pakistan Stock Exchange.`,
    };
  }
}

export default function TickerLayout({ children }: { children: React.ReactNode }) {
  return children;
}
