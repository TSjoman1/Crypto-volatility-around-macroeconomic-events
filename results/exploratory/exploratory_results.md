# Exploratory, descriptive and post hoc results

None of these results can change a confirmatory verdict (see results/test_run).

## Section 4.1 Intraday and weekday pattern (2020-2023)

Hourly RV relative to the daily mean, by UTC hour:

|   hod |   BTCUSDT |   ETHUSDT |
|------:|----------:|----------:|
|     0 |      1.26 |      1.42 |
|     1 |      0.91 |      0.9  |
|     2 |      1.5  |      1.23 |
|     3 |      0.81 |      0.88 |
|     4 |      0.69 |      0.71 |
|     5 |      0.71 |      0.73 |
|     6 |      0.67 |      0.67 |
|     7 |      0.66 |      0.73 |
|     8 |      0.86 |      0.89 |
|     9 |      0.77 |      0.74 |
|    10 |      1.09 |      0.97 |
|    11 |      0.88 |      0.91 |
|    12 |      1.28 |      1.21 |
|    13 |      1.35 |      1.27 |
|    14 |      1.42 |      1.45 |
|    15 |      1.1  |      1.06 |
|    16 |      1.2  |      1.49 |
|    17 |      0.86 |      0.88 |
|    18 |      0.97 |      0.99 |
|    19 |      0.91 |      0.88 |
|    20 |      1.06 |      1    |
|    21 |      1.12 |      1.06 |
|    22 |      0.94 |      0.99 |
|    23 |      0.98 |      0.93 |

RV by weekday relative to the weekly mean (Mon=0): 0: 1.09, 1: 0.97, 2: 1.09, 3: 1.19, 4: 1.25, 5: 0.65, 6: 0.76

## Sections 4.2 and 5.2 Event effects (release hour and hour after)

| window    | event        | hour    |   BTC % |   BTC t |   ETH % |   ETH t |   pooled % |   pooled t |   n |
|:----------|:-------------|:--------|--------:|--------:|--------:|--------:|-----------:|-----------:|----:|
| 2020-2023 | FOMC         | release |     517 |    5.4  |     453 |    5.23 |        484 |       5.47 |  31 |
| 2020-2023 | FOMC         | next    |      95 |    2.25 |     100 |    2.64 |         97 |       2.53 |  31 |
| 2020-2023 | CPI          | release |     211 |    4.13 |     194 |    3.93 |        202 |       4.09 |  48 |
| 2020-2023 | CPI          | next    |      68 |    2.73 |      37 |    1.54 |         52 |       2.15 |  48 |
| 2020-2023 | NFP          | release |     103 |    3.73 |      75 |    3    |         88 |       3.51 |  48 |
| 2020-2023 | NFP          | next    |      -1 |   -0.05 |      18 |    1    |          8 |       0.53 |  48 |
| 2020-2023 | FOMC_unsched | release |    7289 |    4.07 |    3891 |    4.8  |       5330 |       4.38 |   3 |
| 2020-2023 | FOMC_unsched | next    |    2267 |    2.37 |    1569 |    3.82 |       1888 |       2.89 |   3 |
| 2024-2026 | FOMC         | release |     458 |    8.52 |     459 |    7.55 |        459 |       8.16 |  22 |
| 2024-2026 | FOMC         | next    |     286 |    5.24 |     291 |    7.25 |        289 |       6.43 |  22 |
| 2024-2026 | CPI          | release |     224 |    4.87 |     318 |    5.79 |        268 |       5.75 |  32 |
| 2024-2026 | CPI          | next    |     127 |    4.43 |     141 |    4.45 |        134 |       4.72 |  32 |
| 2024-2026 | NFP          | release |     176 |    4.46 |     149 |    4.68 |        163 |       4.78 |  32 |
| 2024-2026 | NFP          | next    |      63 |    2.32 |      41 |    1.45 |         52 |       1.94 |  32 |

## Sections 4.1-4.2 and 5.3 Calendar coefficients (% change in RV)

Design-window fits; the test-window column re-estimates M4 on 2024-2026 for description only.

