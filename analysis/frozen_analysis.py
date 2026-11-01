"""
Frozen analysis for "Crypto Never Sleeps, but It Waits for the Fed".
Implements the pre-analysis plan exactly. One script, two modes:

  dry  : fit 2020-01-01..2022-12-31, evaluate 2023  (design data only; validates the code)
  test : fit 2020-01-01..2023-12-31, evaluate 2024-01-01..2026-09-30
         refuses to run unless SPEC_REGISTERED=yes is set in the environment.

Usage:
  python frozen_analysis.py --mode dry  --panel panel_hourly.parquet --dvol-btc BTC.parquet \
      --dvol-eth ETH.parquet --cpi-nfp cpi_nfp_manual.csv --fomc fomc.csv --out results_dry
  SPEC_REGISTERED=yes python frozen_analysis.py --mode test ...same files... --out results_test
"""
import argparse, json, os, sys
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
from scipy import stats

ALPHA = 0.05 / 8
FLOOR = 1e-12
NW_LAGS = 24
COINS = {'BTCUSDT': 'BTC', 'ETHUSDT': 'ETH'}
NY = ZoneInfo('America/New_York')
WINDOWS = {
    'dry':  dict(fit=('2020-01-01', '2023-01-01'), ev=('2023-01-01', '2024-01-01')),
    'test': dict(fit=('2020-01-01', '2024-01-01'), ev=('2024-01-01', '2026-10-01')),
}
DVOL_START = '2021-03-24'


# ------------------------------------------------------------------ io
def read_parquet(path):
    try:
        return pd.read_parquet(path)
    except Exception:  # environments without pyarrow: optional bundled reader
        sys.path.insert(0, os.environ.get('PQ_READER_DIR', os.path.dirname(os.path.abspath(__file__))))
        import pq
        return pq.read(path)[0]


def load(a):
    p = read_parquet(a.panel)
    p = p[['symbol', 'hour_utc', 'rv', 'n_returns', 'quote_volume', 'us_open_hour', 'us_close_hour',
           'expiry_hour', 'expiry_type']].copy()
    p['hour_utc'] = pd.to_datetime(p.hour_utc)
    p = p[p.symbol.isin(COINS)].sort_values(['symbol', 'hour_utc']).reset_index(drop=True)

    m = pd.read_csv(a.cpi_nfp, parse_dates=['release_date'])
    m['t'] = [pd.Timestamp(f'{d.date()} 08:30').tz_localize(NY).tz_convert('UTC').tz_localize(None) for d in m.release_date]
    f = pd.read_csv(a.fomc, parse_dates=['meeting_end_date'])
    f['t'] = [pd.Timestamp(f'{d.date()} {s}').tz_localize(NY).tz_convert('UTC').tz_localize(None)
              for d, s in zip(f.meeting_end_date, f.statement_time_et)]
    f['event_type'] = np.where(f.scheduled.astype(str).str.lower() == 'true', 'FOMC', 'FOMC_unsched')
    ev = pd.concat([m[['event_type', 't']], f[['event_type', 't']]]).reset_index(drop=True)
    ev['h0'] = ev.t.dt.floor('h')

    dv = {}
    for c, path in (('BTCUSDT', a.dvol_btc), ('ETHUSDT', a.dvol_eth)):
        x = read_parquet(path)
        x['ts_utc'] = pd.to_datetime(x.ts_utc) if 'ts_utc' in x else pd.to_datetime(x.ts, unit='ms')
        dv[c] = x.set_index('ts_utc').close.sort_index()
    return p, ev, dv


