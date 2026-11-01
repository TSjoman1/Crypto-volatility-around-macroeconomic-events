# Research scope (Phase A)

## Aim
Answer whether **known, scheduled events** predict **crypto realised volatility**, without building a full-exchange high-frequency warehouse on a laptop.

## Primary sample
- BTCUSDT, ETHUSDT USD-M perpetual futures (Binance), **15-minute bars**
- Realised variance from 15-minute log returns → hourly and daily panels
- Exact event windows: ±15, 30, 60, 120 minutes (at 15m resolution, ±15m = one bar each side)

## Event types (ordered)
1. US CPI, NFP (08:30 ET), FOMC (14:00 ET) — primary macro
2. Deribit option expiries (08:00 UTC) — primary crypto-native
3. Funding timestamps — secondary microstructure
4. US equity open/close — secondary clock
5. Token unlocks — optional / secondary only

## Design / test
- Design: 2020-01-01 … 2023-12-31  
- Test: 2024-01-01 … last complete UTC day  
- Freeze models, windows, and decision rules in `specs/frozen_spec.yaml` before test.

## Explicitly deferred (not required to answer the questions above)
- Top-30 point-in-time universe
- Full delisted multi-coin history on internal SSD
- Bybit/OKX
- Historical option OI
