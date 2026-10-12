# mapterhorn-municipal-dem-validation

自治体が公開している高解像度 DEM（0.5m・0.25m など）を、[Mapterhorn](https://github.com/mapterhorn/mapterhorn) の作法（source → aggregation → downsampling → bundle）で取り込めるかを手元で検証するためのリポジトリです。本家への提案ではなく、その前の検証の記録です。

## 中身

| 場所 | 内容 |
|---|---|
| `mapterhorn-japan-dem-notes.md` | Mapterhorn に日本の標高データ（国土地理院 DEM）が取り込まれた経緯と、パイプラインの仕組みの調査メモ |
| `municipal-dem/candidates.md` | 取り込み候補の自治体 DEM（公開データと手元の結合 DEM）の一覧 |
| `municipal-dem/ckan/` | G空間情報センター（CKAN API）で候補を探したスクリプトと結果 |
| `municipal-dem/local-scan/` | 手元の DEM を探してヘッダーを読んだスクリプト（結果のファイル一覧は含めていない） |
| `municipal-dem/docker/` | Mapterhorn の pipelines を動かすための Docker イメージ |
| `municipal-dem/tottori/` | 鳥取県 0.5m DEM（z6 タイル 6-55-25）で source〜bundle を通した手順と比較スクリプト |
| `municipal-dem/scripts/` | 標高成果の改定（測地成果2024）にそろえる補正（`hyokorev_grid.py`、`source_vertical_shift.py`） |
| `municipal-dem/compare-param/` | 自治体 DEM と地理院 1m を 3 次メッシュごとに比べ、改定前か後か、水準点と三角点のどちらの補正パラメータが合うかを調べたスクリプトと結果 |
| `japan/` | 本家の日本域 z13+ バンドルを落とすスクリプトと、z6 区画の地図（`viz/`） |

## 動かすときに別途用意するもの

- 本家のクローン: `mapterhorn/`（このリポジトリの直下に `git clone https://github.com/mapterhorn/mapterhorn`）。`tottori/run.sh` は `../../mapterhorn/pipelines` を読み取り専用でマウントします。
- 標高補正パラメータ: 国土地理院の `hyokorevBM_jgd2024_h.par`（水準点）・`hyokorevTR_jgd2024_h.par`（三角点）。地理院のサイトから取得し、`scripts/hyokorev_grid.py` で `grids/hyokorevBM_jgd2024.tif` を作ります。
- 地理院 DEM の一覧: Source Cooperative の `smartmaps/japan-geotiff-dem` にある `latest_file_list.csv.gz`（1/・5/・10/）を展開して `tottori/gsi-lists/latest_{1,5,10}.csv` に置きます。
- 自治体 DEM 本体: 各県の公開元から取得します（`candidates.md` を参照）。データ本体はこのリポジトリに含めていません。

## わかったこと（2026-10 時点）

- 鳥取（6-55-25）で、本家の pipelines をそのまま使って source〜bundle が通った。地理院のデータしかない区画は本家の公開版と一致した。
- 2025-03 以前の自治体 DEM は改定前（測地成果2011）の標高で、改定後の地理院 DEM と地域ごとに数十 cm ずれる。判定できた 15 本（鳥取を含む）はすべて改定前で、水準点の補正パラメータの dH を足すとほぼ 0 になった。

経過の詳細は issue の [#1（取り込みの仕組み）](https://github.com/shiwaku/mapterhorn-municipal-dem-validation/issues/1) と [#2（標高改定の補正）](https://github.com/shiwaku/mapterhorn-municipal-dem-validation/issues/2) にあります。

## ライセンス

コードは [MIT](LICENSE)。データ（自治体 DEM・地理院 DEM、`japan/viz/ne/` の Natural Earth）はそれぞれの提供元の条件に従います。