# ------------------------------------------------------------------ features
def build(p, ev, dv, min_returns, end):
    p = p[p.hour_utc < pd.Timestamp(end)].copy()                     # never touch data past the eval window
    p = p[p.n_returns >= min_returns].copy()
    p['lrv'] = np.log(p.rv.clip(lower=FLOOR))
    p['zero_rv'] = p.rv <= 0
    p['hod'] = p.hour_utc.dt.hour; p['dow'] = p.hour_utc.dt.dayofweek; p['year'] = p.hour_utc.dt.year
    g = p.groupby('symbol', group_keys=False)
    p['h1'] = g.lrv.shift(1)
    p['h24'] = np.log(g.rv.apply(lambda s: s.shift(1).rolling(24).mean()).clip(lower=FLOOR))
    p['h168'] = np.log(g.rv.apply(lambda s: s.shift(1).rolling(168).mean()).clip(lower=FLOOR))
    p['v1'] = np.log(g.quote_volume.shift(1).clip(lower=1))
    p['v24'] = np.log(g.quote_volume.apply(lambda s: s.shift(1).rolling(24).mean()).clip(lower=1))
    for t in ['CPI', 'NFP', 'FOMC', 'FOMC_unsched']:
        hrs = set(ev[ev.event_type == t].h0)
        for k in (-1, 0, 1):
            p[f'{t}_{k}'] = p.hour_utc.isin({h + pd.Timedelta(hours=k) for h in hrs}).astype(float)
    flag_cols = [c for c in p.columns if c.split('_')[0] in ('CPI', 'NFP', 'FOMC') and c[-2:] in ('-1', '_0', '_1')]
    p['any_macro'] = p[flag_cols].sum(axis=1) > 0
    for t in ['weekly', 'monthly', 'quarterly']:
        p[f'exp_{t}'] = ((p.expiry_hour == 1) & (p.expiry_type == t)).astype(float)
    p['eth'] = (p.symbol == 'ETHUSDT').astype(float)
    ivs = []
    for c, s in dv.items():
        x = s.rename('dvol').reset_index(); x['hour_utc'] = x.ts_utc + pd.Timedelta(hours=1); x['symbol'] = c
        ivs.append(x[['symbol', 'hour_utc', 'dvol']])
    p = p.merge(pd.concat(ivs), on=['symbol', 'hour_utc'], how='left')
    p['iv'] = np.log((p.dvol / 100) ** 2 / 8760)
    p.loc[p.hour_utc < pd.Timestamp(DVOL_START), 'iv'] = np.nan
    return p.dropna(subset=['h1', 'h24', 'h168', 'v1', 'v24']).reset_index(drop=True)


HOD = [f'hod_{h}' for h in range(1, 24)]; DOW = [f'dow_{d}' for d in range(1, 7)]
M = {}
M['M1'] = ['eth', 'h1', 'h24', 'h168']
M['M2'] = M['M1'] + HOD + DOW
M['M3'] = M['M2'] + ['us_open_hour', 'us_close_hour', 'exp_weekly', 'exp_monthly', 'exp_quarterly']
M['M4'] = M['M3'] + ['CPI_0', 'CPI_1', 'NFP_0', 'NFP_1', 'FOMC_0', 'FOMC_1']
M['M5'] = M['M4'] + ['v1', 'v24']
M['M1IV'] = M['M1'] + ['iv']
M['M4IV'] = M['M4'] + ['iv']


def design(p):
    for h in range(1, 24): p[f'hod_{h}'] = (p.hod == h).astype(float)
    for d in range(1, 7): p[f'dow_{d}'] = (p.dow == d).astype(float)
    for c in ['us_open_hour', 'us_close_hour']: p[c] = p[c].astype(float)
    return p


def fit_predict(p, cols, fit_mask):
    X = np.column_stack([np.ones(len(p)), p[cols].values.astype(float)])
    ok = fit_mask & ~np.isnan(X).any(1)
    b, *_ = np.linalg.lstsq(X[ok], p.lrv.values[ok], rcond=None)
    pred = X @ b; pred[np.isnan(X).any(1)] = np.nan
    resid = p.lrv.values[ok] - pred[ok]
    return pred, float(np.mean(np.exp(resid)))


