"""手元の DEM ごとに、標高が改定前（測地成果2011）か改定後（2024）かを判定する。
範囲内の 3 次メッシュを無作為に選び、DEM − 地理院 1m（DEM1A、改定後）の差の中央値を出す。
改定前なら差は −dH（BM）、改定後なら 0 付近になる。

使い方: python datum_check.py <dems.tsv> <parフォルダ> <latest_1.csv> <cacheフォルダ> > datum_check.tsv
dems.tsv は「名前<TAB>パス」の行。"""
import csv, random, re, sys, os, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np, rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds

DEMS, PAR, LIST, CACHE = sys.argv[1:5]
N = 60


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
meshes = sorted(set(bm) & set(gsi))
nodes = {c: node(c) for c in meshes}

dems = [l.rstrip('\n').split('\t') for l in open(DEMS, encoding='utf-8') if l.strip() and not l.startswith('#')]
jobs = []
rng = random.Random(0)
for name, path in dems:
    with rasterio.open(path) as d:
        w, s, e, n = transform_bounds(d.crs, 'EPSG:4326', *d.bounds)
    # メッシュの格子点は南西隅なので、メッシュ全体が範囲に入るものを選ぶ
    cand = [c for c in meshes if w <= nodes[c][0] and nodes[c][0] + 1 / 80 <= e and s <= nodes[c][1] and nodes[c][1] + 1 / 120 <= n]
    jobs += [(name, path, c) for c in rng.sample(cand, min(N, len(cand)))]
    print(f'{name}: {len(cand)} meshes in bbox', file=sys.stderr)


def run(job):
    name, dem, c = job
    path = os.path.join(CACHE, os.path.basename(gsi[c]))
    if not os.path.exists(path):
        req = urllib.request.Request(gsi[c], headers={'User-Agent': 'curl/8.0'})
        with urllib.request.urlopen(req) as r, open(path + '.part', 'wb') as f:
            f.write(r.read())
        os.replace(path + '.part', path)
    with rasterio.open(path) as g, rasterio.open(dem) as m:
        a = g.read(1, masked=True)
        with WarpedVRT(m, crs=g.crs, transform=g.transform, width=g.width, height=g.height,
                       resampling=Resampling.average, src_nodata=m.nodata, nodata=-9999) as v:
            b = v.read(1, masked=True)
    ok = ~(np.ma.getmaskarray(a) | np.ma.getmaskarray(b)) & (b.data > -1000) & (b.data < 10000) & (a.data > -1000)
    if ok.sum() < 1000:
        return None
    d = (b.data - a.data)[ok]
    return [name, c, int(ok.sum()), f'{np.median(d):.3f}', f'{np.percentile(d, 25):.3f}',
            f'{np.percentile(d, 75):.3f}', bm[c], tr.get(c, '')]


out = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')
out.writerow(['region', 'mesh', 'n', 'median', 'p25', 'p75', 'bm', 'tr'])
with ThreadPoolExecutor(8) as ex:
    for i, row in enumerate(ex.map(run, jobs)):
        if row:
            out.writerow(row); sys.stdout.flush()
        if i % 50 == 0:
            print(f'{i}/{len(jobs)}', file=sys.stderr)
