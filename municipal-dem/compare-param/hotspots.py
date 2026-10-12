"""手元 DEM の範囲で、BM と TR の dH の差が大きく、地理院 1m（DEM1A）がある 3 次メッシュを挙げる。
使い方: python hotspots.py <parフォルダ> <latest_1.csv> > hotspots.tsv"""
import csv, re, sys
import numpy as np

PAR, LIST = sys.argv[1], sys.argv[2]
REGIONS = [  # 手元に 0.5m 以上の結合 DEM があり、地殻変動の大きくない地域
    ('nagano', 137.46, 138.74, 35.18, 37.04),
    ('yamanashi', 138.18, 139.14, 35.17, 35.97),
    ('kyoto', 134.85, 136.07, 34.70, 35.78),
    ('toyama', 136.77, 137.70, 36.27, 36.99),
    ('kanagawa', 138.94, 139.75, 35.13, 35.68),
    ('saitama', 138.70, 139.57, 35.75, 36.30),
    ('okayama', 133.26, 134.41, 34.29, 35.35),
    ('hiroshima2022', 132.04, 133.50, 34.02, 34.88),
    ('tama', 138.94, 139.60, 35.50, 35.90),
    ('shizuoka-east', 138.51, 138.90, 35.12, 35.45),
]


def load(path):
    d = {}
    for line in open(path, encoding='cp932').readlines()[16:]:
        p = line.split()
        if len(p) >= 2 and len(p[0]) == 8 and p[0].isdigit():
            d[p[0]] = float(p[1])
    return d


def node(c):
    return 100 + int(c[2:4]) + int(c[5]) / 8 + int(c[7]) / 80, (int(c[0:2]) + int(c[4]) / 8 + int(c[6]) / 80) / 1.5


bm, tr = load(f'{PAR}/hyokorevBM_jgd2024_h.par'), load(f'{PAR}/hyokorevTR_jgd2024_h.par')
gsi = {}
for r in csv.DictReader(open(LIST)):
    m = re.search(r'FG-GML-(\d{4})-(\d)(\d)-(\d)(\d)-DEM1A', r['url'])
    if m:
        gsi[m.group(1) + m.group(2) + m.group(3) + m.group(4) + m.group(5)] = r['url']
w_ = csv.writer(sys.stdout, delimiter='\t')
w_.writerow(['region', 'mesh', 'lon', 'lat', 'bm', 'tr', 'tr_minus_bm', 'url'])
for name, w, e, s, n in REGIONS:
    rows = []
    for c in set(bm) & set(tr) & set(gsi):
        lon, lat = node(c)
        if w <= lon <= e and s <= lat <= n:
            rows.append((abs(tr[c] - bm[c]), c, lon, lat))
    rows.sort(reverse=True)
    big = [r for r in rows if r[0] >= 0.08]
    print(f'# {name}: 1m あり {len(rows)} メッシュ, |TR-BM|>=0.08 が {len(big)}', file=sys.stderr)
    for _, c, lon, lat in big:
        w_.writerow([name, c, f'{lon:.4f}', f'{lat:.4f}', bm[c], tr[c], f'{tr[c] - bm[c]:+.3f}', gsi[c]])
