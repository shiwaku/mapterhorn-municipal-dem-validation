"""データのない所を NoData でなく 0 で埋めた図郭で、0 の画素を NoData にする。

使い方（pipelines と同じく作業フォルダで実行）:
  python source_zero_to_nodata.py <source> <nodata> <図郭名> ...

source_set_nodata.py の前に置く。0 埋めの図郭は NoData 値を持たないので、ここで 0 を <nodata> にして NoData 値も付ける。
補正（source_vertical_shift.py）の後では 0 が dH だけずれて見分けにくいので、必ず元の値のうちに行う。
陸地のちょうど 0.000m も消えるので、0 埋めと確かめた図郭だけを名前で渡す。
"""
import os
import sys

import numpy as np
import rasterio


def fix(filepath, nodata):
    tmp = f'{filepath}.zero.tif'
    with rasterio.open(filepath) as src:
        profile = src.profile
        data = src.read(1)
    if profile['nodata'] is not None and profile['nodata'] != nodata:
        raise RuntimeError(f'{filepath}: nodata is already {profile["nodata"]}')
    zero = data == 0
    data[zero] = nodata
    profile.update(nodata=nodata)
    with rasterio.open(tmp, 'w', **profile) as dst:
        dst.write(data, 1)
    os.replace(tmp, filepath)
    print(f'{os.path.basename(filepath)}: {zero.mean() * 100:.1f}% -> nodata')


def main():
    if len(sys.argv) < 4:
        print('usage: python source_zero_to_nodata.py {source} {nodata} {name} ...')
        exit()
    source, nodata = sys.argv[1], float(sys.argv[2])
    for name in sys.argv[3:]:
        fix(f'source-store/{source}/{name}.tif', nodata)


if __name__ == '__main__':
    main()
