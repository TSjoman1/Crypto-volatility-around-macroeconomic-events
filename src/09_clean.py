#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quality pass over clean kline Parquet partitions (one symbol-month at a time).

Adds: is_gap, bad_print, zero_volume flags. Does not forward-fill prices.
Gap grid uses config.KLINE_INTERVAL (default 15m).
Writes logs/clean_summary.csv and data/clean/outage_hours.parquet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from utils import setup_logger

log = setup_logger("09_clean")


def flag_partition(path: Path) -> dict:
    df = pd.read_parquet(path)
    symbol = df["symbol"].iloc[0] if "symbol" in df.columns else path.parts[-2].split("=")[1]
    ts = pd.to_datetime(df["ts_utc"] if "ts_utc" in df.columns else df["open_time"], unit=None, errors="coerce")
    if np.issubdtype(df.get("open_time", pd.Series(dtype=float)).dtype, np.number) and "ts_utc" not in df.columns:
        ts = pd.to_datetime(df["open_time"], unit="ms", utc=True).tz_localize(None)

    df = df.copy()
    df["ts_utc"] = ts
    df = df.sort_values("ts_utc").drop_duplicates("ts_utc", keep="last")

    if df.empty:
        return {"symbol": symbol, "path": str(path), "rows": 0}

    freq = f"{int(cfg.RV_SAMPLING_MINUTES)}min"
    full = pd.date_range(df["ts_utc"].iloc[0], df["ts_utc"].iloc[-1], freq=freq)
    indexed = df.set_index("ts_utc").reindex(full)
    indexed["is_gap"] = indexed["close"].isna()
    indexed["symbol"] = symbol
    indexed = indexed.reset_index().rename(columns={"index": "ts_utc"})

    close = indexed["close"]
    high = indexed["high"]
    low = indexed["low"]
    lr = np.log(close / close.shift(1))
    # Wider threshold than 1m: 15m moves can be larger
    bad = (
        (high < low)
        | (close < low)
        | (close > high)
        | (lr.abs() > 0.40)
    )
    indexed["bad_print"] = bad.fillna(False) & ~indexed["is_gap"].fillna(False)
    indexed["zero_volume"] = (indexed["volume"].fillna(0) == 0) & ~indexed["is_gap"].fillna(False)
    indexed["interval"] = cfg.KLINE_INTERVAL

    indexed.to_parquet(path, index=False, compression="zstd")

    return {
        "symbol": symbol,
        "interval": cfg.KLINE_INTERVAL,
        "path": str(path),
        "rows": int((~indexed["is_gap"]).sum()),
        "gaps": int(indexed["is_gap"].sum()),
        "bad_prints": int(indexed["bad_print"].sum()),
        "zero_volume": int(indexed["zero_volume"].sum()),
        "first": str(indexed["ts_utc"].iloc[0]),
        "last": str(indexed["ts_utc"].iloc[-1]),
    }


def main() -> None:
    root = cfg.CLEAN / f"klines_{cfg.KLINE_INTERVAL}"
    if not root.exists():
        log.error("No clean klines at %s — run 02_download_klines.py first", root)
        sys.exit(1)

    parts = sorted(root.glob("year=*/month=*/symbol=*/part.parquet"))
    log.info("Partitions: %d", len(parts))
    summaries = []
    gap_hours = []

    for i, p in enumerate(parts, 1):
        log.info("[%d/%d] %s", i, len(parts), p)
        # gap expansion can grow RAM — process one month only
        s = flag_partition(p)
        summaries.append(s)

        # hourly gap counts for outage detection later
        df = pd.read_parquet(p, columns=["ts_utc", "symbol", "is_gap"])
        df["hour"] = pd.to_datetime(df["ts_utc"]).dt.floor("h")
        g = df.groupby(["hour", "symbol"], as_index=False)["is_gap"].mean()
        gap_hours.append(g)

    cfg.LOGS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summaries).to_csv(cfg.LOGS / "clean_summary.csv", index=False)

    if gap_hours:
        gh = pd.concat(gap_hours, ignore_index=True)
        # outage: >50% of symbols have gap_frac > 0.5 that hour
        wide = gh.pivot_table(index="hour", columns="symbol", values="is_gap", aggfunc="mean")
        frac_bad = (wide > 0.5).mean(axis=1)
        outages = frac_bad[frac_bad > 0.5].index.to_frame(index=False)
        outages.columns = ["hour_utc"]
        op = cfg.CLEAN / "outage_hours.parquet"
        outages.to_parquet(op, index=False)
        log.info("outage hours=%d → %s", len(outages), op)

    log.info("Wrote %s", cfg.LOGS / "clean_summary.csv")


if __name__ == "__main__":
    main()
