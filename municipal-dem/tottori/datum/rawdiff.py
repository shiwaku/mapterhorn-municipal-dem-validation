"""元の GeoTIFF（source-store, EPSG:3857）どうしで 鳥取 0.5m − 地理院 1m の差を図郭ごとに出す。
鳥取を地理院 1m の格子へ平均で寄せてから引く。"""
import csv, glob, sys
import numpy as np, rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling

S = '/work/source-store'
gsi = list(csv.DictReader(open(f'{S}/jpdem1a/bounds.csv')))
out = csv.writer(sys.stdout)
out.writerow(['tottori', 'cx', 'cy', 'n', 'median', 'p10', 'p90', 'tott_mean'])
for t in csv.DictReader(open(f'{S}/jptottori/bounds.csv')):
    tl, tb, tr, tt = (float(t[k]) for k in ('left', 'bottom', 'right', 'top'))
    diffs, elev = [], []
    for g in gsi:
        gl, gb, gr, gt = (float(g[k]) for k in ('left', 'bottom', 'right', 'top'))
        if gr <= tl or gl >= tr or gt <= tb or gb >= tt:
            continue
        with rasterio.open(f'{S}/jpdem1a/{g["filename"]}') as gd, rasterio.open(f'{S}/jptottori/{t["filename"]}') as td:
            a = gd.read(1, masked=True)
            with WarpedVRT(td, crs=gd.crs, transform=gd.transform, width=gd.width, height=gd.height,
                           resampling=Resampling.average) as v:
                b = v.read(1, masked=True)
        m = ~(np.ma.getmaskarray(a) | np.ma.getmaskarray(b))
        if m.sum():
            diffs.append((b.data - a.data)[m]); elev.append(b.data[m])
    if diffs:
        d = np.concatenate(diffs); e = np.concatenate(elev)
        out.writerow([t['filename'], f'{(tl+tr)/2:.0f}', f'{(tb+tt)/2:.0f}', d.size,
                      f'{np.median(d):.3f}', f'{np.percentile(d,10):.3f}', f'{np.percentile(d,90):.3f}', f'{e.mean():.1f}'])