# ------------------------------------------------------------------ statistics
def nw_se(x, lags=NW_LAGS):
    n = len(x); e = x - x.mean(); s = e @ e / n
    for l in range(1, min(lags, n - 1) + 1): s += 2 * (1 - l / (lags + 1)) * (e[l:] @ e[:-l]) / n
    return np.sqrt(s / n)


def one_sided_t(v):
    v = np.asarray(v, float); v = v[~np.isnan(v)]; n = len(v)
    m, se = v.mean(), v.std(ddof=1) / np.sqrt(n)
    t = m / se; pval = 1 - stats.t.cdf(t, n - 1); h = stats.t.ppf(0.975, n - 1) * se
    return dict(n=n, mean=m, t=t, p=pval, ci=(m - h, m + h))


def verdict(pv):
    return 'Confirmed' if pv < ALPHA else ('Supported, not confirmed' if pv < 0.05 else 'Not supported')


def cw_rows(y, ps, pb, loss='se', scale=(1, 1)):
    if loss == 'se':
        ls, lb = (y - ps) ** 2, (y - pb) ** 2
        return ls - (lb - (ps - pb) ** 2), ls, lb
    rv = np.exp(y); fs, fb = np.exp(ps) * scale[0], np.exp(pb) * scale[1]
    ls, lb = rv / fs - np.log(rv / fs) - 1, rv / fb - np.log(rv / fb) - 1
    return ls - lb, ls, lb                                     # QLIKE: plain differential


def hour_level_test(p, evm, small, big, P, loss='se', subset=None):
    m = evm & ~np.isnan(P[small][0]) & ~np.isnan(P[big][0])
    if subset is not None: m &= subset
    y = p.lrv.values
    cw, ls, lb = cw_rows(y[m], P[small][0][m], P[big][0][m], loss, (P[small][1], P[big][1]))
    d = pd.DataFrame({'h': p.hour_utc.values[m], 'cw': cw}).groupby('h').cw.mean().values
    se = nw_se(d); t = d.mean() / se
    return dict(n_hours=len(d), mse_gain_pct=100 * (1 - lb.mean() / ls.mean()), cw_t=t, p=1 - stats.norm.cdf(t))


