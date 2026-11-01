#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Laptop-scoped config for Scheduled, Not Spontaneous (crypto calendar → vol)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Research windows (sacred)
# ---------------------------------------------------------------------------
START_DATE = date(2020, 1, 1)
DESIGN_END = date(2023, 12, 31)
TEST_START = date(2024, 1, 1)
END_DATE = None  # None = last complete UTC day

# ---------------------------------------------------------------------------
# Universe — Phase A (default): BTC + ETH only
# Phase B (optional): expand TOP_N later without changing schema
# ---------------------------------------------------------------------------
PRIMARY_SYMBOLS = ("BTCUSDT", "ETHUSDT")
QUOTE_ASSET = "USDT"
CONTRACT_TYPE = "PERPETUAL"

# Keep False until Phase A (BTC/ETH) pipeline + QA is green
ENABLE_TOP_N_UNIVERSE = False
UNIVERSE_TOP_N = 10
UNIVERSE_LOOKBACK_DAYS = 30
MIN_HISTORY_DAYS = 60

EXCLUDE_BASES = {
    "USDC", "BUSD", "TUSD", "USDP", "DAI", "FDUSD", "USDE", "PYUSD", "EUR",
    "WBTC", "WBETH", "BTCDOM", "DEFI", "FOOTBALL", "BLUEBIRD",
}

# ---------------------------------------------------------------------------
# Bars / realised variance (laptop: 15m native, not 1m)
# ---------------------------------------------------------------------------
KLINE_INTERVAL = "15m"         # Binance Vision interval folder name
RV_SAMPLING_MINUTES = 15       # RV from these bars directly (no 1m→5m step)
RV_HOURLY_MIN_RETURNS = 3      # of 4 possible 15m returns per hour
RV_DAILY_MIN_RETURNS = 80      # of 96 possible 15m returns per day
EVENT_WINDOWS_MINUTES = (15, 30, 60, 120)  # ±15m = one bar each side at 15m resolution

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA = ROOT / "data"
RAW = DATA / "raw"
CLEAN = DATA / "clean"
DB_PATH = ROOT / "db" / "research.duckdb"
LOGS = ROOT / "logs"
DOCS = ROOT / "docs"
MANIFEST = DATA / "manifest.csv"
CHECKSUMS = DATA / "checksums.txt"
FROZEN_SPEC = ROOT / "specs" / "frozen_spec.yaml"

# ---------------------------------------------------------------------------
# Download politeness / laptop limits
# ---------------------------------------------------------------------------
HTTP_MAX_RPS = 4.0
HTTP_TIMEOUT = 60
KEEP_RAW_ZIP_AFTER_PARQUET = False  # save disk after checksum OK + parquet written
DUCKDB_THREADS = 2

# Binance Vision
BINANCE_VISION = "https://data.binance.vision"
BINANCE_S3_LIST = (
    "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
    "?delimiter=/&prefix=data/futures/um/monthly/klines/"
)
BINANCE_FAPI = "https://fapi.binance.com"
DERIBIT_API = "https://www.deribit.com/api/v2"
