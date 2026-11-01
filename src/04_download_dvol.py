#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download Deribit DVOL (hourly) for BTC and ETH."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from utils import analysis_end, append_manifest, http_get, note, setup_logger, sha256_file

log = setup_logger("04_download_dvol")


def fetch_dvol(currency: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Page get_volatility_index_data at resolution=3600."""
    rows = []
    # API wants ms
    cur = int(start.replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(end.replace(tzinfo=timezone.utc).timestamp() * 1000)
    # chunk ~30 days to keep payloads small
    step = 30 * 24 * 3600 * 1000
    while cur < end_ms:
        chunk_end = min(cur + step, end_ms)
        resp = http_get(
            f"{cfg.DERIBIT_API}/public/get_volatility_index_data",
            params={
                "currency": currency,
                "start_timestamp": cur,
                "end_timestamp": chunk_end,
                "resolution": 3600,
            },
        )
        data = resp.json().get("result", {}).get("data") or []
        rows.extend(data)
        cur = chunk_end + 1
    if not rows:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close"])
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close"])
    df = df.drop_duplicates("ts").sort_values("ts")
    return df


def main() -> None:
    out = cfg.CLEAN / "dvol"
    out.mkdir(parents=True, exist_ok=True)
    end = datetime.combine(analysis_end(), datetime.min.time())
    start = datetime(cfg.START_DATE.year, cfg.START_DATE.month, cfg.START_DATE.day)

    for currency in ("BTC", "ETH"):
        log.info("DVOL %s …", currency)
        df = fetch_dvol(currency, start, end)
        if df.empty:
            note(f"DVOL {currency}: no data returned for {start.date()}–{end.date()}")
            log.warning("empty DVOL %s", currency)
            continue
        df.insert(0, "currency", currency)
        df["ts_utc"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_localize(None)
        first = df["ts_utc"].iloc[0]
        note(f"DVOL {currency} first timestamp {first} (history may start ~2021)")
        path = out / f"{currency}.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        append_manifest(path, "deribit/dvol", sha256_file(path), row_count=len(df))
        log.info("%s DVOL rows=%d first=%s → %s", currency, len(df), first, path)


if __name__ == "__main__":
    main()