|               |   design M3 % |   design M4 % |   test M4 refit % |
|:--------------|--------------:|--------------:|------------------:|
| us_open_hour  |            26 |            31 |                81 |
| us_close_hour |            -4 |            -3 |               -24 |
| exp_weekly    |            -1 |            -1 |                15 |
| exp_monthly   |            51 |            52 |                -3 |
| exp_quarterly |             7 |             8 |                -3 |
| CPI_0         |           nan |           262 |               347 |
| CPI_1         |           nan |             2 |                26 |
| NFP_0         |           nan |           146 |               210 |
| NFP_1         |           nan |           -10 |                -6 |
| FOMC_0        |           nan |           477 |               606 |
| FOMC_1        |           nan |            29 |               184 |

## Section 6 DVOL around releases, event minus placebo (points of log DVOL)

run-up = 48 h before to 1 h before; fall = 1 h before to 24 h after.

| window    | event   | coin   |   n |   placebo |   runup_pp |   runup_t |   fall_pp |   fall_t |
|:----------|:--------|:-------|----:|----------:|-----------:|----------:|----------:|---------:|
| 2021-2023 | CPI     | BTC    |  33 |       520 |       4.99 |      3.39 |     -1.19 |    -0.75 |
| 2021-2023 | CPI     | ETH    |  33 |       520 |       3.64 |      2.83 |     -1.18 |    -0.71 |
| 2021-2023 | FOMC    | BTC    |  22 |       130 |       0.22 |      0.31 |     -0.1  |    -0.1  |
| 2021-2023 | FOMC    | ETH    |  22 |       130 |      -0.93 |     -1.06 |     -1.21 |    -1.1  |
| 2021-2023 | NFP     | BTC    |  33 |       130 |       2.05 |      2.73 |     -0.27 |    -0.37 |
| 2021-2023 | NFP     | ETH    |  33 |       130 |       1.16 |      1.34 |     -0.34 |    -0.53 |
| 2024-2026 | CPI     | BTC    |  32 |       512 |      -0.82 |     -0.82 |     -1.36 |    -2.17 |
| 2024-2026 | CPI     | ETH    |  32 |       512 |      -0.72 |     -0.86 |     -1.07 |    -1.73 |
| 2024-2026 | FOMC    | BTC    |  22 |       256 |      -0.31 |     -0.27 |     -1.65 |    -1.35 |
| 2024-2026 | FOMC    | ETH    |  22 |       256 |       0.88 |      0.91 |     -1.07 |    -1.32 |
| 2024-2026 | NFP     | BTC    |  32 |       512 |      -0.19 |     -0.17 |     -0.49 |    -0.63 |
| 2024-2026 | NFP     | ETH    |  32 |       512 |      -0.04 |     -0.04 |     -0.12 |    -0.16 |

## Section 7.2-7.3 Post hoc checks (labelled post hoc in the paper)

- H2 with March 2020 dropped from the fit: 7.90%
- H2 dropping shutdown-shifted release days: 7.83%; H3: 50.9%
- H2 weekday hours: 7.29%; weekend hours: 9.14%
- H2 QLIKE excluding the 28-29 Oct 2024 outage: 7.70% (t 15.33)
- H4 QLIKE excluding the 28-29 Oct 2024 outage: 9.05% (t 14.28)
- H5 QLIKE excluding the 28-29 Oct 2024 outage: 3.12% (t 10.31)

Appendix A, event effects by year (pooled, controls from the whole test window):

| event   | 2024       | 2025       | 2026      |
|:--------|:-----------|:-----------|:----------|
| FOMC    | +493% (8)  | +531% (8)  | +339% (6) |
| CPI     | +367% (12) | +480% (11) | +53% (9)  |
| NFP     | +257% (12) | +135% (11) | +100% (9) |

Regime split (test window, coin-events; high = 168-hour RV above the design-window median):

- FOMC: high +685% (n=5), low +435% (n=39)
- CPI: high +254% (n=24), low +276% (n=40)
- NFP: high +129% (n=17), low +176% (n=47)
