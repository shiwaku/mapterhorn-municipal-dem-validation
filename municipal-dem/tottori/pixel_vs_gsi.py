"""鳥取 DEM（補正前・補正後）と地理院 DEM を画素ごとに比べ、差（鳥取 − 地理院）の基礎統計を出す。

使い方（work-full で実行）:
  python ../pixel_vs_gsi.py <補正前の一覧.txt> <出力の接頭辞> [processes] [地理院のソース（jpdem1a / jpdem5a）]

- 比べる格子は、鳥取の図郭を 1m にしたもの。鳥取 0.5m は 2×2 画素を平均する（4 画素とも値がある所だけ）。
  地理院 DEM（EPSG:6668 の緯度経度格子）はこの格子へ bilinear で寄せる
- 補正前は ZIP の元の図郭。NoData 値のない図郭があるので -9999 も NoData とみなし、
  0 で埋めた 2 枚（ZERO_FILLED）は 0 も NoData とみなす（補正後と同じ範囲になる）
- 補正前・補正後・地理院の 3 つすべてに値がある画素だけを数える。前後で同じ画素を比べるため
- 平地（補正後の DEM の勾配が FLAT 未満）だけの統計も出す。斜面では水平のずれが鉛直の差に見えるため
- 百分位は 1mm 刻みのヒストグラム（±HIST_MAX m）から。範囲の外の画素数も出す
- 出力: <接頭辞>_sheets.tsv（図郭ごと）、<接頭辞>_summary.tsv（全体）、<接頭辞>_hist.npz（グラフ用）
"""
import os
import sys
from multiprocessing import Pool

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

NODATA = -9999
ZERO_FILLED = {'dem_05lb753.tif', 'dem_05lb964.tif'}
FLAT = 0.05
BIN = 0.001
HIST_MAX = 5.0
GSI = 'jpdem1a'


