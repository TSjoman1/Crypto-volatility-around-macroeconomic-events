# Frozen Spec: Crypto Never Sleeps, but It Waits for the Fed

Nov 1, 2026 · @Toni

Pre-analysis plan for "Crypto Never Sleeps, but It Waits for the Fed: Scheduled US Macro Events and Bitcoin Volatility". It fixes the hypotheses, models, tests and decision rules before any 2024+ data is analysed.

## Status

**Frozen, self-certified.** The specification is not registered with a third party. It is frozen by the file checksums and the freeze record in Section 9, and by this document's version history. Until the freeze record is completed, no statistic may be computed on data from 1 January 2024 onwards, except the row and event counts listed in Section 3.

Freeze procedure, in this order:

1. Confirm the panel is the one listed in Section 9 (the existing 15-minute panel; no rebuild).
2. Run the analysis script in **design mode** as a dry run and record its figures (done; Sections 2 and 8).
3. Record SHA-256 checksums of the panel, DVOL, calendar files and the analysis script in Section 9.
4. Settle the open choices: H6 stays confirmatory; frozen design-window coefficients are the primary estimation.
5. Complete the freeze record in Section 9, then run the script in **test mode** exactly once.
6. Report every result in Section 6's order, whatever it shows. Any deviation from this plan is reported as a deviation, with its reason.

After step 5, nothing in Sections 2 to 6 may change. Because the freeze is self-certified, the paper states this plainly as a limitation.

## Research question and hypotheses

Crypto trades around the clock, yet its largest volatility spikes may be set by the US macro calendar. The paper asks whether scheduled US releases (FOMC statements, CPI and the jobs report) raise Bitcoin and Ether volatility, and whether a forecast that knows the calendar beats one that does not, including after implied volatility.

Eight confirmatory hypotheses, all one-sided, are tested once on the test window:

| ID | Hypothesis | Test statistic | Dry run, 2023 (Section 8) |
| --- | --- | --- | --- |
| H1a | Realised variance in the FOMC statement hour exceeds matched normal hours | Mean log difference per event, t-test | +207% (t 2.1, 8 events) |
| H1b | Realised variance in the CPI release hour exceeds matched normal hours | Same | +222% (t 2.5, 12 events) |
| H1c | Realised variance in the jobs-report release hour exceeds matched normal hours | Same | +69% (t 1.4, 12 events) |
| H2 | The full calendar model (M4) forecasts hourly volatility better than HAR (M1) across all hours | Clark–West, Newey–West 24 lags | 5.4% lower MSE (t 19) |
| H3 | M4 forecasts better than HAR with time-of-day only (M2) in macro event hours | Clark–West differential averaged per event, t-test | 29% lower MSE (t 4.6) |
| H4 | With DVOL in both models, the calendar model (M4+IV) beats HAR+IV across all hours | Clark–West, Newey–West 24 lags | 6.9% lower MSE (t 22) |
| H5 | Lagged volume (M5) improves on the calendar model (M4) | Clark–West, Newey–West 24 lags | 1.7% lower MSE (t 11) |
| H6 | BTC and ETH implied volatility rises more in the 48 hours before CPI than on matched placebo days | Event-minus-placebo run-up, t-test | +2.6 pp (t 2.6, 12 events) |

The dry-run figures are recorded for transparency and do not enter any test. They come from the same 15-minute panel the test will use.

## Data, sample and windows

The primary sample is the Binance USD-M perpetual futures BTCUSDT and ETHUSDT, hourly, in UTC.

| Item | Rule |
| --- | --- |
| Realised variance (RV) | Sum of squared 15-minute log returns within each UTC hour (4 returns). Hours with fewer than 3 valid returns are dropped |
| Zero-RV hours | Floored at 1e-12 before taking logs, and listed in the results |
| Outage hours | Kept in the primary analysis; dropped in a robustness check |
| Volume | Quote volume (USDT) summed over the hour |
| Implied volatility | Deribit DVOL hourly close, BTC and ETH. The candle that closes at the start of hour H is the value known for forecasting hour H |
| Design window | 1 Jan 2020 to 31 Dec 2023 (DVOL models from 24 Mar 2021) |
| Test window | 1 Jan 2024 to 30 Sep 2026 (the last complete month in the panel) |

**Estimation.** Every model is estimated once on the full design window. The coefficients are then frozen and applied to the test window without re-estimation. Matched control means for H1 and the placebo set for H6 are computed within the test window itself.

**Permitted test-window counts before the run:** rows, missing hours, zero-RV hours and event counts. No returns, volatility or volume levels.

