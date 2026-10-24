"""図郭ごとに、自治体 DEM（source-store/<source>）と地理院 DEM（既定は source-store/jpdem1a）の差を出す。

使い方（作業フォルダで実行）:
  python sheet_diff.py <source> <out.tsv> [processes] [地理院のソース（jpdem1a / jpdem5a など）]

自治体 DEM を 2m に間引いて読み、地理院 DEM をその格子へ bilinear で寄せて「自治体 − 地理院」を取る。
両方に値がある画素だけ数える。地理院がない図郭は n=0 になる。
pct_zero_land は、自治体 DEM が 0.5m 未満で地理院が 2m を超える画素の割合。データのない所を 0 で埋めた図郭を探すのに使う。
"""
from glob import glob
import os
import sys
from multiprocessing import Pool

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

STEP = 4  # 0.5m を 4 画素ごと（2m）に読む
GSI = sys.argv[4] if len(sys.argv) > 4 else 'jpdem1a'
GSI_VRT = f'tmp-store/{GSI}.vrt'


def diff(path):
    name = os.path.basename(path)
    with rasterio.open(path) as src:
        h, w = src.height // STEP, src.width // STEP
        a = src.read(1, out_shape=(h, w), resampling=Resampling.nearest).astype(np.float64)
        transform = src.transform * src.transform.scale(src.width / w, src.height / h)
        crs, nodata = src.crs, src.nodata
    with rasterio.open(GSI_VRT) as g, WarpedVRT(g, crs=crs, transform=transform, width=w, height=h,
                                                 resampling=Resampling.bilinear, src_nodata=-9999, nodata=np.nan) as v:
        b = v.read(1).astype(np.float64)
    ok = (a != nodata) & np.isfinite(b) & (b != -9999)
    if not ok.any():
        return f'{name}\t0\t\t\t\t\t'
    d = a[ok] - b[ok]
    ad = np.abs(d)
    zero_land = (a[ok] < 0.5) & (b[ok] > 2)
    return (f'{name}\t{ok.sum()}\t{np.median(d):+.3f}\t{np.percentile(ad, 90):.3f}\t'
            f'{(ad > 1).mean() * 100:.2f}\t{(ad > 5).mean() * 100:.2f}\t{zero_land.mean() * 100:.2f}')


def main():
    source, out = sys.argv[1], sys.argv[2]
    processes = int(sys.argv[3]) if len(sys.argv) > 3 else None
    files = sorted(glob(f'source-store/{GSI}/*.tif'))
    os.makedirs('tmp-store', exist_ok=True)
    open(f'tmp-store/{GSI}.txt', 'w').write('\n'.join(files) + '\n')
    os.system(f'gdalbuildvrt -q -input_file_list tmp-store/{GSI}.txt {GSI_VRT}')
    paths = sorted(glob(f'source-store/{source}/*.tif'))
    with Pool(processes) as pool:
        rows = pool.map(diff, paths, chunksize=4)
    with open(out, 'w') as f:
        f.write('sheet\tn\tmedian\tabs_p90\tpct_gt1m\tpct_gt5m\tpct_zero_land\n')
        f.write('\n'.join(rows) + '\n')
    print(f'{len(rows)} sheets -> {out}')


if __name__ == '__main__':
    main()
