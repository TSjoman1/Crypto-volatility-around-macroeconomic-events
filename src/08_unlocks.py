#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load optional token-unlock snapshot (secondary hypothesis). Phase A: optional."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from utils import append_manifest, note, setup_logger, sha256_file

log = setup_logger("08_unlocks")


def main() -> None:
    raw_dir = cfg.RAW / "unlocks"
    raw_dir.mkdir(parents=True, exist_ok=True)
    snaps = sorted(raw_dir.glob("unlocks_snapshot_*.csv"))
    out = cfg.CLEAN / "unlocks.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)

    if not snaps:
        note("No unlocks snapshot found — writing empty unlocks.parquet (secondary hypothesis deferred)")
        df = pd.DataFrame(
            columns=["base_asset", "unlock_time_utc", "tokens_unlocked", "pct_of_circulating", "category", "source", "snapshot_date"]
        )
        df.to_parquet(out, index=False)
        log.info("empty unlocks → %s", out)
        return

    path = snaps[-1]
    snap_date = path.stem.replace("unlocks_snapshot_", "")
    df = pd.read_csv(path)
    df["snapshot_date"] = snap_date
    df.to_parquet(out, index=False, compression="zstd")
    append_manifest(out, str(path), sha256_file(out), row_count=len(df))
    note(f"Loaded unlocks snapshot {path.name}")
    log.info("unlocks rows=%d from %s", len(df), path.name)


if __name__ == "__main__":
    main()
