#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deribit option expiry calendar (BTC/ETH) + rule-based Friday 08:00 UTC backfill."""

from __future__ import annotations

import calendar
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from utils import analysis_end, append_manifest, http_get, note, setup_logger, sha256_file

log = setup_logger("05_download_expiries")


def classify_expiry(ts: datetime) -> str:
    """daily / weekly / monthly / quarterly (Deribit: 08:00 UTC)."""
    if ts.weekday() != 4:  # Friday
        return "daily"
    # last Friday of month?
    last_day = calendar.monthrange(ts.year, ts.month)[1]
    d = date(ts.year, ts.month, last_day)
    while d.weekday() != 4:
        d -= timedelta(days=1)
    if ts.date() == d:
        if ts.month in (3, 6, 9, 12):
            return "quarterly"
        return "monthly"
    return "weekly"


def friday_rule_schedule(start: date, end: date) -> list[datetime]:
    out = []
    d = start
    # advance to Friday
    while d.weekday() != 4:
        d += timedelta(days=1)
    while d <= end:
        out.append(datetime(d.year, d.month, d.day, 8, 0, 0))
        d += timedelta(days=7)
    return out


def fetch_instruments(currency: str, expired: bool) -> list[dict]:
    resp = http_get(
        f"{cfg.DERIBIT_API}/public/get_instruments",
        params={"currency": currency, "kind": "option", "expired": str(expired).lower()},
    )
    return resp.json().get("result") or []


def main() -> None:
    out = cfg.CLEAN / "expiries"
    out.mkdir(parents=True, exist_ok=True)
    end = analysis_end()

    for currency in ("BTC", "ETH"):
        rows = []
        for expired in (True, False):
            try:
                inst = fetch_instruments(currency, expired)
            except Exception as e:
                log.warning("get_instruments %s expired=%s failed: %s", currency, expired, e)
                inst = []
            for it in inst:
                ms = it.get("expiration_timestamp")
                if not ms:
                    continue
                ts = datetime.utcfromtimestamp(ms / 1000.0)
                rows.append(
                    {
                        "currency": currency,
                        "expiry_time": ts,
                        "expiry_type": classify_expiry(ts),
                        "source": "deribit_api",
                    }
                )

        api_df = pd.DataFrame(rows).drop_duplicates(["currency", "expiry_time"]) if rows else pd.DataFrame()
        if api_df.empty:
            first_api = None
        else:
            first_api = api_df["expiry_time"].min()
            note(f"Deribit API expiries {currency} first={first_api}")

        # Rule backfill Fridays 08:00 UTC from START_DATE
        rule_start = cfg.START_DATE
        rule_end = first_api.date() - timedelta(days=1) if first_api is not None else end
        rule_rows = []
        if rule_start <= rule_end:
            for ts in friday_rule_schedule(rule_start, rule_end):
                rule_rows.append(
                    {
                        "currency": currency,
                        "expiry_time": ts,
                        "expiry_type": classify_expiry(ts),
                        "source": "rule",
                    }
                )
            note(f"Expiry rule backfill {currency}: {len(rule_rows)} Fridays {rule_start}→{rule_end}")

        df = pd.concat([api_df, pd.DataFrame(rule_rows)], ignore_index=True) if rule_rows or not api_df.empty else pd.DataFrame()
        if df.empty:
            log.warning("No expiries for %s", currency)
            continue
        df = df.drop_duplicates(["currency", "expiry_time"]).sort_values("expiry_time")
        path = out / f"{currency}.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        append_manifest(path, "deribit/expiries", sha256_file(path), row_count=len(df))
        log.info("%s expiries=%d → %s", currency, len(df), path)


if __name__ == "__main__":
    main()
