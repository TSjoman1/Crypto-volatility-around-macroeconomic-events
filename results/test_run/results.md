# Results (test mode)

Fit ('2020-01-01', '2024-01-01'), evaluate ('2024-01-01', '2026-10-01'), alpha 0.00625

Eval rows 48192, zero-RV hours 2, events {'NFP': 32, 'CPI': 32, 'FOMC': 22}

| ID | Result | t | p | Verdict |
| --- | --- | --- | --- | --- |
| H1a FOMC | +459% (95% CI +260% to +766%), n=22 | 8.16 | 3e-08 | Confirmed |
| H1b CPI | +268% (95% CI +132% to +484%), n=32 | 5.75 | 1.3e-06 | Confirmed |
| H1c NFP | +163% (95% CI +74% to +296%), n=32 | 4.78 | 2e-05 | Confirmed |
| H2 M4 vs M1 | MSE +7.86% | 39.15 | 0 | Confirmed |
| H4 M4IV vs M1IV | MSE +8.67% | 39.02 | 0 | Confirmed |
| H5 M5 vs M4 | MSE +2.19% | 15.30 | 0 | Confirmed |
| H3 | MSE +51.2% in 216 coin-hours, 86 events | 9.76 | 7.8e-16 | Confirmed |
| H6 | run-up -0.8 pp (95% CI -2.5 to +1.0), n=32 | -0.91 | 0.81 | Not supported |

## Robustness (does not change verdicts)

- H2 BTC: 8.69
- H1a BTC %: 458.33
- H1b BTC %: 223.58
- H1c BTC %: 176.31
- H2 ETH: 7.05
- H1a ETH %: 459.06
- H1b ETH %: 317.70
- H1c ETH %: 149.46
- H2 2024: 8.12
- H2 2025: 8.47
- H2 2026: 6.88
- H2 QLIKE gain %: 8.18
- H2 QLIKE t: 10.89
- H4 QLIKE gain %: 9.73
- H4 QLIKE t: 9.66
- H5 QLIKE gain %: -45.13
- H5 QLIKE t: -0.94
- H2 drop zero-RV: 7.94
- H2 expanding re-estimation: 8.71
- hour after FOMC %: 288.72
- hour after CPI %: 133.76
- hour after NFP %: 51.54
