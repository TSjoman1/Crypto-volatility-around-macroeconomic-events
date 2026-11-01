#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download funding-rate history for Phase-A symbols (archive + REST fallback)."""

from __future__ import annotations

import io
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from utils import (
    analysis_end,
    append_manifest,
    download_file,
    http_get,
    setup_logger,
    sha256_file,
)

log = setup_logger("03_download_funding")


def month_range(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m == 13:
            m = 1
            y += 1


def symbols() -> list[str]:
    return list(cfg.PRIMARY_SYMBOLS)


def archive_url(symbol: str, y: int, m: int) -> str:
    return (
        f"{cfg.BINANCE_VISION}/data/futures/um/monthly/fundingRate/{symbol}/"
        f"{symbol}-fundingRate-{y:04d}-{m:02d}.zip"
    )


def read_funding_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf:
        name = [n for n in zf.namelist() if n.endswith(".csv")][0]
        df = pd.read_csv(io.BytesIO(zf.read(name)))
    df.columns = [c.strip() for c in df.columns]
    # flexible rename
    colmap = {}
    for c in df.columns:
        cl = c.lower()
        if "time" in cl or "calc" in cl:
            colmap[c] = "funding_time"
        elif "rate" in cl:
            colmap[c] = "funding_rate"
        elif "interval" in cl:
            colmap[c] = "interval_hours"
    df = df.rename(columns=colmap)
    if "funding_time" not in df.columns:
        raise ValueError(f"No time column in {path}: {list(df.columns)}")
    df["funding_time"] = pd.to_numeric(df["funding_time"], errors="coerce")
    df["funding_rate"] = pd.to_numeric(df.get("funding_rate"), errors="coerce")
    if "interval_hours" in df.columns:
        df["interval_hours"] = pd.to_numeric(df["interval_hours"], errors="coerce")
    else:
        df["interval_hours"] = pd.NA
    return df[["funding_time", "funding_rate", "interval_hours"]]


def rest_funding(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Paginate fapi fundingRate."""
    rows = []
    start_ms = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime(end.year, end.month, end.day, 23, 59, tzinfo=timezone.utc).timestamp() * 1000)
    cur = start_ms
    while cur < end_ms:
        resp = http_get(
            f"{cfg.BINANCE_FAPI}/fapi/v1/fundingRate",
            params={"symbol": symbol, "startTime": cur, "endTime": end_ms, "limit": 1000},
        )
        batch = resp.json()
        if not batch:
            break
        rows.extend(batch)
        last = int(batch[-1]["fundingTime"])
        nxt = last + 1
        if nxt <= cur:
            break
        cur = nxt
        if len(batch) < 1000:
            break
    if not rows:
        return pd.DataFrame(columns=["funding_time", "funding_rate", "interval_hours"])
    df = pd.DataFrame(rows)
    df = df.rename(columns={"fundingTime": "funding_time", "fundingRate": "funding_rate"})
    df["funding_time"] = pd.to_numeric(df["funding_time"])
    df["funding_rate"] = pd.to_numeric(df["funding_rate"])
    df["interval_hours"] = pd.NA
    return df[["funding_time", "funding_rate", "interval_hours"]]


def main() -> None:
    end = analysis_end()
    out_dir = cfg.CLEAN / "funding"
    out_dir.mkdir(parents=True, exist_ok=True)

    for symbol in symbols():
        parts = []
        for y, m in month_range(cfg.START_DATE, end):
            url = archive_url(symbol, y, m)
            dest = cfg.RAW / "binance" / "funding" / symbol / f"{symbol}-fundingRate-{y:04d}-{m:02d}.zip"
            if not dest.exists():
                if not download_file(url, dest, log):
                    continue
            try:
                parts.append(read_funding_zip(dest))
                append_manifest(dest, url, sha256_file(dest), row_count=len(parts[-1]))
            except Exception as e:
                log.warning("archive read fail %s: %s", dest, e)

        if not parts:
            log.info("No archive funding for %s — REST fallback", symbol)
            df = rest_funding(symbol, cfg.START_DATE, end)
        else:
            df = pd.concat(parts, ignore_index=True)

        if df.empty:
            log.warning("No funding rows for %s", symbol)
            continue

        df = df.drop_duplicates("funding_time").sort_values("funding_time")
        df.insert(0, "symbol", symbol)
        df["funding_time_utc"] = pd.to_datetime(df["funding_time"], unit="ms", utc=True).dt.tz_localize(None)
        path = out_dir / f"{symbol}.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        append_manifest(path, "funding", sha256_file(path), row_count=len(df))
        log.info("%s funding rows=%d → %s", symbol, len(df), path)

        if not cfg.KEEP_RAW_ZIP_AFTER_PARQUET:
            raw = cfg.RAW / "binance" / "funding" / symbol
            if raw.exists():
                for z in raw.glob("*.zip"):
                    z.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