**Scope.** The study is limited to BTCUSDT and ETHUSDT. No other coins are added before or after the test.

## Event calendar

All event times are converted from New York time to UTC per date, so daylight saving is handled. Each event flags the UTC hour that contains it.

| Event | Source file | Time (New York) | Hours flagged | Use |
| --- | --- | --- | --- | --- |
| FOMC statement, scheduled | `fomc.csv`, `scheduled = True` | 14:00 (press conference 14:30) | Statement hour and next hour | Forecast feature; H1a uses the statement hour |
| FOMC, unscheduled | `fomc.csv`, `scheduled = False` | As listed | Statement hour and next hour | Excluded from forecast features (not known in advance); excluded from H1a controls; reported descriptively |
| CPI | `cpi_nfp_manual.csv` | 08:30 | Release hour and next hour | Forecast feature; H1b, H6 |
| Jobs report (NFP) | `cpi_nfp_manual.csv` | 08:30 | Release hour and next hour | Forecast feature; H1c |
| US equity open and close | NYSE calendar | 09:30, 16:00 (early closes as listed) | The containing hour | Forecast feature |
| Deribit option expiry | Expiry table | 08:00 UTC | Expiry hour, by type (weekly, monthly, quarterly) | Forecast feature |

**Control hours for H1.** For each coin, the mean log RV over test-window hours with the same UTC hour and weekday and no macro event (scheduled or not) within that hour, the hour before or the hour after.

**Placebo set for H6.** Hours with the same weekday and UTC hour as the CPI releases, with no macro event within three days.

Releases moved by the 2025 US government shutdown are used at their actual release dates, which BLS announced in advance. Cancelled releases have no row.

## Models and loss

The target is log RV in hour H. All features are known at the start of hour H. Models are pooled OLS over BTC and ETH with a coin intercept, each model nesting the one above it.

| Model | Adds |
| --- | --- |
| M1 HAR | Log of mean RV over the previous 1, 24 and 168 hours |
| M2 | Hour-of-day (23) and weekday (6) dummies |
| M3 | US open hour, US close hour, expiry hour by type (weekly, monthly, quarterly) |
| M4 calendar model | CPI, jobs-report and scheduled FOMC flags: event hour and next hour for each (6 dummies) |
| M5 | Log quote volume in the previous hour, and log of mean quote volume over the previous 24 hours |
| +IV variants | Log implied hourly variance, ln((DVOL/100)² / 8760), added to M1 and M4 |

**Primary loss:** squared error of the log-RV forecast.

**Robustness loss:** QLIKE on RV, with the forecast exp(prediction) scaled by the design-window mean of exp(residual).

**Event-hour set (H3):** test-window hours flagged as a CPI or jobs-report release hour, or a scheduled FOMC statement hour or the hour after it.

## Tests and decision rules

All eight tests are one-sided at a Bonferroni level of **0.05 / 8 = 0.00625**. Each result is reported with its effect size and a 95% confidence interval.

| ID | Unit of observation | Statistic |
| --- | --- | --- |
| H1a–c | One value per event: the BTC and ETH log differences from the matched control, averaged | t-test of the mean against 0 |
| H2, H4, H5 | One value per hour: the Clark–West adjusted loss differential, averaged over BTC and ETH | Mean differential, Newey–West standard error with 24 lags |
| H3 | One value per event: the Clark–West differential averaged over the event's flagged hours and both coins | t-test of the mean against 0 |
| H6 | One value per CPI release: the BTC and ETH log-DVOL change from 48 hours to 1 hour before, minus that coin's mean placebo change, averaged | t-test of the mean against 0 |

**Decision rule for each hypothesis:**

- **Confirmed:** p < 0.00625.
- **Supported, not confirmed:** 0.00625 ≤ p < 0.05.
- **Not supported:** p ≥ 0.05.

**Minimum effects regarded as economically meaningful** (interpretation only, not tests): +50% RV for H1, a 0.5% MSE reduction for H2, H4 and H5, a 10% reduction for H3, and +1 percentage point for H6.

**Expected test-window sample** (calendar counts only): 22 scheduled FOMC statements, 32 CPI releases and 32 jobs reports, over about 24,100 hours per coin. With the pilot effect sizes, every H1 test has high power. H6 is the weakest test, and a failure there should be read as a failure to confirm rather than evidence of no effect.

## Robustness and exploratory analyses

These are reported after the confirmatory results and labelled as such. None of them can change a confirmatory verdict.

