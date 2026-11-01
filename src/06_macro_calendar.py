#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
US macro calendar.

Preferred (no FRED account): hand CSVs under data/raw/macro/
  - cpi_nfp_manual.csv  (CPI / NFP release dates from BLS schedules)
  - fomc.csv            (FOMC decision dates)

Optional: FRED vintagedates if FRED_API_KEY is set (often blocked outside US).
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from utils import analysis_end, append_manifest, et_to_utc, http_get, note, setup_logger, sha256_file

log = setup_logger("06_macro_calendar")
load_dotenv(cfg.ROOT / ".env")


def fred_vintagedates(series_id: str, api_key: str) -> list[date]:
    resp = http_get(
        "https://api.stlouisfed.org/fred/series/vintagedates",
        params={"series_id": series_id, "api_key": api_key, "file_type": "json"},
    )
    vintages = resp.json().get("vintage_dates") or []
    out = []
    for v in vintages:
        d = pd.to_datetime(v).date()
        if cfg.START_DATE <= d <= analysis_end():
            out.append(d)
    return out


def filter_monthly_releaseish(dates: list[date]) -> list[date]:
    """
    Heuristic: keep ~1 date per calendar month (first vintage in month).
    Still cross-check vs BLS schedule; write survivors for human review.
    """
    by_m = {}
    for d in sorted(dates):
        key = (d.year, d.month)
        if key not in by_m:
            by_m[key] = d
    return list(by_m.values())


def build_release_rows(event_type: str, days: list[date], hour: int = 8, minute: int = 30) -> pd.DataFrame:
    rows = []
    for d in days:
        rows.append(
            {
                "event_type": event_type,
                "event_time_utc": et_to_utc(d, hour, minute),
                "scheduled": True,
                "source_url": f"FRED vintagedates filtered ({event_type})",
            }
        )
    return pd.DataFrame(rows)


def ensure_fomc_template() -> Path:
    path = cfg.RAW / "macro" / "fomc.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            "meeting_end_date,statement_time_et,scheduled,source_url,notes\n",
            encoding="utf-8",
        )
        note("Created empty fomc.csv template — fill before analysis")
    return path


def ensure_cpi_nfp_template() -> Path:
    path = cfg.RAW / "macro" / "cpi_nfp_manual.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            "event_type,release_date,scheduled,source_url,notes\n",
            encoding="utf-8",
        )
    return path


def load_cpi_nfp_manual(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, comment="#")
    if df.empty or "release_date" not in df.columns:
        return pd.DataFrame(columns=["event_type", "event_time_utc", "scheduled", "source_url"])
    rows = []
    for _, r in df.iterrows():
        et = str(r.get("event_type", "")).strip().upper()
        if et not in ("CPI", "NFP"):
            continue
        d = pd.to_datetime(r["release_date"]).date()
        if d < cfg.START_DATE or d > analysis_end():
            continue
        src = r.get("source_url") or "cpi_nfp_manual.csv"
        rows.append(
            {
                "event_type": et,
                "event_time_utc": et_to_utc(d, 8, 30),
                "scheduled": bool(r["scheduled"]) if "scheduled" in r and pd.notna(r["scheduled"]) else True,
                "source_url": src,
            }
        )
    return pd.DataFrame(rows)


def _parse_hhmm(val, default_h: int = 14, default_m: int = 0) -> tuple[int, int]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default_h, default_m
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return default_h, default_m
    parts = s.split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def load_fomc(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, comment="#")
    if df.empty or "meeting_end_date" not in df.columns:
        return pd.DataFrame(columns=["event_type", "event_time_utc", "scheduled", "source_url"])
    rows = []
    for _, r in df.iterrows():
        d = pd.to_datetime(r["meeting_end_date"]).date()
        if d < cfg.START_DATE or d > analysis_end():
            continue
        hh, mm = _parse_hhmm(r.get("statement_time_et"), 14, 0)
        rows.append(
            {
                "event_type": "FOMC",
                "event_time_utc": et_to_utc(d, hh, mm),
                "scheduled": bool(r.get("scheduled", True)),
                "source_url": r.get("source_url", "fomc.csv"),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    out_dir = cfg.CLEAN
    out_dir.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("FRED_API_KEY", "").strip()

    frames = []

    # 1) Manual BLS dates (primary path when FRED site is blocked)
    manual_path = ensure_cpi_nfp_template()
    manual = load_cpi_nfp_manual(manual_path)
    if not manual.empty:
        frames.append(manual)
        log.info("Loaded %d CPI/NFP rows from %s", len(manual), manual_path.name)
    else:
        log.warning(
            "cpi_nfp_manual.csv is empty — fill from BLS schedules "
            "(see data/raw/macro/README.md). FRED signup is often blocked outside the US."
        )

    # 2) Optional FRED if a real key works
    placeholder = (not api_key) or api_key.startswith("your_key")
    if not placeholder and manual.empty:
        try:
            cpi_days = filter_monthly_releaseish(fred_vintagedates("CPIAUCSL", api_key))
            nfp_days = filter_monthly_releaseish(fred_vintagedates("PAYEMS", api_key))
            raw = cfg.RAW / "macro"
            raw.mkdir(parents=True, exist_ok=True)
            pd.DataFrame({"vintage_date": cpi_days}).to_csv(raw / "cpi_vintages_filtered.csv", index=False)
            pd.DataFrame({"vintage_date": nfp_days}).to_csv(raw / "jobs_vintages_filtered.csv", index=False)
            note("CPI/NFP from FRED vintages; still cross-check BLS schedules before freezing spec")
            frames.append(build_release_rows("CPI", cpi_days))
            frames.append(build_release_rows("NFP", nfp_days))
        except Exception as e:
            note(f"FRED vintagedates failed ({e})")
            log.error("FRED failed: %s", e)

    fomc_path = ensure_fomc_template()
    frames.append(load_fomc(fomc_path))

    nonempty = [f for f in frames if f is not None and not f.empty]
    cols = ["event_type", "event_time_utc", "scheduled", "source_url"]
    if nonempty:
        df = pd.concat(nonempty, ignore_index=True).sort_values("event_time_utc")
    else:
        df = pd.DataFrame(columns=cols)
        log.warning("macro_events empty — fill cpi_nfp_manual.csv and/or fomc.csv, then re-run 06")
    path = out_dir / "macro_events.parquet"
    df.to_parquet(path, index=False, compression="zstd")
    append_manifest(path, "macro", sha256_file(path), row_count=len(df))
    log.info("macro_events rows=%d → %s", len(df), path)


if __name__ == "__main__":
    main()
