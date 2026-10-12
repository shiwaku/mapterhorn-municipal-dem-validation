"""3 次メッシュごとに、手元の自治体 DEM − 地理院 1m（DEM1A、改定後）の差の中央値を出す。
自治体 DEM が改定前の標高なら、差はおよそ −dH になる。BM と TR のどちらの dH に近いかを見る。

使い方: python mesh_diff.py <hotspots.tsv> <parフォルダ> <latest_1.csv> <cacheフォルダ> > mesh_diff.tsv
hotspots.tsv の地域に加え、各地域から |TR-BM| の小さいメッシュも対照として 40 ずつ選ぶ。"""
import csv, random, re, sys, os, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np, rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling

HOT, PAR, LIST, CACHE = sys.argv[1:5]
DEM = {
    'nagano': 'E:/GIS/pref-nagano/csmap-py/nagano-dem.tif',
    'yamanashi': 'E:/GIS/pref-yamanashi/csmap-py/yamanashi-dem.tif',
    'toyama': 'E:/GIS/pref-toyama/csmap-py/toyama-dem.tif',
    'saitama': 'E:/GIS/pref-saitama/lp-pointcloud/grd/merged_05m_v2.tif',
    'shizuoka-east': 'H:/GIS/geospatial/shizuoka-pointcloud/shizuoka-mt-fuji-shizuoka-east/fuji-shizuoka-east-dem.tif',
}
BBOX = {'nagano': (137.46, 138.74, 35.18, 37.04), 'yamanashi': (138.18, 139.14, 35.17, 35.97),
        'toyama': (136.77, 137.70, 36.27, 36.99), 'saitama': (138.70, 139.57, 35.75, 36.30),
        'shizuoka-east': (138.51, 138.90, 35.12, 35.45)}


def load(path):
    d = {}
    for line in open(path, encoding='cp932').readlines()[16:]:
        p = line.split()
        if len(p) >= 2 and len(p[0]) == 8 and p[0].isdigit():
            d[p[0]] = float(p[1])
    return d


def node(c):
    return 100 + int(c[2:4]) + int(c[5]) / 8 + int(c[7]) / 80, (int(c[0:2]) + int(c[4]) / 8 + int(c[6]) / 80) / 1.5


bm, tr = load(f'{PAR}/hyokorevBM_jgd2024_h.par'), load(f'{PAR}/hyokorevTR_jgd2024_h.par')
gsi = {}
for r in csv.DictReader(open(LIST)):
    m = re.search(r'FG-GML-(\d{4})-(\d)(\d)-(\d)(\d)-DEM1A', r['url'])
    if m:
        gsi[''.join(m.groups())] = r['url']

jobs = [(r['region'], r['mesh'], 'hot') for r in csv.DictReader(open(HOT), delimiter='\t') if r['region'] in DEM]
rng = random.Random(0)
for name, (w, e, s, n) in BBOX.items():
    cand = [c for c in set(bm) & set(tr) & set(gsi) if abs(tr[c] - bm[c]) < 0.02
            and w <= node(c)[0] <= e and s <= node(c)[1] <= n]
    jobs += [(name, c, 'ctrl') for c in rng.sample(sorted(cand), min(40, len(cand)))]
print(f'{len(jobs)} meshes', file=sys.stderr)


def run(job):
    region, c, kind = job
    path = os.path.join(CACHE, os.path.basename(gsi[c]))
    if not os.path.exists(path):
        req = urllib.request.Request(gsi[c], headers={'User-Agent': 'curl/8.0'})
        with urllib.request.urlopen(req) as r, open(path + '.part', 'wb') as f:
            f.write(r.read())
        os.replace(path + '.part', path)
    with rasterio.open(path) as g, rasterio.open(DEM[region]) as m:
        a = g.read(1, masked=True)
        with WarpedVRT(m, crs=g.crs, transform=g.transform, width=g.width, height=g.height,
                       resampling=Resampling.average, src_nodata=m.nodata, nodata=-9999) as v:
            b = v.read(1, masked=True)
    ok = ~(np.ma.getmaskarray(a) | np.ma.getmaskarray(b)) & (b.data > -1000) & (a.data > -1000)
    if ok.sum() < 10000:
        return None
    d = (b.data - a.data)[ok]
    return [region, c, kind, int(ok.sum()), f'{np.median(d):.3f}', f'{np.percentile(d, 25):.3f}',
            f'{np.percentile(d, 75):.3f}', bm[c], tr[c]]


out = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')
out.writerow(['region', 'mesh', 'kind', 'n', 'median', 'p25', 'p75', 'bm', 'tr'])
with ThreadPoolExecutor(8) as ex:
    for i, row in enumerate(ex.map(run, jobs)):
        if row:
            out.writerow(row); sys.stdout.flush()
        if i % 50 == 0:
            print(f'{i}/{len(jobs)}', file=sys.stderr)
