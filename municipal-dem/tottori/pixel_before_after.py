"""補正前（ZIP の元の図郭）と補正後（source-store の図郭）を画素ごとに比べ、差の基礎統計を出す。

使い方（work-full で実行）:
  python ../pixel_before_after.py <補正前の一覧.txt> <dH グリッド.tif> <出力の接頭辞> [processes]

- 差 = 補正後 − 補正前。両方に値がある画素だけ数える（補正前は NoData 値のない図郭があるので -9999 も NoData とみなす）
- 残差 = 差 − dH。dH は source_vertical_shift.py と同じく、グリッドを図郭の格子へ bilinear で寄せる。
  COG 化（LERC、MAX_Z_ERROR=0.001）の誤差がここに出る
- 片方だけに値がある画素も数える（0 埋めを NoData にした図郭など）
- 出力: <接頭辞>_sheets.tsv（図郭ごと）、<接頭辞>_summary.tsv（全体。百分位は 0.1mm 刻みのヒストグラムから）、<接頭辞>_hist.npz（グラフ用）
"""
import os
import sys
from multiprocessing import Pool

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

NODATA = -9999
BIN = 0.0001
DIFF_RANGE = (-0.5, 0.5)    # 差のヒストグラムの範囲（m）
RESID_RANGE = (-0.05, 0.05)  # 残差のヒストグラムの範囲（m）
GRID = None


def hist(x, lo, hi):
    n = int(round((hi - lo) / BIN))
    h, _ = np.histogram(x, bins=n, range=(lo, hi))
    return h.astype(np.int64), int((x < lo).sum()), int((x >= hi).sum())


def compare(before_path):
    name = os.path.basename(before_path)
    with rasterio.open(before_path) as b:
        a0 = b.read(1)
        nd0 = b.nodata
        transform, crs = b.transform, b.crs
    with rasterio.open(f'source-store/jptottori/{name}') as s:
        assert s.transform == transform and s.shape == a0.shape, name
        a1 = s.read(1)
        nd1 = s.nodata
    v0 = (a0 != NODATA) & ((a0 != nd0) if nd0 is not None else True) & np.isfinite(a0)
    v1 = (a1 != nd1) & np.isfinite(a1)
    both = v0 & v1
    row = {'sheet': name, 'n_both': int(both.sum()), 'only_before': int((v0 & ~v1).sum()), 'only_after': int((v1 & ~v0).sum())}
    if not both.any():
        return row, None
    dh = np.full(a0.shape, np.nan, dtype=np.float32)
    with rasterio.open(GRID) as g:
        reproject(rasterio.band(g, 1), dh, src_transform=g.transform, src_crs=g.crs, src_nodata=np.nan,
                  dst_transform=transform, dst_crs=crs, dst_nodata=np.nan, resampling=Resampling.bilinear)
    d = (a1[both].astype(np.float64) - a0[both])
    r = d - dh[both]
    row.update(mean=d.mean(), std=d.std(), min=d.min(), max=d.max(), median=float(np.median(d)),
               resid_mean=r.mean(), resid_absmax=float(np.abs(r).max()))
    acc = {'n': d.size, 's': d.sum(), 'ss': (d * d).sum(), 'min': d.min(), 'max': d.max(),
           'rs': r.sum(), 'rss': (r * r).sum(), 'rmin': r.min(), 'rmax': r.max(),
           'h': hist(d, *DIFF_RANGE), 'rh': hist(r, *RESID_RANGE)}
    return row, acc


def init(grid):
    global GRID
    GRID = grid


def pct(h, under, lo, ps):
    c = np.concatenate([[under], h]).cumsum()
    total = c[-1]
    out = {}
    for p in ps:
        i = int(np.searchsorted(c, p / 100 * total))
        out[p] = lo + (i - 1 + 0.5) * BIN if i > 0 else float('-inf')
    return out


def main():
    lst, grid, prefix = sys.argv[1:4]
    procs = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    paths = [l.strip() for l in open(lst) if l.strip()]
    with Pool(procs, initializer=init, initargs=(grid,)) as pool:
        results = pool.map(compare, paths, chunksize=2)
    cols = ['sheet', 'n_both', 'only_before', 'only_after', 'mean', 'std', 'min', 'max', 'median', 'resid_mean', 'resid_absmax']
    with open(f'{prefix}_sheets.tsv', 'w') as f:
        f.write('\t'.join(cols) + '\n')
        for row, _ in results:
            f.write('\t'.join(f'{row[c]:.4f}' if isinstance(row.get(c), float) else str(row.get(c, '')) for c in cols) + '\n')
    accs = [a for _, a in results if a]
    n = sum(a['n'] for a in accs)
    s, ss = sum(a['s'] for a in accs), sum(a['ss'] for a in accs)
    rs, rss = sum(a['rs'] for a in accs), sum(a['rss'] for a in accs)
    h = sum(a['h'][0] for a in accs); under = sum(a['h'][1] for a in accs); over = sum(a['h'][2] for a in accs)
    rh = sum(a['rh'][0] for a in accs); runder = sum(a['rh'][1] for a in accs); rover = sum(a['rh'][2] for a in accs)
    mean = s / n
    ps = [0.1, 1, 5, 25, 50, 75, 95, 99, 99.9]
    p = pct(h, under, DIFF_RANGE[0], ps)
    rp = pct(rh, runder, RESID_RANGE[0], [1, 50, 99])
    lines = [
        ('sheets_compared', len(accs)),
        ('pixels_both', n),
        ('pixels_only_before', sum(r['only_before'] for r, _ in results)),
        ('pixels_only_after', sum(r['only_after'] for r, _ in results)),
        ('diff_mean', f'{mean:.5f}'),
        ('diff_std', f'{np.sqrt(ss / n - mean * mean):.5f}'),
        ('diff_min', f'{min(a["min"] for a in accs):.5f}'),
        ('diff_max', f'{max(a["max"] for a in accs):.5f}'),
        *[(f'diff_p{k}', f'{v:.4f}') for k, v in p.items()],
        ('diff_outside_hist', under + over),
        ('resid_mean', f'{rs / n:.5f}'),
        ('resid_rms', f'{np.sqrt(rss / n):.5f}'),
        ('resid_min', f'{min(a["rmin"] for a in accs):.5f}'),
        ('resid_max', f'{max(a["rmax"] for a in accs):.5f}'),
        *[(f'resid_p{k}', f'{v:.4f}') for k, v in rp.items()],
        ('resid_outside_hist', runder + rover),
    ]
    # グラフ用にヒストグラムを残す（bin の幅は BIN、範囲は DIFF_RANGE / RESID_RANGE）
    np.savez(f'{prefix}_hist.npz', diff=h, diff_range=DIFF_RANGE, resid=rh, resid_range=RESID_RANGE, bin=BIN)
    with open(f'{prefix}_summary.tsv', 'w') as f:
        for k, v in lines:
            f.write(f'{k}\t{v}\n')
    for k, v in lines:
        print(f'{k}\t{v}')


if __name__ == '__main__':
    main()
