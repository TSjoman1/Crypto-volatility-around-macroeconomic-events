"""
Descriptive, exploratory and post hoc analyses for
"Crypto Never Sleeps, but It Waits for the Fed".

Reproduces every number in the paper that does NOT come from the frozen run
(frozen_analysis.py): Section 4 (design-window patterns), Section 6.1 and the
exploratory parts of 6.2 (DVOL around releases), the exploratory parts of 5.2-5.3,
Section 7.2-7.3 (post hoc checks), Appendix A, and the data behind Figures 1-3.

It imports the frozen script's functions, so both use identical data handling.
Nothing here can change a confirmatory verdict.

Usage (same input files as the frozen run):
  SPEC_REGISTERED=yes python exploratory_analysis.py --panel panel_hourly.parquet \
      --dvol-btc BTC.parquet --dvol-eth ETH.parquet --cpi-nfp cpi_nfp_manual.csv \
      --fomc fomc.csv --out results/exploratory
"""
import argparse, os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frozen_analysis as fa

DESIGN = ('2020-01-01', '2024-01-01')
TEST = ('2024-01-01', '2026-10-01')
DVOL_DESIGN = ('2021-03-24', '2024-01-01')
COINS = ['BTCUSDT', 'ETHUSDT']
K = np.arange(-48, 25)
SHUTDOWN_DAYS = pd.to_datetime(['2025-10-24', '2025-11-20', '2025-12-16', '2025-12-18', '2026-02-11'])
OUTAGE = ('2024-10-28 20:00', '2024-10-29 20:00')

pct = lambda x: 100 * (np.exp(x) - 1)


def window(p, w):
    return ((p.hour_utc >= w[0]) & (p.hour_utc < w[1])).values


# ------------------------------------------------------------------ event effects (same method as H1)
def event_values(p, ev, w, etype, k=0, coins=COINS):
    """One value per event: mean over coins of (log RV in event hour + k) minus matched control."""
    E = p[window(p, w) & p.symbol.isin(coins).values]
    ctl = E[~E.any_macro].groupby(['symbol', 'hod', 'dow']).lrv.mean()
    out = {}
    for h0 in ev[(ev.event_type == etype) & (ev.h0 >= w[0]) & (ev.h0 < w[1])].h0:
        rows = E[E.hour_utc == h0 + pd.Timedelta(hours=k)]
        d = [r.lrv - ctl.get((r.symbol, r.hod, r.dow), np.nan) for r in rows.itertuples()]
        d = [x for x in d if not np.isnan(x)]
        if d: out[h0] = np.mean(d)
    return pd.Series(out, dtype=float)


def summarise(v):
    if len(v) < 2: return dict(n=len(v), pct=pct(v.mean()) if len(v) else np.nan)
    r = fa.one_sided_t(v.values)
    return dict(n=r['n'], pct=pct(r['mean']), lo=pct(r['ci'][0]), hi=pct(r['ci'][1]), t=r['t'])


# ------------------------------------------------------------------ DVOL event minus placebo
def dvol_event(dv, ev, w, etype, name):
    lo, hi = pd.Timestamp(w[0]), pd.Timestamp(w[1])
    evdays = set(ev.h0.dt.floor('D')); near = {d + pd.Timedelta(days=k) for d in evdays for k in range(-3, 4)}
    times = ev[(ev.event_type == etype) & (ev.h0 >= lo) & (ev.h0 < hi)].h0
    res, paths = {}, []
    for c, s in dv.items():
        l = np.log(s[(s.index >= lo - pd.Timedelta(days=3)) & (s.index < hi)])

        def path(h0):
            v = l.reindex([h0 + pd.Timedelta(hours=int(k)) for k in K]).values
            ref = l.get(h0 - pd.Timedelta(hours=24))
            return None if ref is None or np.isnan(v).any() else v - ref
        Ev = np.array([q for q in (path(h) for h in times) if q is not None])
        cand = pd.date_range(max(lo, l.index[0]) + pd.Timedelta(days=3), hi - pd.Timedelta(days=2), freq='h')
        cand = [h for h in cand if h.dayofweek in set(times.dt.dayofweek) and h.hour in set(times.dt.hour)
                and h.floor('D') not in near]
        Pl = np.array([q for q in (path(h) for h in cand) if q is not None])
        i1, i2, i3 = list(K).index(-48), list(K).index(-1), list(K).index(24)
        ru = (Ev[:, i2] - Ev[:, i1]) - (Pl[:, i2] - Pl[:, i1]).mean()
        cr = (Ev[:, i3] - Ev[:, i2]) - (Pl[:, i3] - Pl[:, i2]).mean()
        tt = lambda x: x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
        res[c[:3]] = dict(n=len(Ev), placebo=len(Pl), runup_pp=100 * ru.mean(), runup_t=tt(ru),
                          fall_pp=100 * cr.mean(), fall_t=tt(cr))
        for k, e, q in zip(K, Ev.mean(0), Pl.mean(0)):
            paths.append(dict(coin=c[:3], event=etype, window=name, h=int(k),
                              event_minus_placebo_pp=100 * (e - q)))
    return res, paths


