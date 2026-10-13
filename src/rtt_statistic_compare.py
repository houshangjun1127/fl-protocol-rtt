#!/usr/bin/env python
"""WP-11: does the winner change when the statistic that decides "reached"
changes?

Round-to-target (RTT) is not a single object: it is the first-passage time of
*some* series that the protocol chooses.  We compare three decision statistics
that are all in routine use, applied to the SAME 294 Stage-B traces:

  (a) first-passage    S_r = acc_r
                       -- "the round at which test accuracy first reaches t".
                          This is the definition used everywhere in this paper.
  (b) 5-round mean     S_r = mean(acc_{r-4..r}),   r >= 5
                       -- a short trailing average; the most common informal
                          way of "smoothing the curve before reading off a
                          crossing".
  (c) 10-round mean    S_r = mean(acc_{r-9..r}),   r >= 10
                       -- a long trailing / final-window average, the
                          Morafah-style "converged accuracy" reading.

For each statistic phi, RTT_phi(t) = min{ r : S^phi_r >= t }, and INF if the
run never satisfies it inside the 60-round budget (right-censored).

Everything below is computed from the existing traces; no model is trained.
The point of the exercise is not to argue for one statistic over another -- it
is to measure how much of the ranking is a property of the curve and how much
is a property of the reading rule.

Usage
-----
    python src/rtt_statistic_compare.py
    python src/rtt_statistic_compare.py --out results/rtt_stat_compare.json

Output: a JSON blob plus a human-readable table on stdout.  The numbers that
go into the paper are re-printed under a "PAPER" heading at the end.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import statistics as st
from collections import defaultdict
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRACEDIR = os.path.join(ROOT, 'results', 'rank_inv')

DATASETS = ['mnist', 'fashion', 'cifar10']
ALPHAS = {'mnist': ['0.05', '0.1', '0.3'],
          'fashion': ['0.05', '0.1', '0.3'],
          'cifar10': ['0.1']}
METHODS = ['fedavg', 'fedavgm', 'feddyn', 'scaffold', 'fedproxw',
           'fedadam', 'uniform']
SEEDS = list(range(6))

# target grid: 1 percentage point, the same resolution the main analyzer uses
TGRID = [round(0.30 + 0.01 * i, 2) for i in range(61)]   # 0.30 .. 0.90

STATS = ['first', 'ma5', 'ma10']
STAT_LABEL = {'first': 'first-passage',
              'ma5': '5-round mean',
              'ma10': '10-round mean'}
WIN = {'first': 1, 'ma5': 5, 'ma10': 10}

INF = float('inf')


# --------------------------------------------------------------------------- io
def load_trace(dataset, alpha, method, seed):
    """Return the per-round accuracy list (1-based index == round number)."""
    pat = os.path.join(TRACEDIR, f'{dataset}_a{alpha}_{method}_*_s{seed}.json')
    hits = glob.glob(pat)
    if not hits:
        return None
    if len(hits) > 1:
        # tuned variants: prefer the shortest (canonical) hp tag
        hits.sort(key=len)
    with open(hits[0], encoding='utf-8') as fh:
        d = json.load(fh)
    tr = d.get('trace') or []
    acc = [None] + [float(x['acc']) for x in sorted(tr, key=lambda z: z['round'])]
    return acc, os.path.basename(hits[0])


# ------------------------------------------------------------------- statistics
def smooth(acc, w):
    """Trailing w-round mean series, aligned so out[r] uses rounds r-w+1..r."""
    n = len(acc) - 1                      # acc is 1-based
    out = [None] * (n + 1)
    for r in range(w, n + 1):
        out[r] = sum(acc[r - w + 1:r + 1]) / float(w)
    return out


def rtt_all(acc):
    """First-passage RTT of every decision statistic, on the full TGRID.

    Returns {stat: {t: round or INF}}.
    """
    series = {s: (acc if s == 'first' else smooth(acc, WIN[s])) for s in STATS}
    res = {}
    for s in STATS:
        ser = series[s]
        tbl = {}
        for t in TGRID:
            hit = INF
            for r in range(1, len(ser)):
                v = ser[r]
                if v is not None and v >= t:
                    hit = r
                    break
            tbl[t] = hit
        res[s] = tbl
    return res


def rank_at(rt, t, methods):
    """Order methods by RTT ascending; non-reachers go last, ordered by
    descending RTT-censoring severity (all INF -> tie).  Returns a list of
    method names in rank order."""
    reach = [m for m in methods if rt[m] < INF]
    non = [m for m in methods if rt[m] == INF]
    reach.sort(key=lambda m: (rt[m], m))
    non.sort(key=lambda m: m)
    return reach + non


# ------------------------------------------------------------------------- main
def build():
    data = defaultdict(dict)      # (ds, a, seed) -> method -> {stat: {t: rtt}}
    srcmap = {}
    missing = []
    for ds in DATASETS:
        for a in ALPHAS[ds]:
            for seed in SEEDS:
                for m in METHODS:
                    got = load_trace(ds, a, m, seed)
                    if got is None:
                        missing.append((ds, a, m, seed))
                        continue
                    acc, fn = got
                    data[(ds, a, seed)][m] = rtt_all(acc)
                    srcmap[(ds, a, m, seed)] = fn
    return data, srcmap, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'results',
                                                 'rtt_stat_compare.json'))
    ap.add_argument('--tau', type=float, default=2.0,
                    help='near-tie filter in rounds (same value as the main '
                         'analyzer)')
    args = ap.parse_args()

    data, srcmap, missing = build()
    cells = [(ds, a) for ds in DATASETS for a in ALPHAS[ds]]

    out = {'tau_rounds': args.tau, 'tgrid': [TGRID[0], TGRID[-1], 0.01],
           'stats': STATS, 'n_traces_used': sum(len(v) for v in data.values()),
           'missing': [list(x) for x in missing]}

    # ---------------------------------------------------------- per-cell winner
    cell_tab = {}
    for (ds, a) in cells:
        seeds = [s for s in SEEDS if (ds, a, s) in data]
        row = {'seeds': seeds, 'methods': {}}
        # reference target: highest t on the grid reached by >= 5 of 7 methods
        # under first-passage on a majority of seeds
        reach_count = {}
        for t in TGRID:
            c = 0
            for s in seeds:
                c += sum(1 for m in METHODS
                         if data[(ds, a, s)][m]['first'][t] < INF)
            reach_count[t] = c / float(len(seeds) * len(METHODS))
        cand = [t for t in TGRID if reach_count[t] >= 5.0 / 7.0]
        tref = max(cand) if cand else None
        row['t_ref'] = tref
        row['reach_fraction'] = {f'{t:.2f}': round(reach_count[t], 3)
                                 for t in TGRID[::5]}

        for m in METHODS:
            ent = {}
            for stat in STATS:
                vals = [data[(ds, a, s)][m][stat][tref] for s in seeds] \
                    if tref is not None else []
                fin = [v for v in vals if v < INF]
                ent[stat] = {'mean_rtt': (round(st.mean(fin), 2) if fin else None),
                             'n_reach': len(fin), 'n_seeds': len(seeds),
                             'per_seed': [None if v == INF else v for v in vals]}
            row['methods'][m] = ent

        if tref is not None:
            for stat in STATS:
                sc = {}
                for s in seeds:
                    rt = {m: data[(ds, a, s)][m][stat][tref] for m in METHODS}
                    order = rank_at(rt, tref, METHODS)
                    sc[s] = order[0]
                row[f'winner_{stat}_per_seed'] = sc
                cnt = defaultdict(int)
                for s in seeds:
                    cnt[sc[s]] += 1
                row[f'winner_{stat}'] = dict(cnt)
            # rank position per method under each statistic (mean over seeds)
            for stat in STATS:
                pos = defaultdict(list)
                for s in seeds:
                    rt = {m: data[(ds, a, s)][m][stat][tref] for m in METHODS}
                    for i, m in enumerate(rank_at(rt, tref, METHODS)):
                        pos[m].append(i + 1)
                for m in METHODS:
                    row['methods'][m][stat]['mean_rank'] = \
                        round(st.mean(pos[m]), 2)
        cell_tab[f'{ds}|a{a}'] = row

    out['per_cell'] = cell_tab

    # ------------------------------------------- winner / order flips, pooled
    # A "comparable unit" is a (cell, seed, target) where at least two methods
    # reach t under BOTH statistics being compared.  Within a unit we compare
    # the full ordering restricted to those commonly-reaching methods.
    flips = {}
    for s1, s2 in combinations(STATS, 2):
        key = f'{s1}_vs_{s2}'
        tot = 0
        winflip = 0
        pair_tot = 0
        pair_flip = 0
        per_cell = {}
        for (ds, a) in cells:
            seeds = [s for s in SEEDS if (ds, a, s) in data]
            c_u = c_w = c_p = c_pf = 0
            for seed in seeds:
                for t in TGRID:
                    r1 = {m: data[(ds, a, seed)][m][s1][t] for m in METHODS}
                    r2 = {m: data[(ds, a, seed)][m][s2][t] for m in METHODS}
                    common = [m for m in METHODS
                              if r1[m] < INF and r2[m] < INF]
                    if len(common) < 2:
                        continue
                    c_u += 1
                    o1 = [m for m in sorted(common, key=lambda m: (r1[m], m))]
                    o2 = [m for m in sorted(common, key=lambda m: (r2[m], m))]
                    if o1[0] != o2[0]:
                        c_w += 1
                    for x, y in combinations(common, 2):
                        d1 = r1[x] - r1[y]
                        d2 = r2[x] - r2[y]
                        if abs(d1) < args.tau or abs(d2) < args.tau:
                            continue        # near tie -> not a real reordering
                        c_p += 1
                        if (d1 > 0) != (d2 > 0):
                            c_pf += 1
            per_cell[f'{ds}|a{a}'] = {'units': c_u, 'winner_flips': c_w,
                                      'pairs': c_p, 'pair_flips': c_pf}
            tot += c_u; winflip += c_w; pair_tot += c_p; pair_flip += c_pf
        flips[key] = {'per_cell': per_cell,
                      'units': tot, 'winner_flips': winflip,
                      'winner_flip_rate': round(winflip / tot, 4) if tot else None,
                      'pairs': pair_tot, 'pair_flips': pair_flip,
                      'pair_flip_rate': round(pair_flip / pair_tot, 4)
                      if pair_tot else None}
    out['statistic_flips'] = flips

    # ------------------------------------- spike premium: RTT_smooth - RTT_first
    spike = {}
    for (ds, a) in cells:
        seeds = [s for s in SEEDS if (ds, a, s) in data]
        ent = {}
        for m in METHODS:
            ent[m] = {}
            for stat in ['ma5', 'ma10']:
                ds_ = []
                for s in seeds:
                    for t in TGRID:
                        v1 = data[(ds, a, s)][m]['first'][t]
                        v2 = data[(ds, a, s)][m][stat][t]
                        if v1 < INF and v2 < INF:
                            ds_.append(v2 - v1)
                ent[m][f'{stat}_minus_first'] = {
                    'median': round(st.median(ds_), 2) if ds_ else None,
                    'mean': round(st.mean(ds_), 2) if ds_ else None,
                    'max': max(ds_) if ds_ else None,
                    'n': len(ds_)}
        spike[f'{ds}|a{a}'] = ent
    out['spike_premium'] = spike

    # --------------------------------------------------------------- reporting
    lines = []
    lines.append('=' * 78)
    lines.append('WP-11  three decision statistics for "reached", same 294 traces')
    lines.append('=' * 78)
    lines.append(f'traces used: {out["n_traces_used"]}   missing: {len(missing)}')
    lines.append('')
    for ck, row in cell_tab.items():
        lines.append(f'--- {ck}   t_ref = {row["t_ref"]} ---')
        hdr = f'{"method":10s}' + ''.join(f'{STAT_LABEL[s]:>16s}' for s in STATS)
        lines.append(hdr)
        for m in METHODS:
            e = row['methods'][m]
            cells_ = ''
            for s in STATS:
                v = e[s]['mean_rtt']
                rk = e[s].get('mean_rank')
                cells_ += f'{("-" if v is None else f"{v:5.1f}")+"("+str(rk)+")":>16s}'
            lines.append(f'{m:10s}' + cells_)
        for s in STATS:
            lines.append(f'  winner under {STAT_LABEL[s]}: '
                         f'{row.get(f"winner_{s}")}')
        lines.append('')

    lines.append('--- winner / order flips between statistics (pooled) ---')
    for k, v in flips.items():
        lines.append(f'{k:16s} units={v["units"]:6d} '
                     f'winner_flips={v["winner_flips"]:5d} '
                     f'rate={v["winner_flip_rate"]}   '
                     f'pairs={v["pairs"]:7d} pair_flips={v["pair_flips"]:6d} '
                     f'rate={v["pair_flip_rate"]}')

    lines.append('')
    lines.append('--- spike premium: rounds added by smoothing (median over '
                 'seed x target) ---')
    for ck in [f'{ds}|a{a}' for ds in DATASETS for a in ALPHAS[ds]]:
        ent = spike[ck]
        lines.append(f'  {ck}')
        for m in METHODS:
            a5 = ent[m]['ma5_minus_first']
            a10 = ent[m]['ma10_minus_first']
            lines.append(f'    {m:10s} ma5 : {a5["median"]:>6} (max '
                         f'{a5["max"]}, n={a5["n"]})   '
                         f'ma10: {a10["median"]:>6} (max {a10["max"]}, '
                         f'n={a10["n"]})')

    txt = '\n'.join(lines)
    print(txt)

    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    with open(args.out.replace('.json', '.txt'), 'w', encoding='utf-8') as fh:
        fh.write(txt + '\n')
    print(f'\nwrote {args.out}')


if __name__ == '__main__':
    main()
