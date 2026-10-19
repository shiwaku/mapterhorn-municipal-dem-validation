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

## 自治体 DEM の処理フロー

鳥取県 0.5m DEM（`jptottori`）で回した流れです。本家の pipelines をそのまま使い、自治体 DEM 向けに 2 つの手順（★）を足しています。

```
鳥取県 0.5m DEM（G空間情報センター、ZIP 24 本・33GB、図郭 1,291 枚）
  │
【source】ソースごとに下ごしらえ
  ① 取得・展開        ZIP から図郭の GeoTIFF を取り出す
  ② NoData を付ける    ★本家の source_set_nodata.py で -9999 を付ける
  ③ COG 化            source_to_cog.py
  ④ 標高改定の補正     ★scripts/source_vertical_shift.py（vshift）
  ⑤ 範囲を取る         source_bounds.py
  │   ※ 地理院 1m・5m・10m と GLO-30 も、同じく source を作る
  │
【aggregation】z6 区画の中で、解像度の高いソースを優先して重ね、最大ズームのタイルを作る
【downsampling】下のズームのタイルを作る
【bundle】z6 区画ごとに PMTiles にまとめる（6-55-25.pmtiles）
```

| 足した手順 | 中身 | 理由 |
|---|---|---|
| ② NoData を付ける | NoData 値のない図郭に -9999 を付ける。値は変えない | 1,291 枚のうち 51 枚に NoData 値がない。1 枚でも混ざると `gdalbuildvrt` が図郭の外を 0 として扱い、地理院データの上に 0m の穴ができる（[#3](https://github.com/shiwaku/mapterhorn-municipal-dem-validation/issues/3)） |
| ④ 標高改定の補正 | 地理院の水準点補正量のグリッド（`grids/hyokorevBM_jgd2024.tif`）を bilinear で寄せて標高に足す。処理済みの図郭には `<file>.vshift` を置き、二度足さない | 鳥取県 DEM は 2025-04-01 の標高改定より前（測地成果2011）の値で、改定後の地理院 DEM とそろえないと境目に段差ができる（[#2](https://github.com/shiwaku/mapterhorn-municipal-dem-validation/issues/2)） |

- 本家に入れるときは、`source-catalog/jptottori/` の Justfile に ①〜⑤ と polygonize・tarball 作成を並べる形を考えています（手元の本家クローンに置いているだけで、本家にもフォークにも出していません）。
- 補正量のグリッドは `scripts/hyokorev_grid.py` で、地理院の PatchJGD（標高版）のパラメータ（.par）から作ります。海の格子点は近くの値で埋めます。

### 手元での回し方（`municipal-dem/tottori/`）

| ファイル | 役割 |
|---|---|
| `run.sh <段階>` | 段階（source / bounds / vshift / aggregation / downsampling / bundle）を 1 つずつ、Docker の `mapterhorn-pipelines:local` で回す。本家のクローンは読み取り専用でマウントする。環境変数 `WORK`（作業フォルダ）・`SOURCES`（source で処理するソース）・`CPUS`（CPU 数とプロセス数）で切り替える |
| `run-full.sh [最初の段階]` | 県全体を source〜bundle まで通し、段階ごとの時間と容量を `work-full/stages.tsv` に残す。PC の負荷を抑えるため、既定は `CPUS=4` |
| `limit/sitecustomize.py` | pipelines は `Pool()` を引数なしで呼ぶので、プロセス数を `MAPTERHORN_CPUS` に抑える |
| `extract_tiles.py` | 図郭一覧（`/vsizip/` パス）の図郭を ZIP から取り出す |
| `gsi_list.py`・`gsi_fetch.sh` | 県全体に掛かる地理院 1m・5m・10m の一覧（`gsi-lists/download-*.txt`）を作り、Source Cooperative の `smartmaps/japan-geotiff-dem` から取得する |
| `compare.py` | 2 つの PMTiles を比べる。`stats` は標高差、`count` はタイルの有無、`render` は陰影図 |
| `sheet_diff.py` | 図郭ごとに、自治体 DEM と地理院 DEM の差を出す |

- `run.sh` は downsampling の前に、aggregation が `tmp-store/source` に残したリンクを消します。残っていると downloader が Docker Desktop の共有フォルダ越しに数え続け、downsampling が進みません。

## 動かすときに別途用意するもの

- 本家のクローン: `mapterhorn/`（このリポジトリの直下に `git clone https://github.com/mapterhorn/mapterhorn`）。`tottori/run.sh` は `../../mapterhorn/pipelines` を読み取り専用でマウントします。
- 標高補正パラメータ: 国土地理院の `hyokorevBM_jgd2024_h.par`（水準点）・`hyokorevTR_jgd2024_h.par`（三角点）。地理院のサイトから取得し、`scripts/hyokorev_grid.py` で `grids/hyokorevBM_jgd2024.tif` を作ります。
- 地理院 DEM の一覧: Source Cooperative の `smartmaps/japan-geotiff-dem` にある `latest_file_list.csv.gz`（1/・5/・10/）を展開して `tottori/gsi-lists/latest_{1,5,10}.csv` に置きます。
- 自治体 DEM 本体: 各県の公開元から取得します（`candidates.md` を参照）。データ本体はこのリポジトリに含めていません。

## わかったこと（2026-10 時点）

- 鳥取（6-55-25）で、本家の pipelines をそのまま使って source〜bundle が通った。地理院のデータしかない区画は本家の公開版と一致した。
- 2025-03 以前の自治体 DEM は改定前（測地成果2011）の標高で、改定後の地理院 DEM と地域ごとに数十 cm ずれる。判定できた 15 本（鳥取を含む）はすべて改定前で、水準点の補正パラメータの dH を足すとほぼ 0 になった。
- 鳥取県全体（図郭 1,291 枚）でも source〜bundle が通った。CPUS=4 で aggregation 3時間17分・downsampling 42分・bundle 4分、作業フォルダは最大 93GB、`6-55-25.pmtiles` は 17.45GB。
- 自治体 DEM には NoData 値のない図郭が混ざることがあり、そのままだと 0m の穴ができる。COG 化の前に NoData を付ければ消える。

経過の詳細は issue の [#1（取り込みの仕組み）](https://github.com/shiwaku/mapterhorn-municipal-dem-validation/issues/1)、[#2（標高改定の補正）](https://github.com/shiwaku/mapterhorn-municipal-dem-validation/issues/2)、[#3（鳥取県全体の通し実行）](https://github.com/shiwaku/mapterhorn-municipal-dem-validation/issues/3) にあります。

## ライセンス

コードは [MIT](LICENSE)。データ（自治体 DEM・地理院 DEM、`japan/viz/ne/` の Natural Earth）はそれぞれの提供元の条件に従います。