def coefs(p, cols, mask):
    X = np.column_stack([np.ones(len(p)), p[cols].values.astype(float)])
    ok = mask & ~np.isnan(X).any(1)
    b, *_ = np.linalg.lstsq(X[ok], p.lrv.values[ok], rcond=None)
    return pd.Series(b, ['c'] + cols)


def main(a):
    if os.environ.get('SPEC_REGISTERED') != 'yes':
        sys.exit('Uses test-window data: run only after the frozen test run (set SPEC_REGISTERED=yes).')
    os.makedirs(a.out, exist_ok=True)
    praw, ev, dv = fa.load(a)
    p = fa.design(fa.build(praw, ev, dv, a.min_returns, TEST[1]))
    L = ['# Exploratory, descriptive and post hoc results', '',
         'None of these results can change a confirmatory verdict (see results/test_run).', '']

    # ---- Section 4.1: intraday and weekday profile (design window; Figure 1)
    d = praw[(praw.hour_utc >= DESIGN[0]) & (praw.hour_utc < DESIGN[1]) & (praw.n_returns >= a.min_returns)].copy()
    d['hod'] = d.hour_utc.dt.hour; d['dow'] = d.hour_utc.dt.dayofweek
    prof = d.groupby(['symbol', 'hod']).rv.mean().unstack(0); prof = prof / prof.mean()
    prof.round(4).rename(columns=lambda c: c[:3]).to_csv(os.path.join(a.out, 'figure1_intraday_profile.csv'))
    wd = d.groupby('dow').rv.mean(); wd = wd / wd.mean()
    L += ['## Section 4.1 Intraday and weekday pattern (2020-2023)', '',
          'Hourly RV relative to the daily mean, by UTC hour:', '', prof.round(2).to_markdown(), '',
          'RV by weekday relative to the weekly mean (Mon=0): ' +
          ', '.join(f'{k}: {v:.2f}' for k, v in wd.items()), '']

    # ---- Section 4.2 / Figure 2: event effects, design and test, per coin and pooled
    rows, fig2 = [], []
    for w, name in ((DESIGN, '2020-2023'), (TEST, '2024-2026')):
        for et in ['FOMC', 'CPI', 'NFP', 'FOMC_unsched']:
            for k in (0, 1):
                if et == 'FOMC_unsched' and name == '2024-2026': continue
                r = {'window': name, 'event': et, 'hour': 'release' if k == 0 else 'next'}
                for c in COINS:
                    s = summarise(event_values(p, ev, w, et, k, [c]))
                    r[f'{c[:3]} %'] = round(s['pct']); r[f'{c[:3]} t'] = round(s.get('t', np.nan), 2)
                s = summarise(event_values(p, ev, w, et, k))
                r.update({'pooled %': round(s['pct']), 'pooled t': round(s.get('t', np.nan), 2), 'n': s['n']})
                rows.append(r)
                if k == 0 and et != 'FOMC_unsched':
                    fig2.append(dict(window=name, event=et, pct=round(s['pct']), lo=round(s['lo']),
                                     hi=round(s['hi']), n=s['n']))
    pd.DataFrame(fig2).to_csv(os.path.join(a.out, 'figure2_event_effects.csv'), index=False)
    L += ['## Sections 4.2 and 5.2 Event effects (release hour and hour after)', '',
          pd.DataFrame(rows).to_markdown(index=False), '']

    # ---- Calendar coefficients: US open with and without macro flags; design vs test refit
    dm, tm = window(p, DESIGN), window(p, TEST)
    c3d, c4d, c4t = coefs(p, fa.M['M3'], dm), coefs(p, fa.M['M4'], dm), coefs(p, fa.M['M4'], tm)
    cols = ['us_open_hour', 'us_close_hour', 'exp_weekly', 'exp_monthly', 'exp_quarterly',
            'CPI_0', 'CPI_1', 'NFP_0', 'NFP_1', 'FOMC_0', 'FOMC_1']
    ct = pd.DataFrame({'design M3 %': [pct(c3d[c]) if c in c3d else np.nan for c in cols],
                       'design M4 %': [pct(c4d[c]) for c in cols], 'test M4 refit %': [pct(c4t[c]) for c in cols]},
                      index=cols).round(0)
    L += ['## Sections 4.1-4.2 and 5.3 Calendar coefficients (% change in RV)', '',
          'Design-window fits; the test-window column re-estimates M4 on 2024-2026 for description only.', '',
          ct.to_markdown(), '']

    # ---- Section 6: DVOL around releases, design and test (Figure 3)
    paths, drows = [], []
    for w, name in ((DVOL_DESIGN, '2021-2023'), (TEST, '2024-2026')):
        for et in ['CPI', 'FOMC', 'NFP']:
            res, pth = dvol_event(dv, ev, w, et, name); paths += pth
            for c, r in res.items():
                drows.append({'window': name, 'event': et, 'coin': c, **{k: round(v, 2) for k, v in r.items()}})
    pd.DataFrame(paths).round(3).to_csv(os.path.join(a.out, 'figure3_dvol_paths.csv'), index=False)
    L += ['## Section 6 DVOL around releases, event minus placebo (points of log DVOL)', '',
          'run-up = 48 h before to 1 h before; fall = 1 h before to 24 h after.', '',
          pd.DataFrame(drows).to_markdown(index=False), '']

    # ---- Section 7.2-7.3 post hoc checks
    fit = window(p, DESIGN); evm = window(p, TEST)
    P = {k: fa.fit_predict(p, fa.M[k], fit) for k in fa.M}
    g = lambda s, b, P_=P, sub=None, loss='se': fa.hour_level_test(p, evm, s, b, P_, loss=loss, subset=sub)
    fit2 = fit & ~((p.hour_utc >= '2020-03-01') & (p.hour_utc < '2020-04-01')).values
    P2 = {k: fa.fit_predict(p, fa.M[k], fit2) for k in ['M1', 'M4']}
    shut = ~p.hour_utc.dt.floor('D').isin(SHUTDOWN_DAYS).values
    y = p.lrv.values
    evset = evm & (p[['CPI_0', 'NFP_0', 'FOMC_0', 'FOMC_1']].sum(axis=1) > 0).values & shut
    h3_shut = 100 * (1 - ((y - P['M4'][0]) ** 2)[evset].mean() / ((y - P['M2'][0]) ** 2)[evset].mean())
    out = ~((p.hour_utc >= OUTAGE[0]) & (p.hour_utc <= OUTAGE[1])).values
    wk = (p.dow < 5).values
    L += ['## Section 7.2-7.3 Post hoc checks (labelled post hoc in the paper)', '',
          f"- H2 with March 2020 dropped from the fit: {g('M1', 'M4', P2)['mse_gain_pct']:.2f}%",
          f"- H2 dropping shutdown-shifted release days: {g('M1', 'M4', sub=shut)['mse_gain_pct']:.2f}%; H3: {h3_shut:.1f}%",
          f"- H2 weekday hours: {g('M1', 'M4', sub=wk)['mse_gain_pct']:.2f}%; weekend hours: {g('M1', 'M4', sub=~wk)['mse_gain_pct']:.2f}%"]
    for h, s_, b_ in (('H2', 'M1', 'M4'), ('H4', 'M1IV', 'M4IV'), ('H5', 'M4', 'M5')):
        r = g(s_, b_, sub=out, loss='qlike')
        L.append(f"- {h} QLIKE excluding the 28-29 Oct 2024 outage: {r['mse_gain_pct']:.2f}% (t {r['cw_t']:.2f})")
    L += ['', 'Appendix A, event effects by year (pooled, controls from the whole test window):', '']
    yr = []
    for et in ['FOMC', 'CPI', 'NFP']:
        v = event_values(p, ev, TEST, et)
        yr.append({'event': et, **{str(y_): f'{pct(v[v.index.year == y_].mean()):+.0f}% ({(v.index.year == y_).sum()})'
                                   for y_ in (2024, 2025, 2026)}})
    L += [pd.DataFrame(yr).to_markdown(index=False), '']
    # volatility-regime split (exploratory), coin-level values
    med = np.median(p.h168.values[fit]); E = p[evm]
    ctl = E[~E.any_macro].groupby(['symbol', 'hod', 'dow']).lrv.mean()
    L += ['Regime split (test window, coin-events; high = 168-hour RV above the design-window median):', '']
    for et in ['FOMC', 'CPI', 'NFP']:
        res = {}
        for h0 in ev[(ev.event_type == et) & (ev.h0 >= TEST[0]) & (ev.h0 < TEST[1])].h0:
            for r in E[E.hour_utc == h0].itertuples():
                res.setdefault('high' if r.h168 > med else 'low', []).append(r.lrv - ctl.get((r.symbol, r.hod, r.dow), np.nan))
        L.append(f'- {et}: ' + ', '.join(f'{k} {pct(np.nanmean(v)):+.0f}% (n={len(v)})' for k, v in sorted(res.items())))
    open(os.path.join(a.out, 'exploratory_results.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    for k in ('panel', 'dvol-btc', 'dvol-eth', 'cpi-nfp', 'fomc', 'out'): ap.add_argument(f'--{k}', required=True)
    ap.add_argument('--min-returns', type=int, default=3)
    main(ap.parse_args())
