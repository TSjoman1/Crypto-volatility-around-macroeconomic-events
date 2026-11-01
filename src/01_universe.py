#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build symbol universe. Phase A: BTCUSDT + ETHUSDT (+ optional archive discovery)."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from utils import http_get, setup_logger

log = setup_logger("01_universe")


def list_archive_usdt_perps() -> list[str]:
    """List USDT-margined perpetual symbols from Binance Vision S3 listing."""
    symbols: list[str] = []
    marker = None
    ns = {"": "http://s3.amazonaws.com/doc/2006-03-01/"}
    while True:
        url = cfg.BINANCE_S3_LIST
        if marker:
            url = url + f"&marker={marker}"
        resp = http_get(url)
        root = ET.fromstring(resp.content)
        prefixes = []
        for cp in root.findall("CommonPrefixes", ns):
            pref = cp.findtext("Prefix", default="", namespaces=ns) or ""
            # data/futures/um/monthly/klines/BTCUSDT/
            parts = pref.strip("/").split("/")
            if parts:
                symbols.append(parts[-1])
                prefixes.append(pref)
        truncated = (root.findtext("IsTruncated", default="false", namespaces=ns) or "").lower() == "true"
        if not truncated or not prefixes:
            break
        marker = prefixes[-1]

    out = []
    for s in sorted(set(symbols)):
        if not s.endswith(cfg.QUOTE_ASSET):
            continue
        # drop dated quarterly delivery contracts
        if "_" in s:
            continue
        base = s[: -len(cfg.QUOTE_ASSET)]
        if base in cfg.EXCLUDE_BASES:
            continue
        out.append(s)
    return out


def enrich_exchange_info(symbols: list[str]) -> pd.DataFrame:
    rows = []
    live = {}
    try:
        resp = http_get(f"{cfg.BINANCE_FAPI}/fapi/v1/exchangeInfo")
        for s in resp.json().get("symbols", []):
            live[s["symbol"]] = s
    except Exception as e:
        log.warning("exchangeInfo failed: %s — marking archive-only as DELISTED", e)

    for sym in symbols:
        base = sym[: -len(cfg.QUOTE_ASSET)]
        meta = live.get(sym, {})
        status = meta.get("status", "DELISTED")
        onboard = meta.get("onboardDate")
        rows.append(
            {
                "symbol": sym,
                "base_asset": base,
                "status": status,
                "onboard_date": pd.to_datetime(onboard, unit="ms", utc=True).date() if onboard else pd.NaT,
                "last_date": pd.NaT,
                "is_1000_prefixed": base.startswith("1000"),
                "phase_a_primary": sym in cfg.PRIMARY_SYMBOLS,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    out_dir = cfg.RAW / "universe"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not cfg.ENABLE_TOP_N_UNIVERSE:
        log.info("Phase A: primary symbols only %s", cfg.PRIMARY_SYMBOLS)
        symbols = list(cfg.PRIMARY_SYMBOLS)
    else:
        log.info("Listing archive symbols (Phase B) …")
        symbols = list_archive_usdt_perps()
        # Always ensure primaries included
        for s in cfg.PRIMARY_SYMBOLS:
            if s not in symbols:
                symbols.append(s)
        log.info("Archive USDT perps kept: %d", len(symbols))

    df = enrich_exchange_info(symbols)
    path = out_dir / "symbols.csv"
    df.to_csv(path, index=False)
    log.info("Wrote %s (%d symbols)", path, len(df))


if __name__ == "__main__":
    main()
