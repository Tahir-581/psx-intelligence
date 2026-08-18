declare module "@sentry/nextjs" {
  export function init(options: {
    dsn?: string;
    tracesSampleRate?: number;
    environment?: string;
  }): void;
}
