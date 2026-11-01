# Scheduled, Not Spontaneous — Data Pipeline (laptop scope)

Research database for **"Scheduled, Not Spontaneous: Do Known Events Predict Crypto Volatility?"**

## Scope (Phase A — default)

Keep the **same research questions**, smaller warehouse:

| In scope | Deferred |
|----------|----------|
| **BTCUSDT + ETHUSDT** **15m** perps (2020→) | 1m bars; top-N cross-section (`ENABLE_TOP_N_UNIVERSE`) |
| Funding, Deribit DVOL, expiries | Full delisted multi-coin archive |
| CPI / NFP / FOMC, NYSE open/close | Unlocks as primary (optional secondary) |
| Hourly + daily RV panels + **exact event windows** | Multi-exchange |

Turn on Phase B later by setting `ENABLE_TOP_N_UNIVERSE = True` in `config.py` — schema stays the same.

## Research questions this stack can still answer

1. Do **CPI / NFP / FOMC** change BTC/ETH realised vol in exact ±15/30/60/120m windows?  
2. Do **Deribit expiries** (08:00 UTC) show vol effects vs matched non-event hours?  
3. Do **funding timestamps** matter for RV (vs clock-of-day controls)?  
4. Do **US equity open/close** hours matter for crypto RV?  
5. How does **DVOL** (IV) move around the same events vs realised vol?

Primary sample: **BTC & ETH**. Design window only until the frozen spec is registered.

## Sacred split

- `DESIGN_END = 2023-12-31`
- `TEST_START = 2024-01-01`
- Analysis must use `utils.load_panel(..., mode="design"|"test")`
- `mode="test"` requires `specs/frozen_spec.yaml` **and** `SPEC_REGISTERED=yes`

## Setup

```bash
cd crypto-calendar-vol
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add FRED_API_KEY
```

## Run order

```bash
python src/01_universe.py
python src/02_download_klines.py      # longest; one symbol-month at a time
python src/03_download_funding.py
python src/04_download_dvol.py
python src/05_download_expiries.py
python src/06_macro_calendar.py       # fill data/raw/macro/fomc.csv
python src/07_market_hours.py
python src/08_unlocks.py              # optional
python src/09_clean.py
python src/10_build_db.py
python src/11_qa_report.py
```

Each step is idempotent/resumable. With `KEEP_RAW_ZIP_AFTER_PARQUET = False`, zips are deleted after checksum + Parquet to save disk.

## Layout

See `config.py` for paths. Outputs: `data/clean/` (Parquet), `db/research.duckdb`, `docs/`.

## Agent rules

1. Never overwrite raw downloads; clean → `data/clean/`.  
2. Verify Binance `.CHECKSUM` (SHA-256); quarantine failures.  
3. All timestamps UTC.  
4. No test-window return/vol/volume **levels** in QA or charts until spec frozen.  
5. Log deviations in `docs/data_notes.md`.  
6. Be polite to APIs (~4 req/s, backoff).

## Hand-off checklist

- [ ] `data/manifest.csv` populated  
- [ ] `docs/qa_report.md` (counts only)  
- [ ] `docs/data_notes.md` updated  
- [ ] `panel_hourly` / `panel_daily` / `event_windows` in DuckDB  
- [ ] Test mode blocked without frozen spec  
- [ ] Human registers `specs/frozen_spec.yaml` before any test analysis  
