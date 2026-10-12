"""mesh_diff.tsv を地域・種類ごとにまとめ、差 + BM dH と 差 + TR dH の残りを比べる。"""
import csv, sys
import numpy as np
rows = list(csv.DictReader(open(sys.argv[1]), delimiter='\t'))
print('region kind n | diff_med | +BM med rms | +TR med rms | fit diff=a+k*(-dH): k_BM a_BM sd | k_TR a_TR sd')
for reg in sorted({r['region'] for r in rows}):
    for kind in ('hot', 'ctrl', 'all'):
        rr = [r for r in rows if r['region'] == reg and (kind == 'all' or r['kind'] == kind)]
        if len(rr) < 3:
            continue
        d = np.array([float(r['median']) for r in rr]); b = np.array([float(r['bm']) for r in rr]); t = np.array([float(r['tr']) for r in rr])
        def fit(x):
            A = np.c_[np.ones_like(x), -x]; c, *_ = np.linalg.lstsq(A, d, rcond=None); res = d - A @ c
            return f'{c[1]:+.2f} {c[0]:+.3f} {res.std():.3f}'
        rb, rt = d + b, d + t
        print(f'{reg} {kind} {len(rr)} | {np.median(d):+.3f} | {np.median(rb):+.3f} {np.sqrt(np.mean((rb-np.median(rb))**2)):.3f} | '
              f'{np.median(rt):+.3f} {np.sqrt(np.mean((rt-np.median(rt))**2)):.3f} | {fit(b)} | {fit(t)}')
