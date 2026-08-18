const AVATAR_COLORS: Record<string, { bg: string; text: string }> = {
  blue: { bg: "bg-blue-100 dark:bg-blue-950", text: "text-blue-700 dark:text-blue-300" },
  teal: { bg: "bg-teal-100 dark:bg-teal-950", text: "text-teal-700 dark:text-teal-300" },
  purple: { bg: "bg-purple-100 dark:bg-purple-950", text: "text-purple-700 dark:text-purple-300" },
  amber: { bg: "bg-amber-100 dark:bg-amber-950", text: "text-amber-700 dark:text-amber-300" },
  green: { bg: "bg-emerald-100 dark:bg-emerald-950", text: "text-emerald-700 dark:text-emerald-300" },
  coral: { bg: "bg-rose-100 dark:bg-rose-950", text: "text-rose-700 dark:text-rose-300" },
};

export function getAvatarColors(color: string) {
  return AVATAR_COLORS[color] ?? AVATAR_COLORS.blue;
}

export function formatCurrency(amount: number): string {
  const abs = Math.abs(amount);
  if (abs >= 1_000_000_000_000) {
    const val = abs / 1_000_000_000_000;
    return `$${val < 10 ? val.toFixed(1) : Math.round(val)}T`;
  }
  if (abs >= 1_000_000_000) {
    const val = abs / 1_000_000_000;
    return `$${val < 10 ? val.toFixed(1) : Math.round(val)}B`;
  }
  if (abs >= 1_000_000) {
    const val = abs / 1_000_000;
    return `$${val < 10 ? val.toFixed(1) : Math.round(val)}M`;
  }
  const val = abs / 1_000;
  return `$${val < 10 ? val.toFixed(1) : Math.round(val)}K`;
}

export function formatPct(pct: number, signed = false): string {
  const rounded = pct.toFixed(1);
  if (signed && pct > 0) return `+${rounded}%`;
  return `${rounded}%`;
}

export function formatShortDate(iso: string): string {
  if (!iso?.trim()) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
}

export function formatShares(shares: number): string {
  if (shares >= 1_000_000) return `${(shares / 1_000_000).toFixed(1)}M`;
  if (shares >= 1_000) return `${(shares / 1_000).toFixed(1)}K`;
  return shares.toLocaleString();
}

export function getInvestorTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    hedge_fund: "Hedge fund",
    pe_activist: "PE / Activist",
    individual: "Individual",
    mutual_fund: "Mutual fund",
    value_fund: "Value fund",
  };
  return labels[type] ?? type;
}
