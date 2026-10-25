"""作った Terrarium PMTiles（鳥取入り）と本家の PMTiles を、同じタイルの画素ごとに比べ、差（作った − 本家）の基礎統計を出す。

使い方:
  python pixel_tiles.py <本家.pmtiles> <作った.pmtiles> <z> <範囲の GeoJSON> <出力の接頭辞> [processes]

- 範囲の GeoJSON（source_coverage.py の出力）の外接矩形に掛かる z のタイルを、両方にあるものだけ読む
- 画素を「鳥取 0.5m の範囲の中」と「外」に分けて数える。外は地理院 DEM どうしなので 0 に近いはず
- Terrarium の分解能は 1/256m（約 4mm）。百分位は 1mm 刻みのヒストグラム（±HIST_MAX m）から
"""
import io
import json
import sys
from multiprocessing import Pool

import mercantile
import numpy as np
from PIL import Image
from pmtiles.reader import MmapSource, Reader
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from shapely.geometry import box, shape
from shapely.ops import transform as stransform
from pyproj import Transformer

BIN = 0.001
HIST_MAX = 5.0
OLD = NEW = COVER = None


def decode(data):
    rgb = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'), dtype=np.float64)
    return rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768


def init(old_path, new_path, cover):
    global OLD, NEW, COVER
    OLD, NEW = Reader(MmapSource(open(old_path, 'rb'))), Reader(MmapSource(open(new_path, 'rb')))
    COVER = cover


def empty():
    return {'n': 0, 's': 0.0, 'ss': 0.0, 'min': np.inf, 'max': -np.inf,
            'h': np.zeros(int(2 * HIST_MAX / BIN), np.int64), 'out': 0}


def add(acc, d):
    if d.size == 0:
        return
    acc['n'] += d.size
    acc['s'] += d.sum()
    acc['ss'] += (d * d).sum()
    acc['min'] = min(acc['min'], d.min())
    acc['max'] = max(acc['max'], d.max())
    acc['h'] += np.histogram(d, bins=acc['h'].size, range=(-HIST_MAX, HIST_MAX))[0]
    acc['out'] += int((np.abs(d) >= HIST_MAX).sum())


def work(chunk):
    res = {'inside': empty(), 'outside': empty(), 'both': 0, 'only_old': 0, 'only_new': 0}
    for z, x, y in chunk:
        a, b = OLD.get(z, x, y), NEW.get(z, x, y)
        if not (a and b):
            res['only_old' if a else 'only_new'] += 1 if (a or b) else 0
            continue
        res['both'] += 1
        d = decode(b) - decode(a)
        xy = mercantile.xy_bounds(x, y, z)
        tb = box(xy.left, xy.bottom, xy.right, xy.top)
        if COVER.contains(tb):
            m = np.ones(d.shape, bool)
        elif not COVER.intersects(tb):
            m = np.zeros(d.shape, bool)
        else:
            t = from_bounds(xy.left, xy.bottom, xy.right, xy.top, d.shape[1], d.shape[0])
            m = rasterize([COVER.intersection(tb)], out_shape=d.shape, transform=t, dtype='uint8').astype(bool)
        add(res['inside'], d[m])
        add(res['outside'], d[~m])
    return res


def summary(acc):
    n, h = acc['n'], acc['h']
    if n == 0:
        return {}
    mean = acc['s'] / n
    c = h.cumsum()
    centers = -HIST_MAX + (np.arange(h.size) + 0.5) * BIN
    pct = lambda p: centers[min(int(np.searchsorted(c, p / 100 * c[-1])), h.size - 1)]
    med = pct(50)
    dev = np.abs(centers - med)
    o = np.argsort(dev)
    nmad = 1.4826 * dev[o][int(np.searchsorted(h[o].cumsum(), c[-1] / 2))]
    gt = lambda thr: h[np.abs(centers) > thr].sum() / c[-1] * 100
    return {'n': n, 'mean': f'{mean:+.4f}', 'median': f'{med:+.4f}', 'std': f'{np.sqrt(acc["ss"] / n - mean ** 2):.4f}',
            'rms': f'{np.sqrt(acc["ss"] / n):.4f}', 'nmad': f'{nmad:.4f}',
            **{f'p{p}': f'{pct(p):+.4f}' for p in (1, 5, 25, 75, 95, 99)},
            'min': f'{acc["min"]:+.4f}', 'max': f'{acc["max"]:+.4f}',
            'abs_gt_0.1m': f'{gt(0.1):.2f}%', 'abs_gt_0.5m': f'{gt(0.5):.2f}%', 'outside_5m': acc['out']}


def main():
    old_path, new_path, z, cover_path, prefix = sys.argv[1:6]
    z = int(z)
    procs = int(sys.argv[6]) if len(sys.argv) > 6 else 4
    g = shape(json.load(open(cover_path, encoding='utf-8'))['features'][0]['geometry'])
    cover = stransform(Transformer.from_crs(4326, 3857, always_xy=True).transform, g)
    tiles = [(t.z, t.x, t.y) for t in mercantile.tiles(*g.bounds, zooms=z)]
    chunks = [tiles[i:i + 50] for i in range(0, len(tiles), 50)]
    print(f'z{z}: {len(tiles)} tiles in bbox', flush=True)
    with Pool(procs, initializer=init, initargs=(old_path, new_path, cover)) as pool:
        parts = pool.map(work, chunks, chunksize=1)
    tot = {'inside': empty(), 'outside': empty()}
    for p in parts:
        for k in tot:
            a, b = tot[k], p[k]
            for f in ('n', 's', 'ss', 'out'):
                a[f] += b[f]
            a['min'], a['max'] = min(a['min'], b['min']), max(a['max'], b['max'])
            a['h'] += b['h']
    counts = {k: sum(p[k] for p in parts) for k in ('both', 'only_old', 'only_new')}
    s = {k: summary(v) for k, v in tot.items()}
    keys = list(s['inside'].keys())
    with open(f'{prefix}_summary.tsv', 'w') as f:
        f.write(f'# z{z} tiles: both={counts["both"]} only_old={counts["only_old"]} only_new={counts["only_new"]}\n')
        f.write('stat\tinside_tottori\toutside_tottori\n')
        for k in keys:
            f.write(f'{k}\t{s["inside"].get(k, "")}\t{s["outside"].get(k, "")}\n')
    print(open(f'{prefix}_summary.tsv').read())


if __name__ == '__main__':
    main()
