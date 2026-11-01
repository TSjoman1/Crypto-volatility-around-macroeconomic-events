# Analysis: Crypto Never Sleeps, but It Waits for the Fed

This folder holds the analysis behind the paper *Crypto Never Sleeps, but It Waits for the Fed:
Scheduled US Macro Events and Bitcoin Volatility*. The data pipeline that builds the inputs is
described in `README.md`.

## What is here

| Path | What it is |
| --- | --- |
| `docs/FROZEN_SPEC.md` | Pre-analysis plan: hypotheses, models, tests and decision rules, frozen on 1 Nov 2026 before any 2024+ statistic was computed, plus the recorded results |
| `analysis/frozen_analysis.py` | The frozen script. Produces every confirmatory result (H1a to H6) and the pre-specified robustness checks |
| `analysis/exploratory_analysis.py` | Descriptive, exploratory and post hoc analyses (paper Sections 4, 6, 7.2 to 7.3, Appendix A) and the data behind Figures 1 to 3. Imports the frozen script's functions |
| `results/dry_run/` | Frozen script in dry mode: fitted on 2020 to 2022, evaluated on 2023 |
| `results/test_run/` | The single test run: fitted on 2020 to 2023, evaluated on Jan 2024 to Sep 2026, with its console log |
| `results/exploratory/` | Output of the exploratory script and the figure data (CSV) |
| `CHECKSUMS.sha256` | SHA-256 of the frozen script and the five input files used in the test run |

## Inputs

| File | Content |
| --- | --- |
| `panel_hourly.parquet` | Hourly BTCUSDT and ETHUSDT panel, Binance USD-M perpetuals, 2020-01-01 to 2026-09-30, RV from 15-minute returns |
| `BTC.parquet`, `ETH.parquet` | Deribit DVOL hourly candles from 2021-03-24 |
| `cpi_nfp_manual.csv` | CPI and jobs-report release dates (BLS schedules) |
| `fomc.csv` | FOMC statement dates and times, scheduled and unscheduled (Federal Reserve calendars) |

## How to reproduce

```bash
pip install -r requirements-analysis.txt

# 1. Verify the inputs are the frozen ones (run where the files are; adjust paths in the file if needed)
sha256sum -c CHECKSUMS.sha256

# 2. Dry run (design window only)
python analysis/frozen_analysis.py --mode dry --panel panel_hourly.parquet \
  --dvol-btc BTC.parquet --dvol-eth ETH.parquet --cpi-nfp cpi_nfp_manual.csv \
  --fomc fomc.csv --out results/dry_run

# 3. Test run (the confirmatory results)
SPEC_REGISTERED=yes python analysis/frozen_analysis.py --mode test --panel panel_hourly.parquet \
  --dvol-btc BTC.parquet --dvol-eth ETH.parquet --cpi-nfp cpi_nfp_manual.csv \
  --fomc fomc.csv --out results/test_run

# 4. Descriptive, exploratory and post hoc results
SPEC_REGISTERED=yes python analysis/exploratory_analysis.py --panel panel_hourly.parquet \
  --dvol-btc BTC.parquet --dvol-eth ETH.parquet --cpi-nfp cpi_nfp_manual.csv \
  --fomc fomc.csv --out results/exploratory
```

`SPEC_REGISTERED=yes` means "spec frozen". The study was not registered with an external
registry; the freeze rests on the dated specification, its version history and the checksums.

## Results in brief

Seven of eight pre-specified hypotheses are confirmed at the Bonferroni level 0.00625 in the
test window (Jan 2024 to Sep 2026):

| ID | Result | Verdict |
| --- | --- | --- |
| H1a | FOMC statement hour: realised variance +459% vs matched normal hours (t 8.2) | Confirmed |
| H1b | CPI release hour: +268% (t 5.8) | Confirmed |
| H1c | Jobs-report release hour: +163% (t 4.8) | Confirmed |
| H2 | Calendar model vs HAR: 7.9% lower MSE | Confirmed |
| H3 | Macro event hours: 51% lower MSE | Confirmed |
| H4 | With DVOL in both models: 8.7% lower MSE | Confirmed |
| H5 | Lagged volume: 2.2% lower MSE | Confirmed |
| H6 | Pre-CPI rise in DVOL: −0.8 points (t −0.9) | Not supported |

## Notes and known issues

- **Outage hour.** 2024-10-28 20:00 UTC has zero volume and zero RV for both coins. It stays in
  the primary analysis and drives the H5 QLIKE failure; see paper Section 7.3.
- **Post hoc checks.** Three robustness checks listed in the specification (March 2020 dropped,
  shutdown-shifted release days dropped, event effects by year) were not in the frozen script and
  are produced by `exploratory_analysis.py`.
- **Placebo matching for DVOL.** The exploratory script matches placebo hours to the weekdays and
  hours of the events inside each window. An earlier pilot used weekdays from 2020 events, before
  DVOL existed; the paper reports the matched version. The CPI result (H6) is the same either way.
- **Fallback Parquet reader.** `frozen_analysis.py` falls back to a bundled minimal reader only if
  `pandas.read_parquet` fails; with `pyarrow` installed it is never used.
