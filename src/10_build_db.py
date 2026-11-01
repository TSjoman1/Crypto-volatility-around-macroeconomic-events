#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build DuckDB views + derived RV / event / panel tables.

Laptop-safe: RV computed per symbol via SQL over Parquet; panels stay hourly/daily.
Also builds event_windows (exact ±15/30/60/120m) for the paper's primary tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from utils import setup_logger

log = setup_logger("10_build_db")


def main() -> None:
    cfg.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(cfg.DB_PATH))
    con.execute(f"PRAGMA threads={cfg.DUCKDB_THREADS}")

    iv = cfg.KLINE_INTERVAL
    klines_glob = str(cfg.CLEAN / f"klines_{iv}" / "**" / "*.parquet")
    con.execute(
        f"""
        CREATE OR REPLACE VIEW klines AS
        SELECT * FROM read_parquet('{klines_glob}', hive_partitioning := true);
        """
    )
    # Alias for older notes / QA
    con.execute("CREATE OR REPLACE VIEW klines_15m AS SELECT * FROM klines;")

    def view_or_empty(name: str, glob: str, cols_sql: str):
        paths = list(Path(glob.replace("**", "").split("*")[0]).parent.glob("**/*")) if False else None
        # simpler: try read, else empty
        g = glob
        try:
            n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{g}', hive_partitioning := true)").fetchone()
            con.execute(
                f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{g}', hive_partitioning := true);"
            )
            log.info("view %s rows~%s", name, n)
        except Exception:
            try:
                con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{g}');")
            except Exception as e:
                log.warning("view %s empty (%s)", name, e)
                con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM (SELECT {cols_sql}) WHERE 1=0;")

    view_or_empty("funding", str(cfg.CLEAN / "funding" / "*.parquet"),
                  "CAST(NULL AS VARCHAR) AS symbol, CAST(NULL AS TIMESTAMP) AS funding_time_utc, CAST(NULL AS DOUBLE) AS funding_rate")
    view_or_empty("dvol", str(cfg.CLEAN / "dvol" / "*.parquet"),
                  "CAST(NULL AS VARCHAR) AS currency, CAST(NULL AS TIMESTAMP) AS ts_utc, CAST(NULL AS DOUBLE) AS close")
    view_or_empty("expiries", str(cfg.CLEAN / "expiries" / "*.parquet"),
                  "CAST(NULL AS VARCHAR) AS currency, CAST(NULL AS TIMESTAMP) AS expiry_time, CAST(NULL AS VARCHAR) AS expiry_type")

    for table, path in [
        ("macro_events", cfg.CLEAN / "macro_events.parquet"),
        ("equity_sessions", cfg.CLEAN / "equity_sessions.parquet"),
        ("unlocks", cfg.CLEAN / "unlocks.parquet"),
        ("outage_hours", cfg.CLEAN / "outage_hours.parquet"),
    ]:
        if path.exists():
            con.execute(f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM read_parquet('{path}');")
        else:
            log.warning("missing %s", path)

    sym_csv = cfg.RAW / "universe" / "symbols.csv"
    if sym_csv.exists():
        con.execute(f"CREATE OR REPLACE VIEW symbols AS SELECT * FROM read_csv_auto('{sym_csv}');")

    # --- RV bars = native KLINE_INTERVAL (15m); no 1m→5m downsample ---
    log.info("Building bars_rv from native %s klines …", iv)
    con.execute(
        """
        CREATE OR REPLACE TABLE bars_rv AS
        SELECT
            symbol,
            ts_utc AS ts_bar,
            open, high, low, close,
            volume,
            quote_volume,
            count AS trades,
            taker_buy_volume
        FROM klines
        WHERE close IS NOT NULL
        ORDER BY 1, 2;
        """
    )

    # --- hourly RV (sum of squared 15m log returns within the hour) ---
    log.info("Building rv_hourly …")
    min_n = cfg.RV_HOURLY_MIN_RETURNS
    con.execute(
        f"""
        CREATE OR REPLACE TABLE rv_hourly AS
        WITH r AS (
            SELECT
                symbol,
                ts_bar,
                time_bucket(INTERVAL '1 hour', ts_bar) AS hour_utc,
                ln(close / lag(close) OVER (PARTITION BY symbol ORDER BY ts_bar)) AS lr,
                quote_volume,
                trades,
                taker_buy_volume,
                volume
            FROM bars_rv
        )
        SELECT
            symbol,
            hour_utc,
            sum(lr * lr) AS rv,
            ln(greatest(sum(lr * lr), 1e-12)) AS log_rv,
            count(lr) AS n_returns,
            sum(lr) AS ret,
            sum(quote_volume) AS quote_volume,
            sum(trades) AS trades,
            sum(taker_buy_volume) / nullif(sum(volume), 0) AS taker_buy_share,
            (count(lr) < {min_n}) AS thin_hour
        FROM r
        WHERE lr IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, 2;
        """
    )

    log.info("Building rv_daily …")
    min_d = cfg.RV_DAILY_MIN_RETURNS
    con.execute(
        f"""
        CREATE OR REPLACE TABLE rv_daily AS
        WITH r AS (
            SELECT
                symbol,
                ts_bar,
                cast(ts_bar AS DATE) AS day_utc,
                ln(close / lag(close) OVER (PARTITION BY symbol ORDER BY ts_bar)) AS lr,
                quote_volume,
                trades
            FROM bars_rv
        )
        SELECT
            symbol,
            day_utc,
            sum(lr * lr) AS rv,
            ln(greatest(sum(lr * lr), 1e-12)) AS log_rv,
            count(lr) AS n_returns,
            sum(lr) AS ret,
            sum(quote_volume) AS quote_volume,
            sum(trades) AS trades,
            (count(lr) < {min_d}) AS thin_day
        FROM r
        WHERE lr IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, 2;
        """
    )

    # --- event calendar hourly (market-wide + coin funding) ---
    log.info("Building event_calendar_hourly …")
    con.execute(
        """
        CREATE OR REPLACE TABLE event_calendar_hourly AS
        WITH hours AS (
            SELECT DISTINCT hour_utc FROM rv_hourly
        ),
        macro AS (
            SELECT
                time_bucket(INTERVAL '1 hour', cast(event_time_utc AS TIMESTAMP)) AS hour_utc,
                max(CASE WHEN event_type = 'CPI' THEN 1 ELSE 0 END) AS cpi_hour,
                max(CASE WHEN event_type = 'NFP' THEN 1 ELSE 0 END) AS nfp_hour,
                max(CASE WHEN event_type = 'FOMC' THEN 1 ELSE 0 END) AS fomc_hour
            FROM macro_events
            GROUP BY 1
        ),
        exp AS (
            SELECT
                time_bucket(INTERVAL '1 hour', cast(expiry_time AS TIMESTAMP)) AS hour_utc,
                max(1) AS expiry_hour,
                any_value(expiry_type) AS expiry_type
            FROM expiries
            GROUP BY 1
        ),
        eq AS (
            SELECT
                time_bucket(INTERVAL '1 hour', cast(open_utc AS TIMESTAMP)) AS open_h,
                time_bucket(INTERVAL '1 hour', cast(close_utc AS TIMESTAMP)) AS close_h
            FROM equity_sessions
        )
        SELECT
            h.hour_utc,
            coalesce(m.cpi_hour, 0) AS cpi_hour,
            coalesce(m.nfp_hour, 0) AS nfp_hour,
            coalesce(m.fomc_hour, 0) AS fomc_hour,
            coalesce(e.expiry_hour, 0) AS expiry_hour,
            e.expiry_type,
            CASE WHEN h.hour_utc IN (SELECT open_h FROM eq) THEN 1 ELSE 0 END AS us_open_hour,
            CASE WHEN h.hour_utc IN (SELECT close_h FROM eq) THEN 1 ELSE 0 END AS us_close_hour,
            extract(hour FROM h.hour_utc)::INT AS hour_of_day,
            extract(dow FROM h.hour_utc)::INT AS day_of_week,
            CASE WHEN extract(dow FROM h.hour_utc) IN (0, 6) THEN 1 ELSE 0 END AS weekend
        FROM hours h
        LEFT JOIN macro m ON h.hour_utc = m.hour_utc
        LEFT JOIN exp e ON h.hour_utc = e.hour_utc
        ORDER BY 1;
        """
    )

    # Exact event windows (research primary)
    log.info("Building event_windows …")
    windows = cfg.EVENT_WINDOWS_MINUTES
    # Build from pandas for clarity / low complexity
    try:
        events = con.execute("SELECT event_type, event_time_utc, scheduled, source_url FROM macro_events").df()
    except Exception:
        events = pd.DataFrame()
    try:
        ex = con.execute("SELECT currency, expiry_time AS event_time_utc, expiry_type FROM expiries").df()
        if not ex.empty:
            ex = ex.rename(columns={"currency": "event_type"})
            ex["event_type"] = "EXPIRY_" + ex["event_type"].astype(str)
            ex["scheduled"] = True
            ex["source_url"] = "deribit"
            events = pd.concat([events, ex[["event_type", "event_time_utc", "scheduled", "source_url"]]], ignore_index=True)
    except Exception:
        pass

    ew_rows = []
    for _, r in events.iterrows():
        t0 = pd.Timestamp(r["event_time_utc"])
        for w in windows:
            ew_rows.append(
                {
                    "event_type": r["event_type"],
                    "event_time_utc": t0,
                    "window_minutes": w,
                    "window_start": t0 - pd.Timedelta(minutes=w),
                    "window_end": t0 + pd.Timedelta(minutes=w),
                    "scheduled": r.get("scheduled", True),
                }
            )
    ew = pd.DataFrame(ew_rows)
    con.execute("CREATE OR REPLACE TABLE event_windows AS SELECT * FROM ew")

    # Panel hourly
    log.info("Building panel_hourly …")
    test_start = str(cfg.TEST_START)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE panel_hourly AS
        SELECT
            r.*,
            e.cpi_hour, e.nfp_hour, e.fomc_hour, e.expiry_hour, e.expiry_type,
            e.us_open_hour, e.us_close_hour, e.hour_of_day, e.day_of_week, e.weekend,
            CASE WHEN r.hour_utc < TIMESTAMP '{test_start}' THEN 'design' ELSE 'test' END AS window
        FROM rv_hourly r
        LEFT JOIN event_calendar_hourly e ON r.hour_utc = e.hour_utc
        WHERE r.symbol IN ({", ".join(repr(s) for s in cfg.PRIMARY_SYMBOLS)});
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE panel_daily AS
        SELECT
            d.*,
            CASE WHEN cast(d.day_utc AS TIMESTAMP) < TIMESTAMP '{test_start}' THEN 'design' ELSE 'test' END AS window
        FROM rv_daily d
        WHERE d.symbol IN ({", ".join(repr(s) for s in cfg.PRIMARY_SYMBOLS)});
        """
    )

    # funding flag join helper table
    con.execute(
        """
        CREATE OR REPLACE TABLE funding_hours AS
        SELECT DISTINCT
            symbol,
            time_bucket(INTERVAL '1 hour', cast(funding_time_utc AS TIMESTAMP)) AS hour_utc
        FROM funding;
        """
    )

    n_h = con.execute("SELECT COUNT(*) FROM panel_hourly").fetchone()[0]
    n_d = con.execute("SELECT COUNT(*) FROM panel_daily").fetchone()[0]
    log.info("panel_hourly=%s  panel_daily=%s  db=%s", n_h, n_d, cfg.DB_PATH)
    con.close()


if __name__ == "__main__":
    main()