**Pre-specified robustness checks:**

1. Each test separately for BTC and ETH.
2. Each test by calendar year (2024, 2025, 2026 to September).
3. QLIKE loss in place of squared log error (H2–H5).
4. Outage hours and zero-RV hours dropped.
5. March 2020 (the COVID crash) dropped from the fit window.
6. Coefficients re-estimated each January on an expanding window, instead of frozen.
7. Hours affected by the 2025 shutdown-shifted releases dropped.

**Exploratory analyses:**

- Size of the hour-after effect for each event (press conference, CPI spillover).
- Unscheduled FOMC actions, descriptively.
- The fall in implied volatility after CPI and FOMC (event minus placebo, 1 hour before to 24 hours after).
- The FOMC implied-volatility run-up.
- The US-open and expiry effects in the test window.
- H2 restricted to weekday hours, and to weekend hours.
- Whether event effects differ between high- and low-volatility regimes (split at the design-window median of 168-hour RV).

## Design-window results recorded before the test

The frozen script was dry-run on the design window: fitted on 2020–2022 and evaluated on 2023, using the current 15-minute panel. It reproduced the earlier pilot: H2 gave a 5.35% MSE gain against 5.37% in the pilot, and H5 gave 1.67% in both. The tests on 2024 onwards were blocked as intended when `SPEC_REGISTERED` was not set.

**Event effects over the whole design window** (2020–2023, matched normal hours):

| Event | BTC | ETH | Events |
| --- | --- | --- | --- |
| FOMC statement hour | +517% (t 5.4) | +453% (t 5.2) | 31 |
| CPI release hour | +211% (t 4.1) | +194% (t 3.9) | 48 |
| Jobs-report release hour | +103% (t 3.7) | +75% (t 3.0) | 48 |
| Unscheduled FOMC (descriptive only) | about 70x | about 40x | 3 |

**CPI implied-volatility run-up, 2021–2023** (event minus placebo): +5.0 pp for BTC (t 3.4) and +3.6 pp for ETH (t 2.8). The fall after release was not significant (−1.2 pp for both coins). The jobs report showed no premium once Friday effects were controlled.

**Power.** The dry run's 2023 sample is small (8 FOMC, 12 CPI, 12 jobs reports). The test window has 22, 32 and 32. Scaling the 2023 t-statistics by sample size gives roughly t 3.4 for H1a, 4.0 for H1b, 2.3 for H1c and 4.3 for H6. On that rough guide, H1c is the hypothesis most likely to end as supported but not confirmed.

**Known limitations at freezing:** two coins only; hourly RV from only four 15-minute returns, which makes it noisy and lowers power; one exchange; DVOL is a 30-day measure, so H4 and H6 cannot by themselves show whether options price individual events correctly.

## Freeze checklist and checksums

SHA-256 checksums of the files the test run will read. All values are final; if any file changes, its checksum is replaced and the change is reported as a deviation.

| File | SHA-256 |
| --- | --- |
| `frozen_analysis.py` | `30f883b73a1417191462939861994e666ce4a55230cfc0ba14d7945da64dc6cc` |
| `panel_hourly.parquet` | `5d4f6f250fec4c7f914c31421d704b0ec81c26614c1ea64caad6202bfbbe4879` |
| `cpi_nfp_manual.csv` | `dec784494d0345b5dc10f7ed71ea2deb975fbe2ac5150d76f7061e38ec957fc0` |
| `fomc.csv` | `78f2ebf4ead378f7e9c12320c6555b82e6487e7dcc506272b181966ad9e2cd7b` |
| `dvol/BTC.parquet` | `9e31170736b4d2874609e0d085dfa4b3199327460ef19011dc820de6d2f3f119` |
| `dvol/ETH.parquet` | `d4ad50c53b25b6be29cf0c4cfe28d5ab46299eac1c6fcd98dd9bddeabf11ed51` |

