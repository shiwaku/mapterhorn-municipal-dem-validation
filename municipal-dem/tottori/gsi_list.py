"""地理院 DEM の一覧（gsi-lists/latest_{1,5,10}.csv）から、範囲に掛かるファイルを「ソース名 URL」で書き出す。

使い方:
  python gsi_list.py <minlon> <minlat> <maxlon> <maxlat> > gsi-lists/download-full.txt

ファイル名のメッシュコード（1 次・2 次・3 次）から範囲を出して判定する。
ソース名は本家にそろえる（DEM1A → jpdem1a、DEM5A → jpdem5a、DEM5B → jpdem5b、dem10b → jpdem10b）。
"""
import csv
import re
import sys


def mesh_bounds(m1, m2, m3):
    lat, lon = int(m1[:2]) / 1.5, int(m1[2:]) + 100
    h, w = 40 / 60, 1.0
    if m2:
        lat += int(m2[0]) * 5 / 60
        lon += int(m2[1]) * 7.5 / 60
        h, w = 5 / 60, 7.5 / 60
    if m3:
        lat += int(m3[0]) * 0.5 / 60
        lon += int(m3[1]) * 0.75 / 60
        h, w = 0.5 / 60, 0.75 / 60
    return lon, lat, lon + w, lat + h


def main():
    minlon, minlat, maxlon, maxlat = map(float, sys.argv[1:5])
    for res in ('1', '5', '10'):
        for row in csv.DictReader(open(f'gsi-lists/latest_{res}.csv')):
            name = row['url'].rsplit('/', 1)[1]
            m = re.match(r'FG-GML-(\d{4})-(\d\d)(?:-(\d\d))?-(dem\w+?)-', name, re.I)
            x0, y0, x1, y1 = mesh_bounds(*m.groups()[:3])
            if x1 > minlon and x0 < maxlon and y1 > minlat and y0 < maxlat:
                print(f'jp{m.group(4).lower()} {row["url"]}')


if __name__ == '__main__':
    main()
