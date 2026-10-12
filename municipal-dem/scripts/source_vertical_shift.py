"""source-store/<source>/*.tif の標高に、dH グリッドの値を足す（例: 測地成果2011 → 2024 の標高改定）。

使い方（pipelines と同じく作業フォルダで実行）:
  python source_vertical_shift.py <source> <dh_grid.tif>

source_to_cog.py の後、source_bounds.py の前に置く。dH は各ファイルの格子へ bilinear で寄せる。
出力は source_to_cog.py と同じ作成オプションの COG。処理済みのファイルには <file>.vshift を置き、二度足さない。
"""
from glob import glob
import os
import sys
from multiprocessing import Pool

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

import utils

GRID = None


def shift(filepath):
    if os.path.isfile(f'{filepath}.vshift'):
        return
    tmp = f'{filepath}.vshift.tif'
    with rasterio.open(filepath) as src:
        profile = src.profile
        data = src.read(1)
        nodata = src.nodata
        dh = np.full(data.shape, np.nan, dtype=np.float32)
        with rasterio.open(GRID) as g:
            reproject(rasterio.band(g, 1), dh, src_transform=g.transform, src_crs=g.crs, src_nodata=np.nan,
                      dst_transform=src.transform, dst_crs=src.crs, dst_nodata=np.nan,
                      resampling=Resampling.bilinear)
    valid = data != nodata if nodata is not None else np.ones(data.shape, bool)
    if np.isnan(dh[valid]).any():
        raise RuntimeError(f'{filepath}: dH grid has no value for some pixels')
    out = data.astype(np.float32)
    out[valid] += dh[valid]
    profile.update(driver='GTiff', dtype='float32', compress='deflate', tiled=True, blockxsize=512, blockysize=512, BIGTIFF='YES')
    with rasterio.open(tmp, 'w', **profile) as dst:
        dst.write(out, 1)
    utils.run_command(f'GDAL_CACHEMAX=512 gdal_translate -q -of COG -co BLOCKSIZE=512 -co OVERVIEWS=NONE -co SPARSE_OK=YES -co BIGTIFF=YES -co COMPRESS=LERC -co MAX_Z_ERROR=0.001 "{tmp}" "{filepath}"', silent=True)
    os.remove(tmp)
    open(f'{filepath}.vshift', 'w').write(f'{GRID} mean={float(np.mean(dh[valid])):.4f}\n')


def init(grid):
    global GRID
    GRID = grid


def main():
    if len(sys.argv) < 3:
        print('usage: python source_vertical_shift.py {source} {dh_grid.tif}')
        exit()
    source, grid = sys.argv[1], sys.argv[2]
    filepaths = sorted(glob(f'source-store/{source}/*.tif'))
    print(f'vertical shift for source={source}, {len(filepaths)} files, grid={grid}')
    with Pool(initializer=init, initargs=(grid,)) as pool:
        pool.map(shift, filepaths, chunksize=1)


if __name__ == '__main__':
    main()
