"""Mapterhorn の z6 区割り（日本域）の地図ページ z6map.html を作る。
  python -I make_z6map.py
入力: ne/（Natural Earth 1:50m の陸地・陸の国境）、z6map.tpl.html、
      ../files.txt・../download_urls.json・../*.ok（download.sh が作る。進み具合はファイルサイズから読む）
公開先: https://claude.ai/artifact/1Yx8NQGVrgqWdVhPqTNf8D（Claude に「z6 区割りを更新」と頼むと作り直して上げ直す）
shapely 2 が要る。
"""
import json, math, os, datetime
from shapely.geometry import shape, box
from shapely import clip_by_rect

S = os.path.dirname(os.path.abspath(__file__))
D = os.path.dirname(S)
PX = 96  # 1 タイルの px
X0, X1, Y0, Y1 = 52.55, 60.05, 21.45, 29.05  # 表示範囲（z6 タイル座標）
W, H = round((X1 - X0) * PX), round((Y1 - Y0) * PX)


def merc(lon, lat):
    x = (lon + 180) / 360 * 64
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 64
    return x, y


def px(lon, lat):
    x, y = merc(lon, lat)
    return round((x - X0) * PX, 1), round((y - Y0) * PX, 1)


def lonlat(tx, ty):
    lon = tx / 64 * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / 64))))
    return lon, lat


lo0, la1 = lonlat(X0, Y0)
lo1, la0 = lonlat(X1, Y1)
view = (lo0 - 1, la0 - 1, lo1 + 1, la1 + 1)


def path_of(geom):
    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.geom_type == "Polygon":
            for ring in [g.exterior, *g.interiors]:
                pts = [px(*c) for c in ring.coords]
                out.append("M" + "L".join(f"{a:g} {b:g}" for a, b in pts) + "Z")
        elif g.geom_type == "LineString":
            pts = [px(*c) for c in g.coords]
            out.append("M" + "L".join(f"{a:g} {b:g}" for a, b in pts))
    return "".join(out)


def load(fn, tol):
    parts = []
    for f in json.load(open(os.path.join(S, "ne", fn), encoding="utf-8"))["features"]:
        g = shape(f["geometry"])
        if not g.intersects(box(*view)):
            continue
        g = clip_by_rect(g, *view).simplify(tol)
        if not g.is_empty:
            parts.append(path_of(g))
    return "".join(parts)


land = load("land.geojson", 0.02)
borders = load("countries.geojson", 0.02)

ok = {n[:-3] for n in os.listdir(D) if n.endswith(".ok")}
mirrored = {"6-54-25", "6-54-26", "6-54-27", "6-55-26"}  # 2026-10-11 時点で R2 にあったもの
du = json.load(open(os.path.join(D, "download_urls.json"), encoding="utf-8"))
names = [l.split()[0] for l in open(os.path.join(D, "files.txt")) if l.startswith("6-")]
tiles = []
for it in du["items"]:
    if it["name"] not in names:
        continue
    n = it["name"][:-8]
    _, x, y = map(int, n.split("-"))
    p = os.path.join(D, it["name"])
    got = os.path.getsize(p) if os.path.exists(p) else 0
    state = "done" if it["name"] in ok else ("partial" if got else "todo")
    tiles.append({
        "name": n, "x": x, "y": y, "size": it["size"], "got": got if state != "done" else it["size"],
        "state": state, "mirror": n in mirrored,
        "bbox": [round(it[k], 2) for k in ("min_lon", "min_lat", "max_lon", "max_lat")],
        "px": [round((x - X0) * PX, 1), round((y - Y0) * PX, 1)],
    })
tiles.sort(key=lambda t: -t["size"])

bb = [122.9, 20.4, 154.0, 45.6]
a, b = px(bb[0], bb[3]), px(bb[2], bb[1])
grid = {"x": list(range(53, 60)), "y": list(range(22, 29))}

data = {
    "W": W, "H": H, "PX": PX, "X0": X0, "Y0": Y0, "land": land, "borders": borders, "tiles": tiles,
    "bbox": [a[0], a[1], b[0] - a[0], b[1] - a[1]],
    "gridX": [round((gx - X0) * PX, 1) for gx in range(53, 61)],
    "gridY": [round((gy - Y0) * PX, 1) for gy in range(22, 30)],
    "lonTicks": [[lo, px(lo, 30)[0]] for lo in range(115, 165, 5) if 0 < px(lo, 30)[0] < W],
    "latTicks": [[la, px(140, la)[1]] for la in range(15, 50, 5) if 0 < px(140, la)[1] < H],
    "asof": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "version": du.get("version"),
}
tpl = open(os.path.join(S, "z6map.tpl.html"), encoding="utf-8").read()
open(os.path.join(S, "z6map.html"), "w", encoding="utf-8").write(tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False)))
print("ok", len(tiles), "tiles", round(len(land) / 1024), "KB land", round(len(borders) / 1024), "KB borders")
