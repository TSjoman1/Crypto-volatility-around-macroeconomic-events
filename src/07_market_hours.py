#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NYSE session open/close (UTC) via pandas_market_calendars."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from utils import analysis_end, append_manifest, setup_logger, sha256_file

log = setup_logger("07_market_hours")


def main() -> None:
    end = analysis_end()
    nyse = mcal.get_calendar("NYSE")
    sched = nyse.schedule(start_date=str(cfg.START_DATE), end_date=str(end))
    df = sched.reset_index().rename(columns={"index": "date", "market_open": "open_utc", "market_close": "close_utc"})
    # some versions use 'date' already as index name
    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["open_utc"] = pd.to_datetime(df["open_utc"], utc=True).dt.tz_localize(None)
    df["close_utc"] = pd.to_datetime(df["close_utc"], utc=True).dt.tz_localize(None)
    # early close: session shorter than ~6.5h
    dur = (pd.to_datetime(df["close_utc"]) - pd.to_datetime(df["open_utc"])).dt.total_seconds() / 3600.0
    df["early_close"] = dur < 6.0

    path = cfg.CLEAN / "equity_sessions.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="zstd")
    append_manifest(path, "NYSE calendar", sha256_file(path), row_count=len(df))
    log.info("equity_sessions rows=%d → %s", len(df), path)


if __name__ == "__main__":
    main()