# ------------------------------------------------------------------ main
def run(a):
    if a.mode == 'test' and os.environ.get('SPEC_REGISTERED') != 'yes':
        sys.exit('Test window locked: register the frozen spec and record checksums, then set SPEC_REGISTERED=yes.')
    W = WINDOWS[a.mode]
    praw, ev, dv = load(a)
    p = design(build(praw, ev, dv, a.min_returns, W['ev'][1]))
    fit = ((p.hour_utc >= W['fit'][0]) & (p.hour_utc < W['fit'][1])).values
    evm = ((p.hour_utc >= W['ev'][0]) & (p.hour_utc < W['ev'][1])).values
    assert p.hour_utc.max() < pd.Timestamp(W['ev'][1])
    P = {k: fit_predict(p, cols, fit) for k, cols in M.items()}
    E = p[evm].copy()
    R = {'mode': a.mode, 'fit_window': W['fit'], 'eval_window': W['ev'], 'alpha': ALPHA,
         'eval_rows': int(evm.sum()), 'zero_rv_hours_eval': int(E.zero_rv.sum())}
    evE = ev[(ev.h0 >= W['ev'][0]) & (ev.h0 < W['ev'][1])]
    R['event_counts'] = evE.event_type.value_counts().to_dict()

    # ---- H1
    ctl = E[~E.any_macro].groupby(['symbol', 'hod', 'dow']).lrv.mean()
    def h1(etype, k=0, data=E):
        vals = []
        for h0 in evE[evE.event_type == etype].h0:
            rows = data[data.hour_utc == h0 + pd.Timedelta(hours=k)]
            d = [r.lrv - ctl.get((r.symbol, r.hod, r.dow), np.nan) for r in rows.itertuples()]
            d = [x for x in d if not np.isnan(x)]
            if d: vals.append(np.mean(d))
        return one_sided_t(vals) if len(vals) > 1 else None
    for hid, et in (('H1a', 'FOMC'), ('H1b', 'CPI'), ('H1c', 'NFP')):
        r = h1(et)
        R[hid] = dict(event=et, n=r['n'], effect_pct=100 * (np.exp(r['mean']) - 1),
                      ci_pct=[100 * (np.exp(c) - 1) for c in r['ci']], t=r['t'], p=r['p'], verdict=verdict(r['p']))

    # ---- H2, H4, H5
    for hid, small, big in (('H2', 'M1', 'M4'), ('H4', 'M1IV', 'M4IV'), ('H5', 'M4', 'M5')):
        r = hour_level_test(p, evm, small, big, P)
        R[hid] = dict(models=f'{big} vs {small}', **r, verdict=verdict(r['p']))

    # ---- H3
    y = p.lrv.values
    evset = evm & (p[['CPI_0', 'NFP_0', 'FOMC_0', 'FOMC_1']].sum(axis=1) > 0).values
    cw, ls, lb = cw_rows(y[evset], P['M2'][0][evset], P['M4'][0][evset])
    hrs = p.hour_utc.values[evset]
    eid = np.where(p.FOMC_1.values[evset] == 1, pd.to_datetime(hrs) - pd.Timedelta(hours=1), pd.to_datetime(hrs))
    per = pd.Series(cw).groupby(pd.to_datetime(eid)).mean().values
    r = one_sided_t(per)
    R['H3'] = dict(models='M4 vs M2 in macro event hours', n_events=r['n'], n_coin_hours=int(evset.sum()),
                   mse_gain_pct=100 * (1 - lb.mean() / ls.mean()), t=r['t'], p=r['p'], verdict=verdict(r['p']))

    # ---- H6
    allday = set(ev.h0.dt.floor('D')); near = {d + pd.Timedelta(days=k) for d in allday for k in range(-3, 4)}
    cpi = evE[evE.event_type == 'CPI'].h0
    lo, hi = pd.Timestamp(W['ev'][0]), pd.Timestamp(W['ev'][1])
    cand = pd.date_range(lo + pd.Timedelta(days=3), hi - pd.Timedelta(days=2), freq='h')
    cand = [h for h in cand if h.dayofweek in set(cpi.dt.dayofweek) and h.hour in set(cpi.dt.hour) and h.floor('D') not in near]
    def runup(l, h0):
        a_, b_ = l.get(h0 - pd.Timedelta(hours=1)), l.get(h0 - pd.Timedelta(hours=48))
        return np.nan if a_ is None or b_ is None else a_ - b_
    per_coin = {}
    for c, s in dv.items():
        l = np.log(s[(s.index >= lo - pd.Timedelta(days=3)) & (s.index < hi)])
        plc = np.nanmean([runup(l, h) for h in cand])
        per_coin[c] = {h0: runup(l, h0) - plc for h0 in cpi}
    vals = [np.nanmean([per_coin[c][h0] for c in per_coin]) for h0 in cpi]
    r = one_sided_t(vals)
    R['H6'] = dict(n=r['n'], n_placebo_hours=len(cand), runup_pp=100 * r['mean'], ci_pp=[100 * c for c in r['ci']],
                   t=r['t'], p=r['p'], verdict=verdict(r['p']))

    # ---- robustness (labelled; cannot change verdicts)
    rob = {}
    for c in COINS:
        sub = (p.symbol == c).values
        rob[f'H2 {COINS[c]}'] = hour_level_test(p, evm, 'M1', 'M4', P, subset=sub)['mse_gain_pct']
        Ec = E[E.symbol == c]
        for hid, et in (('H1a', 'FOMC'), ('H1b', 'CPI'), ('H1c', 'NFP')):
            rr = h1(et, data=Ec); rob[f'{hid} {COINS[c]} %'] = 100 * (np.exp(rr['mean']) - 1)
    for yr in sorted(E.year.unique()):
        sub = (p.year == yr).values
        rob[f'H2 {yr}'] = hour_level_test(p, evm, 'M1', 'M4', P, subset=sub)['mse_gain_pct']
    for hid, s_, b_ in (('H2', 'M1', 'M4'), ('H4', 'M1IV', 'M4IV'), ('H5', 'M4', 'M5')):
        q = hour_level_test(p, evm, s_, b_, P, loss='qlike'); rob[f'{hid} QLIKE gain %'] = q['mse_gain_pct']; rob[f'{hid} QLIKE t'] = q['cw_t']
    rob['H2 drop zero-RV'] = hour_level_test(p, evm, 'M1', 'M4', P, subset=~p.zero_rv.values)['mse_gain_pct']
    # expanding re-estimation each January
    pe = {k: np.full(len(p), np.nan) for k in ('M1', 'M4')}
    for yr in sorted(E.year.unique()):
        fm = (p.hour_utc < pd.Timestamp(f'{yr}-01-01')).values; tm = evm & (p.year == yr).values
        for k in pe: pe[k][tm] = fit_predict(p, M[k], fm)[0][tm]
    Pe = {k: (pe[k], 1.0) for k in pe}
    rob['H2 expanding re-estimation'] = hour_level_test(p, evm, 'M1', 'M4', Pe)['mse_gain_pct']
    for et in ['FOMC', 'CPI', 'NFP']:
        rr = h1(et, k=1)
        if rr: rob[f'hour after {et} %'] = 100 * (np.exp(rr['mean']) - 1)
    R['robustness'] = rob
    return R


