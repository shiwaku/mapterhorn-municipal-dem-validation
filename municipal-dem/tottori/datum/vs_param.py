"""図郭ごとの差（rawdiff.csv）と、地理院の標高補正パラメータ dH（測地成果2011→2024）を比べる。"""
import csv
import numpy as np
from pyproj import Transformer

def load(path):
    d = {}
    for line in open(path, encoding='cp932').readlines()[16:]:
        p = line.split()
        if len(p) >= 2:
            d[p[0]] = float(p[1])
    return d

def mesh3(lon, lat):
    a = lat * 1.5; p = int(a); q = int((a - p) * 8); r = int(((a - p) * 8 - q) * 10)
    b = lon - 100; u = int(b); v = int((b - u) * 8); w = int(((b - u) * 8 - v) * 10)
    return f'{p}{u}{q}{v}{r}{w}'

tr, bm = load('/d/par/hyokorevTR_jgd2024_h.par'), load('/d/par/hyokorevBM_jgd2024_h.par')
rows = list(csv.DictReader(open('/d/rawdiff.csv')))
x = np.array([float(r['cx']) for r in rows]); y = np.array([float(r['cy']) for r in rows])
lon, lat = Transformer.from_crs(3857, 4326, always_xy=True).transform(x, y)
d = np.array([float(r['median']) for r in rows])
t = np.array([tr.get(mesh3(a, b), np.nan) for a, b in zip(lon, lat)])
b_ = np.array([bm.get(mesh3(a, b), np.nan) for a, b in zip(lon, lat)])
ok = ~np.isnan(t)
print(f'sheets={len(d)} with param={ok.sum()}')
print(f'diff (tottori-gsi) median={np.median(d):.3f}')
print(f'TR dH median={np.nanmedian(t):.3f} range={np.nanmin(t):.3f}..{np.nanmax(t):.3f}')
print(f'BM dH median={np.nanmedian(b_):.3f}')
r = d[ok] + t[ok]
print(f'diff + TR dH: median={np.median(r):+.3f} p10={np.percentile(r,10):+.3f} p90={np.percentile(r,90):+.3f} rms={np.sqrt(np.mean(r**2)):.3f}')
print(f'corr(diff, -TR dH)={np.corrcoef(d[ok], -t[ok])[0,1]:.2f}')
okb = ~np.isnan(b_); rb = d[okb] + b_[okb]
print(f'diff + BM dH: median={np.median(rb):+.3f} p10={np.percentile(rb,10):+.3f} p90={np.percentile(rb,90):+.3f} rms={np.sqrt(np.mean(rb**2)):.3f} corr={np.corrcoef(d[okb], -b_[okb])[0,1]:.2f}')
