"""ソースの図郭から、データのある範囲のポリゴン（GeoJSON, EPSG:4326）を作る。

ビューワ（naisui-risk-verification/viewer）が「この地点の DEM」を出すのに使う。
本家の source_polygonize.py は図郭を元の解像度でポリゴン化するが、0.5m の 1,291 枚では重いので、
各図郭を 1/FACTOR に間引いて読み（COG の overview が使われる）、NoData でない格子をポリゴンにする。
縁は間引いた格子の分（0.5m × 32 = 16m）だけ粗くなる。

使い方: python source_coverage.py <source-store/{source} のフォルダ> <出力 .geojson> [FACTOR]
"""
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import shapes
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union
from pyproj import Transformer


def sheet_polygons(path: Path, factor: int):
    with rasterio.open(path) as ds:
        h, w = max(1, ds.height // factor), max(1, ds.width // factor)
        # NoData を含む格子を落とさないよう、最近傍で読んだ値の有効マスクを使う
        mask = ds.read_masks(1, out_shape=(h, w), resampling=Resampling.nearest) > 0
        if not mask.any():
            return [], ds.crs
        t = ds.transform * ds.transform.scale(ds.width / w, ds.height / h)
        geoms = [shape(g) for g, v in shapes(mask.astype(np.uint8), mask=mask, transform=t) if v == 1]
        return geoms, ds.crs


def main():
    folder, out = Path(sys.argv[1]), Path(sys.argv[2])
    factor = int(sys.argv[3]) if len(sys.argv) > 3 else 32
    files = sorted(folder.glob('*.tif'))
    geoms, crs = [], None
    for i, f in enumerate(files):
        g, crs = sheet_polygons(f, factor)
        geoms += g
        if i % 200 == 0:
            print(f'{i} / {len(files)}', flush=True)
    # 隣の図郭との継ぎ目（間引きで出る細い隙間）を閉じてから合わせる
    with rasterio.open(files[0]) as ds:
        cell = abs(ds.transform.a) * factor
    merged = unary_union([g.buffer(cell, join_style=2) for g in geoms]).buffer(-cell, join_style=2)
    merged = merged.simplify(cell / 2)
    to4326 = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True).transform
    merged = transform(to4326, merged)
    fc = {
        'type': 'FeatureCollection',
        'features': [{'type': 'Feature', 'properties': {'source': folder.name}, 'geometry': mapping(merged)}],
    }
    out.write_text(json.dumps(fc, separators=(',', ':')), encoding='utf-8')
    print(f'{len(files)} sheets -> {out} ({out.stat().st_size / 1e3:.0f} kB)')


if __name__ == '__main__':
    main()