def report(R, out):
    os.makedirs(out, exist_ok=True)
    json.dump(R, open(os.path.join(out, 'results.json'), 'w'), indent=2, default=float)
    L = [f"# Results ({R['mode']} mode)", '', f"Fit {R['fit_window']}, evaluate {R['eval_window']}, alpha {R['alpha']:.5f}", '',
         f"Eval rows {R['eval_rows']}, zero-RV hours {R['zero_rv_hours_eval']}, events {R['event_counts']}", '',
         '| ID | Result | t | p | Verdict |', '| --- | --- | --- | --- | --- |']
    for k in ['H1a', 'H1b', 'H1c']:
        r = R[k]; L.append(f"| {k} {r['event']} | {r['effect_pct']:+.0f}% (95% CI {r['ci_pct'][0]:+.0f}% to {r['ci_pct'][1]:+.0f}%), n={r['n']} | {r['t']:.2f} | {r['p']:.2g} | {r['verdict']} |")
    for k in ['H2', 'H4', 'H5']:
        r = R[k]; L.append(f"| {k} {r['models']} | MSE {r['mse_gain_pct']:+.2f}% | {r['cw_t']:.2f} | {r['p']:.2g} | {r['verdict']} |")
    r = R['H3']; L.append(f"| H3 | MSE {r['mse_gain_pct']:+.1f}% in {r['n_coin_hours']} coin-hours, {r['n_events']} events | {r['t']:.2f} | {r['p']:.2g} | {r['verdict']} |")
    r = R['H6']; L.append(f"| H6 | run-up {r['runup_pp']:+.1f} pp (95% CI {r['ci_pp'][0]:+.1f} to {r['ci_pp'][1]:+.1f}), n={r['n']} | {r['t']:.2f} | {r['p']:.2g} | {r['verdict']} |")
    L += ['', '## Robustness (does not change verdicts)', ''] + [f'- {k}: {v:.2f}' for k, v in R['robustness'].items()]
    open(os.path.join(out, 'results.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['dry', 'test'], default='dry')
    for k in ('panel', 'dvol-btc', 'dvol-eth', 'cpi-nfp', 'fomc', 'out'): ap.add_argument(f'--{k}', required=True)
    ap.add_argument('--min-returns', type=int, default=3, help='spec: RV from 15-minute returns (4 per hour); drop hours with fewer than 3')
    report(run(ap.parse_args()), ap.parse_args().out)
