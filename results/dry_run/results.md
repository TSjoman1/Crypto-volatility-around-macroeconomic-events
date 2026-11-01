# Results (dry mode)

Fit ('2020-01-01', '2023-01-01'), evaluate ('2023-01-01', '2024-01-01'), alpha 0.00625

Eval rows 17520, zero-RV hours 0, events {'NFP': 12, 'CPI': 12, 'FOMC': 8}

| ID | Result | t | p | Verdict |
| --- | --- | --- | --- | --- |
| H1a FOMC | +207% (95% CI -15% to +1011%), n=8 | 2.07 | 0.039 | Supported, not confirmed |
| H1b CPI | +222% (95% CI +14% to +813%), n=12 | 2.47 | 0.016 | Supported, not confirmed |
| H1c NFP | +69% (95% CI -26% to +285%), n=12 | 1.39 | 0.096 | Not supported |
| H2 M4 vs M1 | MSE +5.35% | 19.41 | 0 | Confirmed |
| H4 M4IV vs M1IV | MSE +6.93% | 21.93 | 0 | Confirmed |
| H5 M5 vs M4 | MSE +1.67% | 11.25 | 0 | Confirmed |
| H3 | MSE +28.7% in 80 coin-hours, 32 events | 4.57 | 3.6e-05 | Confirmed |
| H6 | run-up +2.6 pp (95% CI +0.4 to +4.8), n=12 | 2.64 | 0.011 | Supported, not confirmed |

## Robustness (does not change verdicts)

- H2 BTC: 5.68
- H1a BTC %: 112.00
- H1b BTC %: 196.27
- H1c BTC %: 63.55
- H2 ETH: 5.03
- H1a ETH %: 345.98
- H1b ETH %: 250.04
- H1c ETH %: 73.70
- H2 2023: 5.35
- H2 QLIKE gain %: 3.48
- H2 QLIKE t: 2.68
- H4 QLIKE gain %: 4.41
- H4 QLIKE t: 2.16
- H5 QLIKE gain %: 4.24
- H5 QLIKE t: 2.09
- H2 drop zero-RV: 5.35
- H2 expanding re-estimation: 5.35
- hour after FOMC %: 196.41
- hour after CPI %: 147.78
- hour after NFP %: 94.74
