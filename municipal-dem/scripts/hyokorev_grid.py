"""国土地理院の標高補正パラメータ（PatchJGD(標高版) の .par）を、全国の dH グリッド（GeoTIFF, EPSG:6668）にする。

使い方: python hyokorev_grid.py <in.par> <out.tif>

.par の各行は 3 次メッシュコードと dH（m）。PatchJGD と同じく、値はメッシュの南西隅の格子点にあるとみなす。
GeoTIFF の画素の中心を格子点に合わせるので、bilinear で読めば PatchJGD の補間と同じになる。
海などで値のない格子点は、近くの値で埋めて（最大 20 格子点）、海岸の画素でも補正量が出るようにする。
"""
import sys

import numpy as np
import rasterio
from rasterio.fill import fillnodata
from rasterio.transform import from_origin

DLON = 1 / 80  # 45 秒
DLAT = 1 / 120  # 30 秒
LON0, LON1 = 122.0, 154.0
LAT0, LAT1 = 20.0, 46.0


def read_par(path):
    with open(path, encoding='cp932') as f:
        lines = f.readlines()
    for line in lines[16:]:
        parts = line.split()
        if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 8:
            yield parts[0], float(parts[1])


def node(code):
    p, u, q, v, r, w = int(code[0:2]), int(code[2:4]), int(code[4]), int(code[5]), int(code[6]), int(code[7])
    lat = (p + q / 8 + r / 80) / 1.5
    lon = 100 + u + v / 8 + w / 80
    return lon, lat


def main():
    src, out = sys.argv[1], sys.argv[2]
    width = round((LON1 - LON0) / DLON)
    height = round((LAT1 - LAT0) / DLAT)
    grid = np.full((height, width), np.nan, dtype=np.float32)
    n = 0
    for code, dh in read_par(src):
        lon, lat = node(code)
        col = round((lon - LON0) / DLON)
        row = round((LAT1 - lat) / DLAT)
        if 0 <= row < height and 0 <= col < width:
            grid[row, col] = dh
            n += 1
    mask = ~np.isnan(grid)
    filled = fillnodata(np.where(mask, grid, 0).astype(np.float32), mask=mask.astype(np.uint8), max_search_distance=20)
    filled[~mask & (fillnodata(mask.astype(np.float32), mask=mask.astype(np.uint8), max_search_distance=20) == 0)] = np.nan
    transform = from_origin(LON0 - DLON / 2, LAT1 + DLAT / 2, DLON, DLAT)
    with rasterio.open(out, 'w', driver='GTiff', width=width, height=height, count=1, dtype='float32',
                       crs='EPSG:6668', transform=transform, nodata=np.nan, compress='deflate') as dst:
        dst.write(filled, 1)
    print(f'{out}: {n} nodes, {width}x{height}, filled {int(np.sum(~np.isnan(filled)) - n)} nodes near coasts')


if __name__ == '__main__':
    main()
