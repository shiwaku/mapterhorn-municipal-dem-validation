"""本家版と検証版の Terrarium PMTiles を比べる。

使い方:
  python compare.py stats  <old.pmtiles> <new.pmtiles> <z> <minlon> <minlat> <maxlon> <maxlat>
  python compare.py render <pmtiles> <z> <minlon> <minlat> <maxlon> <maxlat> <out.png>

stats  : 範囲内のタイルを両方から読み、どちらにあるかと標高差の統計を出す
render : 範囲内のタイルをつないで陰影図（PNG）にする
"""
import io
import sys

import mercantile
import numpy as np
from PIL import Image
from pmtiles.reader import MmapSource, Reader


def open_reader(path):
    f = open(path, 'rb')
    return Reader(MmapSource(f))


def decode(data):
    rgb = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'), dtype=np.float64)
    return rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768


def tiles(z, bbox):
    return list(mercantile.tiles(*bbox, zooms=z))


def stats(old_path, new_path, z, bbox):
    old, new = open_reader(old_path), open_reader(new_path)
    only_old = only_new = both = 0
    diffs = []
    for t in tiles(z, bbox):
        a, b = old.get(t.z, t.x, t.y), new.get(t.z, t.x, t.y)
        if a and b:
            both += 1
            diffs.append((decode(b) - decode(a)).ravel())
        elif a:
            only_old += 1
        elif b:
            only_new += 1
    print(f'z{z}: both={both} only_old={only_old} only_new={only_new}')
    if diffs:
        d = np.concatenate(diffs)
        ad = np.abs(d)
        print(f'  new-old [m]: mean={d.mean():+.3f} median={np.median(d):+.3f} '
              f'|d| p50={np.percentile(ad, 50):.3f} p90={np.percentile(ad, 90):.3f} '
              f'p99={np.percentile(ad, 99):.3f} max={ad.max():.2f}')
        for th in (0.1, 0.5, 1, 5):
            print(f'  |d|>{th}m: {(ad > th).mean() * 100:.2f}%')


def hillshade(elev, pixel_m, az=315, alt=45):
    dy, dx = np.gradient(elev, pixel_m)
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    az, alt = np.radians(az), np.radians(alt)
    hs = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(hs * 255, 0, 255).astype(np.uint8)


def render(path, z, bbox, out):
    r = open_reader(path)
    ts = tiles(z, bbox)
    xs = sorted({t.x for t in ts})
    ys = sorted({t.y for t in ts})
    size = None
    canvas = None
    for t in ts:
        data = r.get(t.z, t.x, t.y)
        if not data:
            continue
        e = decode(data)
        if canvas is None:
            size = e.shape[0]
            canvas = np.full((len(ys) * size, len(xs) * size), np.nan)
        i, j = ys.index(t.y), xs.index(t.x)
        canvas[i * size:(i + 1) * size, j * size:(j + 1) * size] = e
    if canvas is None:
        print('no tiles')
        return
    lat = (bbox[1] + bbox[3]) / 2
    pixel_m = 40075016.686 * np.cos(np.radians(lat)) / (2 ** z * size)
    filled = np.where(np.isnan(canvas), 0, canvas)
    Image.fromarray(hillshade(filled, pixel_m)).save(out)
    print(f'{out}: z{z} {canvas.shape[1]}x{canvas.shape[0]} px, {pixel_m:.2f} m/px')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'stats':
        stats(sys.argv[2], sys.argv[3], int(sys.argv[4]), [float(v) for v in sys.argv[5:9]])
    elif cmd == 'render':
        render(sys.argv[2], int(sys.argv[3]), [float(v) for v in sys.argv[4:8]], sys.argv[8])
