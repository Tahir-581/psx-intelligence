"""Backfill sec_filers summaries from sec_holdings."""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def backfill_filer_summaries(engine: Engine) -> dict[str, int]:
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                WITH latest AS (
                  SELECT cik, MAX(report_period) AS report_period
                  FROM sec_holdings GROUP BY cik
                ),
                agg AS (
                  SELECT h.cik, l.report_period,
                         COALESCE(SUM(h.value_usd), 0)::bigint AS total_value,
                         COUNT(*)::int AS holdings_count,
                         (SELECT COALESCE(ticker, LEFT(cusip, 6))
                          FROM sec_holdings h2
                          WHERE h2.cik = h.cik AND h2.report_period = l.report_period
                          ORDER BY value_usd DESC LIMIT 1) AS top_ticker,
                         (SELECT portfolio_pct
                          FROM sec_holdings h3
                          WHERE h3.cik = h.cik AND h3.report_period = l.report_period
                          ORDER BY portfolio_pct DESC LIMIT 1) AS top_pct
                  FROM sec_holdings h
                  INNER JOIN latest l ON h.cik = l.cik AND h.report_period = l.report_period
                  GROUP BY h.cik, l.report_period
                )
                UPDATE sec_filers f
                SET total_portfolio_value = agg.total_value,
                    holdings_count = agg.holdings_count,
                    top_ticker = COALESCE(agg.top_ticker, ''),
                    top_pct = COALESCE(agg.top_pct, 0),
                    last_report_period = GREATEST(
                      COALESCE(f.last_report_period, '1900-01-01'::date),
                      agg.report_period
                    ),
                    updated_at = NOW()
                FROM agg WHERE f.cik = agg.cik
            """)
        )
        return {"updated": result.rowcount or 0}
