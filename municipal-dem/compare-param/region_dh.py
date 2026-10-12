"""候補地域の範囲で、水準点（BM）と三角点（TR）の標高補正パラメータ dH を比べる。
2 つの差が大きい地域ほど、どちらのパラメータが合うかを見分けやすい。"""
import sys
import numpy as np

PAR = sys.argv[1]  # .par のあるフォルダ


def load(path):
    d = {}
    for line in open(path, encoding='cp932').readlines()[16:]:
        p = line.split()
        if len(p) >= 2 and len(p[0]) == 8 and p[0].isdigit():
            c = p[0]
            lat = (int(c[0:2]) + int(c[4]) / 8 + int(c[6]) / 80) / 1.5
            lon = 100 + int(c[2:4]) + int(c[5]) / 8 + int(c[7]) / 80
            d[c] = (lon, lat, float(p[1]))
    return d


bm = load(f'{PAR}/hyokorevBM_jgd2024_h.par')
tr = load(f'{PAR}/hyokorevTR_jgd2024_h.par')
common = sorted(set(bm) & set(tr))
lon = np.array([bm[c][0] for c in common]); lat = np.array([bm[c][1] for c in common])
b = np.array([bm[c][2] for c in common]); t = np.array([tr[c][2] for c in common])

REGIONS = [  # 名前, 西, 東, 南, 北（candidates.md の手元 DEM の範囲）
    ('長野', 137.46, 138.74, 35.18, 37.04),
    ('山梨', 138.18, 139.14, 35.17, 35.97),
    ('京都', 134.85, 136.07, 34.70, 35.78),
    ('富山', 136.77, 137.70, 36.27, 36.99),
    ('鳥取', 133.12, 134.53, 35.05, 35.62),
    ('神奈川', 138.94, 139.75, 35.13, 35.68),
    ('埼玉山間部', 138.70, 139.57, 35.75, 36.30),
    ('岡山', 133.26, 134.41, 34.29, 35.35),
    ('広島2022', 132.04, 133.50, 34.02, 34.88),
    ('東京区部', 139.56, 139.92, 35.52, 35.82),
    ('東京多摩', 138.94, 139.60, 35.50, 35.90),
    ('能登', 136.58, 137.39, 36.59, 37.87),
    ('静岡東部', 138.51, 138.90, 35.12, 35.45),
    ('静岡中西部', 137.48, 138.65, 34.59, 35.12),
    ('高知', 132.4, 134.4, 32.7, 33.9),
    ('栃木', 139.3, 140.3, 36.2, 37.2),
]
print('地域\tBM中央\tBM範囲\tTR中央\tTR範囲\tTR-BM中央\t|TR-BM|p90\tメッシュ数')
for name, w, e, s, n in REGIONS:
    m = (lon >= w) & (lon <= e) & (lat >= s) & (lat <= n)
    d = t[m] - b[m]
    print(f'{name}\t{np.median(b[m]):+.3f}\t{b[m].min():+.2f}..{b[m].max():+.2f}\t{np.median(t[m]):+.3f}\t'
          f'{t[m].min():+.2f}..{t[m].max():+.2f}\t{np.median(d):+.3f}\t{np.percentile(np.abs(d), 90):.3f}\t{m.sum()}')
