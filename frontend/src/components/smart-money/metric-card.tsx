import { MetricTooltip } from "@/components/metric-tooltip";

export function MetricCard({
  label,
  value,
  metricId,
}: {
  label: string;
  value: string;
  metricId?: string;
}) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white px-3 py-2.5 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="text-[11px] text-zinc-500 dark:text-zinc-400">
        {metricId ? <MetricTooltip metricId={metricId}>{label}</MetricTooltip> : label}
      </div>
      <div className="text-sm font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">{value}</div>
    </div>
  );
}
