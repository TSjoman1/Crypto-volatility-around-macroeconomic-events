#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download Binance USD-M perpetual klines (Vision archive).

Default interval: 15m (config.KLINE_INTERVAL) for laptop disk/RAM.
Processes PRIMARY_SYMBOLS one symbol-month at a time, verifies .CHECKSUM,
writes Parquet under data/clean; optionally drops zip after.
"""

from __future__ import annotations

import io
import sys
import zipfile
from datetime import date
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
    setup_logger,
    sha256_file,
    verify_checksum,
)

log = setup_logger("02_download_klines")

COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "count", "taker_buy_volume",
    "taker_buy_quote_volume", "ignore",
]


def month_range(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def load_symbols() -> list[str]:
    path = cfg.RAW / "universe" / "symbols.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not cfg.ENABLE_TOP_N_UNIVERSE:
            return [s for s in cfg.PRIMARY_SYMBOLS if s in set(df["symbol"])] or list(cfg.PRIMARY_SYMBOLS)
        return df["symbol"].astype(str).tolist()
    return list(cfg.PRIMARY_SYMBOLS)


def zip_url(symbol: str, y: int, m: int) -> str:
    iv = cfg.KLINE_INTERVAL
    return (
        f"{cfg.BINANCE_VISION}/data/futures/um/monthly/klines/{symbol}/{iv}/"
        f"{symbol}-{iv}-{y:04d}-{m:02d}.zip"
    )


def klines_clean_root() -> Path:
    return cfg.CLEAN / f"klines_{cfg.KLINE_INTERVAL}"


def klines_raw_root() -> Path:
    return cfg.RAW / "binance" / f"klines_{cfg.KLINE_INTERVAL}"


def read_klines_zip(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        name = [n for n in zf.namelist() if n.endswith(".csv")][0]
        raw = zf.read(name)
    # detect header
    first = raw.split(b"\n", 1)[0].decode("utf-8", errors="replace").lower()
    has_header = "open" in first
    df = pd.read_csv(io.BytesIO(raw), header=0 if has_header else None)
    if not has_header:
        df.columns = COLS[: len(df.columns)]
    else:
        # normalize names
        df.columns = [str(c).strip() for c in df.columns]
        rename = {c: COLS[i] for i, c in enumerate(df.columns) if i < len(COLS)}
        df = df.rename(columns=rename)
    keep = [c for c in COLS if c in df.columns and c != "ignore"]
    df = df[keep].copy()
    # ms timestamps (futures)
    df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce").astype("int64")
    for c in ["open", "high", "low", "close", "volume", "quote_volume",
              "taker_buy_volume", "taker_buy_quote_volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "count" in df.columns:
        df["count"] = pd.to_numeric(df["count"], errors="coerce").astype("Int64")
    return df


def write_clean_parquet(df: pd.DataFrame, symbol: str, y: int, m: int) -> Path:
    out = klines_clean_root() / f"year={y:04d}" / f"month={m:02d}" / f"symbol={symbol}"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "part.parquet"
    df = df.copy()
    df.insert(0, "symbol", symbol)
    df["interval"] = cfg.KLINE_INTERVAL
    df["ts_utc"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_localize(None)
    df.to_parquet(path, index=False, compression="zstd")
    return path


def main() -> None:
    symbols = load_symbols()
    end = analysis_end()
    start = cfg.START_DATE
    iv = cfg.KLINE_INTERVAL
    log.info("Interval=%s  Symbols=%s  %s → %s", iv, symbols, start, end)

    for symbol in symbols:
        for y, m in month_range(start, end):
            # skip future incomplete month beyond last complete day
            if date(y, m, 1) > end:
                continue
            url = zip_url(symbol, y, m)
            dest = klines_raw_root() / symbol / f"{symbol}-{iv}-{y:04d}-{m:02d}.zip"
            csum_url = url + ".CHECKSUM"
            csum_path = dest.with_suffix(dest.suffix + ".CHECKSUM")

            clean_path = (
                klines_clean_root() / f"year={y:04d}" / f"month={m:02d}"
                / f"symbol={symbol}" / "part.parquet"
            )
            if clean_path.exists():
                log.info("skip existing clean %s %04d-%02d", symbol, y, m)
                continue

            if not dest.exists():
                ok = download_file(url, dest, log)
                if not ok:
                    continue
                if not download_file(csum_url, csum_path, log):
                    log.error("Missing checksum for %s", dest)
                    continue
                if not verify_checksum(dest, csum_path, log):
                    continue
            elif csum_path.exists():
                if not verify_checksum(dest, csum_path, log):
                    continue

            try:
                df = read_klines_zip(dest)
            except Exception as e:
                log.error("read fail %s: %s", dest, e)
                continue
            pq = write_clean_parquet(df, symbol, y, m)
            sha = sha256_file(dest)
            append_manifest(dest, url, sha, row_count=len(df))
            append_manifest(pq, url, sha256_file(pq), row_count=len(df))
            log.info("%s %04d-%02d rows=%d → %s", symbol, y, m, len(df), pq)

            if not cfg.KEEP_RAW_ZIP_AFTER_PARQUET:
                # keep checksum for audit; drop zip to save disk
                dest.unlink(missing_ok=True)
                log.info("removed zip %s (KEEP_RAW_ZIP_AFTER_PARQUET=False)", dest.name)


if __name__ == "__main__":
    main()
