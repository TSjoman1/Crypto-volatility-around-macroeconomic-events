# QA report
Generated for project root `/Users/tonisjoman/Desktop/crypto-calendar-vol`

## Symbols
    symbol base_asset  ...  is_1000_prefixed  phase_a_primary
0  BTCUSDT        BTC  ...             False             True
1  ETHUSDT        ETH  ...             False             True

[2 rows x 7 columns]

## Klines partitions (row counts by symbol/year)
     symbol     y   rows
0   BTCUSDT  2020  35136
1   BTCUSDT  2021  35040
2   BTCUSDT  2022  35040
3   BTCUSDT  2023  35040
4   BTCUSDT  2024  35136
5   BTCUSDT  2025  35040
6   BTCUSDT  2026  26208
7   ETHUSDT  2020  35136
8   ETHUSDT  2021  35040
9   ETHUSDT  2022  35040
10  ETHUSDT  2023  35040
11  ETHUSDT  2024  35136
12  ETHUSDT  2025  35040
13  ETHUSDT  2026  26208

## Panel hourly row counts by window (counts only)
ERR: Parser Error: syntax error at or near ","

LINE 1: SELECT symbol, window, COUNT(*) AS n FROM panel_hourly GROUP BY 1,2 ORDER BY 1,2
                             ^

## Macro event counts by year/type
Empty DataFrame
Columns: [event_type, y, n]
Index: []

## Expiries by source
  currency       source    n
0      BTC         rule  357
1      ETH  deribit_api   14
2      BTC  deribit_api   14
3      ETH         rule  357

## DVOL coverage (timestamps only)
  currency   first_ts    last_ts      n
0      ETH 2021-03-24 2026-10-31  49129
1      BTC 2021-03-24 2026-10-31  49129

## Funding row counts
    symbol     n
0  ETHUSDT  7488
1  BTCUSDT  7488

*Note: No returns, realised variance levels, or volume levels are reported for the test window.*
