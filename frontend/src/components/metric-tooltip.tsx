"use client";

import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { getMetricInfo, resolveMetricInfo } from "@/lib/metric-glossary";
import { cn } from "@/lib/utils";

type MetricTooltipProps = {
  metricId?: string;
  children: ReactNode;
  className?: string;
};

export function MetricTooltip({ metricId, children, className }: MetricTooltipProps) {
  const info = metricId ? getMetricInfo(metricId) : resolveMetricInfo(String(children));
  const tooltipId = useId();
  const triggerRef = useRef<HTMLSpanElement>(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0, placement: "top" as "top" | "bottom" });
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const updatePosition = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const tooltipWidth = 280;
    const gap = 8;
    const estimatedHeight = 120;
    const spaceAbove = rect.top;
    const placement = spaceAbove < estimatedHeight + gap ? "bottom" : "top";

    let left = rect.left + rect.width / 2 - tooltipWidth / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - tooltipWidth - 8));

    const top =
      placement === "top" ? rect.top - gap : rect.bottom + gap;

    setPos({ top, left, placement });
  }, []);

  const show = useCallback(() => {
    updatePosition();
    setOpen(true);
  }, [updatePosition]);

  const hide = useCallback(() => {
    setOpen(false);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onScroll = () => updatePosition();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onScroll);
    };
  }, [open, updatePosition]);

  if (!info) {
    return <>{children}</>;
  }

  const displayLabel = typeof children === "string" ? children : info.aliases?.[0] ?? info.fullName;

  return (
    <>
      <span
        ref={triggerRef}
        tabIndex={0}
        className={cn(
          "cursor-help border-b border-dotted border-zinc-400/70 dark:border-zinc-500/70",
          className,
        )}
        aria-describedby={open ? tooltipId : undefined}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
      >
        {children}
      </span>
      {mounted &&
        open &&
        createPortal(
          <div
            id={tooltipId}
            role="tooltip"
            className="pointer-events-none fixed z-[9999] w-[280px] rounded-lg border border-zinc-200 bg-white p-3 text-left shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
            style={{
              top: pos.placement === "top" ? undefined : pos.top,
              bottom: pos.placement === "top" ? window.innerHeight - pos.top : undefined,
              left: pos.left,
              transform: pos.placement === "top" ? "translateY(-100%)" : undefined,
            }}
          >
            <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              {info.fullName}
              {displayLabel && displayLabel !== info.fullName && (
                <span className="font-normal text-zinc-500"> ({displayLabel})</span>
              )}
            </p>
            <p className="mt-1.5 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">
              {info.definition}
            </p>
            <p className="mt-2 text-xs leading-relaxed text-zinc-500 dark:text-zinc-500">
              <span className="font-medium text-zinc-600 dark:text-zinc-400">Why it matters: </span>
              {info.benefit}
            </p>
          </div>,
          document.body,
        )}
    </>
  );
}
