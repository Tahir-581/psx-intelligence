export function FilingBadge({ formType }: { formType: string }) {
  const colors: Record<string, string> = {
    "13F": "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
    "4": "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
    "13D": "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
    "13G": "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300",
  };
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${colors[formType] ?? "bg-zinc-100 text-zinc-700"}`}>
      {formType}
    </span>
  );
}
