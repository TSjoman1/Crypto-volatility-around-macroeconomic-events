# Data notes

Deviations from the original full-universe README and live decisions.

- Phase A default: `PRIMARY_SYMBOLS = BTCUSDT, ETHUSDT` only (`ENABLE_TOP_N_UNIVERSE = False`).
- Bar interval: **15m** (`KLINE_INTERVAL = "15m"`), not 1m — laptop disk/RAM choice; RV sampled at 15m.
- Raw ZIP files deleted after checksum + Parquet when `KEEP_RAW_ZIP_AFTER_PARQUET = False`.
- Event analysis prefers `event_windows` (exact ± minutes) over hour-bucket flags alone.
- FOMC calendar is hand-curated via `data/raw/macro/fomc.csv`.
- CPI/NFP: prefer `data/raw/macro/cpi_nfp_manual.csv` from BLS schedules — FRED API key signup is often Akamai-blocked outside the US.
- FRED remains optional if a key becomes available.
- 2026-11-01: DVOL BTC first timestamp 2021-03-24 00:00:00 (history may start ~2021)
- 2026-11-01: DVOL ETH first timestamp 2021-03-24 00:00:00 (history may start ~2021)
- 2026-11-01: Deribit API expiries BTC first=2026-11-01 08:00:00
- 2026-11-01: Expiry rule backfill BTC: 357 Fridays 2020-01-01→2026-10-31
- 2026-11-01: Deribit API expiries ETH first=2026-11-01 08:00:00
- 2026-11-01: Expiry rule backfill ETH: 357 Fridays 2020-01-01→2026-10-31
- 2026-11-01: FRED_API_KEY missing/placeholder — skip CPI/NFP; add a real key to .env and re-run 06
- 2026-11-01: Created empty fomc.csv template — fill before analysis
- 2026-11-01: FRED_API_KEY missing/placeholder — skip CPI/NFP; add a real key to .env and re-run 06
- 2026-11-01: No unlocks snapshot found — writing empty unlocks.parquet (secondary hypothesis deferred)
