"use client";

import { useEffect } from "react";

export function SentryInit() {
  useEffect(() => {
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
    if (!dsn) return;

    void import("@sentry/nextjs")
      .then((Sentry) => {
        Sentry.init({
          dsn,
          tracesSampleRate: 0.1,
          environment: process.env.NODE_ENV,
        });
      })
      .catch(() => {
        /* @sentry/nextjs not installed */
      });
  }, []);

  return null;
}