def to_1m(a, valid):
    """0.5m → 1m。2×2 の平均で、4 画素とも値がある所だけ残す。"""
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    a, valid = a[:h, :w], valid[:h, :w]
    s = np.where(valid, a, 0).astype(np.float64).reshape(h // 2, 2, w // 2, 2).sum(axis=(1, 3))
    n = valid.reshape(h // 2, 2, w // 2, 2).sum(axis=(1, 3))
    return s / 4, n == 4


def stats(d):
    h, _ = np.histogram(d, bins=int(2 * HIST_MAX / BIN), range=(-HIST_MAX, HIST_MAX))
    return {'n': d.size, 's': d.sum(), 'ss': (d * d).sum(), 'min': d.min(), 'max': d.max(),
            'h': h.astype(np.int64), 'out': int((np.abs(d) >= HIST_MAX).sum())}


def compare(before_path):
    name = os.path.basename(before_path)
    with rasterio.open(before_path) as b:
        a0 = b.read(1)
        nd0 = b.nodata
    with rasterio.open(f'source-store/jptottori/{name}') as s:
        a1 = s.read(1)
        nd1 = s.nodata
        t, crs = s.transform, s.crs
    v0 = (a0 != NODATA) & np.isfinite(a0)
    if nd0 is not None:
        v0 &= a0 != nd0
    if name in ZERO_FILLED:
        v0 &= a0 != 0
    v1 = (a1 != nd1) & np.isfinite(a1)
    b0, m0 = to_1m(a0, v0)
    b1, m1 = to_1m(a1, v1)
    t1 = t * t.scale(2, 2)
    with rasterio.open(f'tmp-store/{GSI}.vrt') as g, WarpedVRT(g, crs=crs, transform=t1, width=b1.shape[1], height=b1.shape[0],
                                                               resampling=Resampling.bilinear, src_nodata=NODATA, nodata=np.nan) as v:
        gsi = v.read(1).astype(np.float64)
    ok = m0 & m1 & np.isfinite(gsi) & (gsi != NODATA)
    row = {'sheet': name, 'n': int(ok.sum())}
    if ok.sum() < 100:
        return row, None
    gy, gx = np.gradient(np.where(m1, b1, np.nan), 1.0)
    flat = ok & (np.hypot(gx, gy) < FLAT)
    d0, d1 = b0[ok] - gsi[ok], b1[ok] - gsi[ok]
    f0, f1 = b0[flat] - gsi[flat], b1[flat] - gsi[flat]
    row.update(n_flat=int(flat.sum()), before_median=float(np.median(d0)), after_median=float(np.median(d1)),
               before_mean=d0.mean(), after_mean=d1.mean(), after_rms=float(np.sqrt((d1 * d1).mean())))
    acc = {'before': stats(d0), 'after': stats(d1)}
    if f0.size:
        acc.update(before_flat=stats(f0), after_flat=stats(f1))
    return row, acc


def merge(accs, key):
    xs = [a[key] for a in accs if key in a]
    n = sum(x['n'] for x in xs)
    s, ss = sum(x['s'] for x in xs), sum(x['ss'] for x in xs)
    h = sum(x['h'] for x in xs)
    mean = s / n
    c = h.cumsum()
    lo_out = sum(x['out'] for x in xs)  # 範囲の外（上下合計）。百分位は範囲内の分布で近似する

    def pct(p):
        i = int(np.searchsorted(c, p / 100 * c[-1]))
        return -HIST_MAX + (i + 0.5) * BIN

    p = {k: pct(k) for k in (1, 5, 25, 50, 75, 95, 99)}
    return {
        'n': n, 'mean': mean, 'std': np.sqrt(ss / n - mean * mean), 'rms': np.sqrt(ss / n),
        'min': min(x['min'] for x in xs), 'max': max(x['max'] for x in xs),
        **{f'p{k}': v for k, v in p.items()},
        'outside': lo_out, 'hist': h,
    }


def frac_abs_gt(h, thr):
    centers = -HIST_MAX + (np.arange(h.size) + 0.5) * BIN
    return h[np.abs(centers) > thr].sum() / h.sum()


def nmad(h, med):
    centers = -HIST_MAX + (np.arange(h.size) + 0.5) * BIN
    dev = np.abs(centers - med)
    order = np.argsort(dev)
    c = h[order].cumsum()
    return 1.4826 * dev[order][int(np.searchsorted(c, c[-1] / 2))]


def main():
    global GSI
    lst, prefix = sys.argv[1:3]
    procs = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    if len(sys.argv) > 4:
        GSI = sys.argv[4]
    paths = [l.strip() for l in open(lst) if l.strip()]
    with Pool(procs) as pool:
        results = pool.map(compare, paths, chunksize=2)
    cols = ['sheet', 'n', 'n_flat', 'before_median', 'after_median', 'before_mean', 'after_mean', 'after_rms']
    with open(f'{prefix}_sheets.tsv', 'w') as f:
        f.write('\t'.join(cols) + '\n')
        for row, _ in results:
            f.write('\t'.join(f'{row[c]:.4f}' if isinstance(row.get(c), float) else str(row.get(c, '')) for c in cols) + '\n')
    accs = [a for _, a in results if a]
    keys = ['before', 'after', 'before_flat', 'after_flat']
    m = {k: merge(accs, k) for k in keys}
    # グラフ用にヒストグラムを残す（1mm 刻み、±HIST_MAX m）
    np.savez(f'{prefix}_hist.npz', **{k: m[k]['hist'] for k in keys}, hist_max=HIST_MAX, bin=BIN)
    rows = ['n', 'mean', 'median', 'std', 'rms', 'nmad', 'p1', 'p5', 'p25', 'p75', 'p95', 'p99', 'min', 'max', 'abs_gt_0.1m', 'abs_gt_0.5m', 'outside_5m']
    with open(f'{prefix}_summary.tsv', 'w') as f:
        f.write('stat\t' + '\t'.join(keys) + '\n')
        for r in rows:
            vals = []
            for k in keys:
                x = m[k]
                if r == 'n':
                    v = f"{x['n']}"
                elif r == 'median':
                    v = f"{x['p50']:+.4f}"
                elif r == 'nmad':
                    v = f"{nmad(x['hist'], x['p50']):.4f}"
                elif r == 'abs_gt_0.1m':
                    v = f"{frac_abs_gt(x['hist'], 0.1) * 100:.2f}%"
                elif r == 'abs_gt_0.5m':
                    v = f"{frac_abs_gt(x['hist'], 0.5) * 100:.2f}%"
                elif r == 'outside_5m':
                    v = f"{x['outside']}"
                elif r in ('std', 'rms'):
                    v = f"{x[r]:.4f}"
                else:
                    v = f"{x[r]:+.4f}"
                vals.append(v)
            f.write(r + '\t' + '\t'.join(vals) + '\n')
    print(open(f'{prefix}_summary.tsv').read())
    print(f'sheets with data: {len(accs)}')


if __name__ == '__main__':
    main()