- [x] Dry run on the design window (fit 2020–2022, evaluate 2023): done, figures in Sections 2 and 8
- [x] Open choices settled: H6 confirmatory; frozen coefficients primary, yearly re-estimation as robustness
- [x] Not registered with a third party (author's decision); freeze is self-certified
- [x] Checksums verified on the files used for the test run (all six match)
- [x] Test run, once: `SPEC_REGISTERED=yes python frozen_analysis.py --mode test --panel panel_hourly.parquet --dvol-btc BTC.parquet --dvol-eth ETH.parquet --cpi-nfp cpi_nfp_manual.csv --fomc fomc.csv --out results_test`
- [x] Results reported in full below, in Section 6's order

**Freeze record:** Sections 2 to 6 frozen on 1 November 2026, before any 2024+ statistic was computed. The `SPEC_REGISTERED=yes` setting in the test command means "spec frozen"; no external registration exists.

## Test-window results (1 Jan 2024 to 30 Sep 2026)

**Seven of eight hypotheses are confirmed; H6 is not supported.** The run was made once on 1 November 2026 with the frozen script, after all six checksums were verified. The window covers 48,192 coin-hours, with 22 FOMC statements, 32 CPI releases and 32 jobs reports.

| ID | Result | t | p | Verdict |
| --- | --- | --- | --- | --- |
| H1a FOMC statement hour | +459% (95% CI +260% to +766%), 22 events | 8.16 | 3e-08 | Confirmed |
| H1b CPI release hour | +268% (95% CI +132% to +484%), 32 events | 5.75 | 1.3e-06 | Confirmed |
| H1c Jobs-report release hour | +163% (95% CI +74% to +296%), 32 events | 4.78 | 2e-05 | Confirmed |
| H2 Calendar model vs HAR, all hours | 7.9% lower MSE | 39.2 | < 1e-15 | Confirmed |
| H3 Calendar model in macro event hours | 51% lower MSE (216 coin-hours, 86 events) | 9.76 | 8e-16 | Confirmed |
| H4 Calendar model vs HAR, both with DVOL | 8.7% lower MSE | 39.0 | < 1e-15 | Confirmed |
| H5 Lagged volume | 2.2% lower MSE | 15.3 | < 1e-15 | Confirmed |
| H6 CPI implied-volatility run-up | −0.8 pp (95% CI −2.5 to +1.0), 32 events | −0.91 | 0.81 | Not supported |

Every confirmed effect is larger in the test window than in the 2023 dry run, and each is well above its minimum meaningful size.

**Pre-specified robustness checks (in the frozen script):**

- *By coin:* FOMC +458% BTC and +459% ETH; CPI +224% and +318%; jobs report +176% and +149%. H2 gain 8.7% BTC and 7.1% ETH.
- *By year:* H2 gain 8.1% (2024), 8.5% (2025), 6.9% (2026).
- *QLIKE loss:* H2 +8.2% (t 10.9), H4 +9.7% (t 9.7). H5 fails at −45%, entirely because of one outage hour (see below).
- *Zero-RV hours dropped:* H2 7.9%.
- *Yearly re-estimation:* H2 8.7%.

**Robustness checks listed in Section 7 but missing from the frozen script, run afterwards and labelled post hoc:**

- *March 2020 dropped from the fit:* H2 7.9%.
- *Shutdown-shifted release days dropped:* H2 7.8%, H3 50.9%.
- *Event effects by year:* FOMC +493%, +531% and +339% (2024, 2025, 2026); CPI +367%, +480% and +53%; jobs report +257%, +135% and +100%.

**Deviations and data issues:**

1. Three Section 7 checks (March 2020, shutdown days, by-year event effects) were not implemented in the frozen script. They were run after the test, using the same frozen functions, and are labelled post hoc.
2. On 28 Oct 2024 at 20:00 UTC both coins have zero volume and zero RV, which is likely an exchange or data outage. The panel has no outage flag, so the hour stayed in the primary analysis as Section 3 specifies. It drives the H5 QLIKE failure, because the volume model then forecasts near-zero volatility for the next hour. Excluding 28–29 October 2024, QLIKE gains are H2 +7.7% (t 15.3), H4 +9.1% (t 14.3) and H5 +3.1% (t 10.3). The confirmatory H5 verdict is unchanged, but the volume result is sensitive to outage handling.
3. Outage-hour removal (check 4) could only be done as zero-RV removal, since the panel has no outage flag.

**Exploratory (hour after each event):** FOMC +289% (press conference), CPI +134%, jobs report +52%.

**Reading the results:**

- Scheduled US macro releases are the largest predictable volatility events in BTC and ETH. FOMC is the biggest, at roughly 5.6 times normal volatility in the statement hour.
- A forecast that knows the calendar beats both HAR and HAR with implied volatility, by about 8% overall and about 50% in macro event hours.
- The CPI run-up in implied volatility found in 2021–2023 did not recur in 2024–2026. It should be reported as an in-sample pattern that failed out of sample.
- The CPI effect weakened sharply in 2026 (+53% over 9 releases), which is worth discussing as possible regime dependence: CPI mattered most while inflation was the market's main concern.
