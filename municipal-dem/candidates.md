# 自治体 DEM 取り込み検証: 候補データの整理

- 作成: 2026-10-12
- 目的: 自治体 DEM（公開データと手元の自作 DEM）を Mapterhorn の作法（source → aggregation → downsampling → bundle）で取り込めるか検証する。そのための候補を洗い出す
- 背景・仕組み: `../mapterhorn-japan-dem-notes.md`（重ね順は 4 節、日本での具体像は 4.7 節 6、配信と描画は 4.9 節）
- 調べ方: G空間情報センター CKAN API（`ckan/ckan.py` は検索、`ckan/ckan2.py` は詳細取得）。結果は `ckan/ckan_rows.tsv`（約 150 件）と `ckan/ckan_detail.txt` に残した

---

## 1. 取り込みで効く前提

- **重ね順は maxzoom で決まる**: 0.5m なら z17 になり、jpdem1a（1m・z16）より自動で優先される。1m の自治体データは jpdem1a と同じ順位になり、ソース名の辞書順で順位が決まる
- **1m は地理院 1m と重なる**: 詳しくは 2 節冒頭
- **座標系**: 自治体データは JGD2011 平面直角座標系（EPSG:6669〜6687）が多い。GeoTIFF に CRS が付いていれば `source_to_cog.py` に直接渡せる
- **テキスト形式**（XYZ・CSV グリッド）は GeoTIFF への変換を一段挟む（gdal_translate / gdal_grid、または自作の変換）
- **鉛直基準**: いずれも T.P. 標高。GSI とは測量時期が違うので、改変地では境界に段差が出うる
- **標高成果の改定（2025-04-01、測地成果2024）**: 地理院の DEM1A・5A・5B は 2025-07-31 に改定後の標高へ差し替え済み。2025-03 以前に公開された自治体 DEM は改定前（測地成果2011）の標高なので、地域ごとに数十 cm ずれる。鳥取（鳥取市付近）で確かめたところ、鳥取 0.5m − 地理院 1m は +0.22m で、地理院の水準点標高補正パラメータ（hyokorevBM_jgd2024_h.par）の dH を足すと残差は中央値 −0.001m・RMS 0.022m になった（`tottori\datum\`）。取り込むときは、図郭ごとにこの dH を足す補正が要る
- **ライセンス**: 上流に出すなら CC BY 4.0 相当以下であること（issue #142 の wipfli さんの条件）。PDL1.0 は CC BY 4.0 互換

---

## 2. 公開データ（G空間情報センター、2026-10-12 時点）

解像度は CKAN の説明文・リソース説明に書かれた値。林野庁の加工データは、配布されている GeoTIFF のヘッダーを `gdalinfo /vsicurl/` で読んで確かめた（`ckan/rinya_spec.txt` に諸元 PDF の抜粋がある）。

### 1m のデータの扱い

地理院の 1m DEM（jpdem1a）がすでに国土の約 49% を z16 で覆っている。そのため 1m の自治体データを入れても、ズームは z16 のままで解像度は上がらない。一覧からは外さず、使い道を次の 2 つに限って残す。

- 地理院の 1m がない範囲を埋める（地理院の 5m・10m しかない所）
- 地理院より新しい測量で置き換える（造成地・災害後など）

なお、重ね順は jpdem1a と同じ maxzoom（z16）の中でソース名の辞書順に決まる。自治体データを優先したいときは、名前の付け方で順位を調整する必要がある。以下の表で解像度が 1m の行には「地理院 1m と重複」と書いた。

### A. GeoTIFF の DEM（変換なしで source にできる）

| 県 | CKAN id | 解像度 | 座標系 | 計測 | 容量 | ライセンス | 備考 |
|---|---|---|---|---|---|---|---|
| 高知 | dem05_kochi | 0.5m | 平面直角 | 2018（林野庁） | 89 GB | CC BY | Terrain-RGB タイル（z2–18）もある |
| 栃木 | dem05_tochigi | 0.5m | 平面直角 | 2021–22 | 49 GB | CC BY | Terrain-RGB タイル（z2–18）もある |
| 愛媛 | dem05_ehime | 0.5m | 平面直角 | 2018（林野庁） | 未確認 | CC BY | 市町村ごとの ZIP |
| 鳥取 | dem05_tottori | 0.5m | 平面直角 | 2018–2024 | 未確認 | PDL1.0 | ZIP。日南町の 4 図郭に不備あり（差し替え予定） |
| 長野 | nagano-dem | 0.5m | 平面直角 | 2013–14 | 未確認（大容量と注記あり） | CC BY | 地域ごとの ZIP |
| 東京 | tokyopc-23ku-2024 / tokyopc-tama-2023 / tokyopc-shima-2023 | 0.25m・0.5m | 9 系 | 2023–24 | 大 | CC BY | 点群データセットに含まれるグリッド DEM。区部は 0.25m と 0.5m の両方。多摩・島しょは 0.5m が仕様で、0.25m は参考扱い。島しょの沿岸は測深込み |
| 山梨 | yamanashi-pointcloud-2024 | 0.5m | 8 系 | 2024 | 大 | CC BY 4.0 と ODbL の二重 | 点群データセットに含まれる。グラウンド由来の DEM（GeoTIFF・txt）と DSM の両方がある |

### B. ライセンスの確認が要る（GeoTIFF）

| 県 | CKAN id | 解像度 | 容量 | 論点 |
|---|---|---|---|---|
| 富山 | dem | 0.5m | 18 GB | CC BY の表示だが、利用規約 PDF と申請様式（9〜12 号）が付いている |
| 京都 | dem05_kyoto | 0.5m | 10 GB | 独自利用規約（計測は 2019–2023） |

### C. 変換が要る（テキスト・CSV・LAS）

| 県 | CKAN id | 解像度 | 形式 | ライセンス | 備考 |
|---|---|---|---|---|---|
| 兵庫 | 2010-2018-hyogo-geo-dem | 1m（地理院 1m と重複） | XYZ テキスト・V 系 | CC BY 4.0 の表示（CKAN 上は独自規約） | 全県 1m |
| 兵庫 | 2022-hyougo-geo-dem | 0.5m | XYZ テキスト・V 系 | 同上 | 全県（2021–22）。Terrain-RGB 版もある（dem05_hyogo、0.5m） |
| 静岡 | shizuoka-2019 / 2020 / 2021 / 2022 / 2025-pointcloud、shizuoka-2025-pointcloud-alb、virtual-shizuoka-mw | 0.5m | テキスト・8 系 | CC BY 4.0 と ODbL の二重 | 6 データセットそれぞれにグラウンド由来の 0.5m グリッドがある。ALB（測深）のグリッドも 0.5m |
| 神奈川 | kanagawa-2019 / 2020-1 / 2020-2 / 2021 / 2022 / 2024-pointcloud | 0.5m（2022 は 1m もあり、地理院 1m と重複） | CSV・メッシュ | CC BY | 2019–2024 |
| 島根 | shimane-kasen-dem | 1m（地理院 1m と重複） | LAS | PDL1.0 | 河川の両岸 20m 幅だけ |

### D. 林野庁の加工データ（PDL1.0、GeoTIFF）

| 範囲 | CKAN id | 解像度 | 座標系 | 計測 |
|---|---|---|---|---|
| 長野・伊那谷 | inatani_067 | 0.5m（実測） | 6676 | 2013 |
| 三重・北伊勢 | kitaise_081 | 0.5m（実測） | 6674 | 2013–2023 |
| 愛知・尾張西三河 | owarinishimikawa_078 | 0.5m（実測） | 6675 | 2018–2021 |
| 愛知・東三河 | higashimikawa_079 | 0.5m（推定：同シリーズ。ヘッダーはサーバーエラーで読めず） | — | 2018–2021 |
| 徳島・吉野川 | yoshinokawa_116 | 0.5m（推定：同上） | — | 2019–2022 |
| 徳島・那賀海部川 | tokushima_aerial_laser | 0.5m（実測） | 6672 | 2018–2020 |
| 山形・庄内 | 028_syounai | 0.5m（実測） | 6678 | 2022–23 |
| 大分南部 | oita_aerial_laser | 0.5m（推定：同上） | — | 2020 |
| 熊本地震 | h28_kumamoto_earthquake_aerial_laser | 0.5m（業務報告書に「0.5mDEM」と記載） | — | 2016 前後 |
| 令和 2 年 7 月豪雨 | r2_7_gouu | 0.5m（報告書に「0.5m グリッドデータ」と記載） | — | 2020 |
| 平成 30 年 7 月豪雨 | h30_7_gouu | 未確認 | — | 2018 |
| 能登半島地震 | r6_noto-peninsula-earthquake | 未確認 | — | 2024 |

### E. グリッドがない（点群だけ）

解像度はない。DEM にするには、グラウンド点群から自分でグリッドを作る必要がある。

- 埼玉: 山間部（2024）・河川・道路
- 北海道: UAV・小規模治山（局所）
- 大阪市: 淀川区・京橋駅周辺（局所）

### F. 手元の作業から見つかった公開元（CKAN 検索では拾えなかったもの）

| 県 | 公開元 | 解像度 | 形式 | 備考 |
|---|---|---|---|---|
| 宮城 | G空間情報センター「宮城県_3次元点群データ_グリッドデータ_2023」（gic-miyagi） | 1m（地理院 1m と重複） | CSV（図郭 ZIP） | ライセンスは要確認 |
| 広島 | 広島県 DoboX（data.hiroshima-dobox.jp） | 1m グリッド。2022 年の点群からは手元で 0.5m を作った | CSV・点群（bz2） | ライセンスは要確認 |
| 岡山 | 不明（手元にある `*_0.5g.txt`） | 0.5m | テキスト | 出典・ライセンスとも要確認 |
| 和歌山 | 和歌山県の点群 | 点群（手元で 1m に格子化） | LAS/LAZ | ライセンスは要確認 |
| 長崎（対馬） | オープンナガサキ | 点群 | LAZ | ライセンスは要確認 |

---

## 3. 手元の自作 DEM

- 走査: 2026-10-12。`C:\Users\yshiw` と外付けの D〜H から、tif / vrt / asc / xyz / las / laz / pmtiles / mbtiles を集めた（約 17.8 万ファイル）。その中から地域単位で結合した DEM の本体を選び、`gdalinfo` でヘッダーを読んだ
- 結果の一式は `local-scan/` にある（`ginfo.tsv` が選んだファイルのヘッダー情報、`demscan/*.tsv` がドライブごとの全ファイル一覧）
- ほとんどは csmap-py（CS立体図づくり）の途中で作った結合 DEM。図郭単位ではなく 1 枚の大きな GeoTIFF（Float32、DEFLATE）
- 同じファイルが複数の場所にあるものは、代表の場所だけを書き、「複製」の列に数を入れた

### A. 都道府県・広域の結合 DEM

| 地域 | 代表のパス | 解像度 | 座標系 | 範囲（経度, 緯度） | 容量 | 作成日 | 元データ | 複製 |
|---|---|---|---|---|---|---|---|---|
| 長野 | `E:\GIS\pref-nagano\csmap-py\nagano-dem.tif` | 0.5m | 6676 | 137.46–138.74, 35.18–37.04 | 20.3 GB | 2025-05-23 | nagano-dem（2 節 A） | — |
| 山梨 | `E:\GIS\pref-yamanashi\csmap-py\yamanashi-dem.tif` | 0.5m | 6676 | 138.18–139.14, 35.17–35.97 | 20.3 GB | 2025-04-06 | yamanashi-pointcloud-2024 の DEM | 2 |
| 山梨（4326 版） | `C:\Users\yshiw\Documents\GIS\dem2tiles\output-yamanashi\merged.tif` | 約 0.5m（5.0e-6°） | 4326 | 同上 | 53.4 GB | 2026-09-29 | grid2geotiff で作った図郭 tif（`GIS\grid2geotiff\testdata\yamanashi-dem\out`、3.8 万枚） | — |
| 京都 | `E:\GIS\pref-kyoto\csmap-py\kyoto-dem.tif` | 0.5m | 6674 | 134.85–136.07, 34.70–35.78 | 25.4 GB | 2025-04-05 | dem05_kyoto（2 節 B） | 2 |
| 富山 | `E:\GIS\pref-toyama\csmap-py\toyama-dem.tif` | 0.5m | 6675 | 136.77–137.70, 36.27–36.99 | 9.3 GB | 2025-04-15 | 富山 dem（2 節 B） | 5 |
| 鳥取 | `E:\GIS\pref-tottori\csmap-py\tottori-dem.tif` | 0.5m | 6673 | 133.12–134.53, 35.05–35.62 | 20.4 GB | 2025-06-15 | dem05_tottori。元の ZIP 24 本は `E:\GIS\pref-tottori\zip` | — |
| 神奈川 | `E:\GIS\pref-kanagawa\csmap-py\kanagawa-dem.tif` | 0.5m | 6677 | 138.94–139.75, 35.13–35.68 | 3.6 GB | 2025-06-15 | kanagawa-20xx の 0.5m グリッド | 2（OLD） |
| 埼玉（山間部） | `E:\GIS\pref-saitama\lp-pointcloud\grd\merged_05m_v2.tif` | 0.5m | 6677 | 138.70–139.57, 35.75–36.30 | 23.0 GB | 2025-09-14 | 埼玉 山間部点群（mountainous-area-pointcloud-saitama、砂防）から laspy と GMT triangulate で作った。v1 は `merged_05m.tif`（`csmap-py\saitama-dem.tif` と同じ） | 1 |
| 岡山 | `E:\GIS\pref-okayama\csmap-py\okayama-dem.tif` | 0.5m | 6673 | 133.26–134.41, 34.29–35.35 | 12.3 GB | 2025-06-16 | 岡山県の 0.5m グリッド（`*_0.5g.txt`）。出典は要確認 | — |
| 広島（2022） | `E:\GIS\pref-hiroshima-dem-2022\hiroshima-dem-2022.tif` | 0.5m | 6671 | 132.04–133.50, 34.02–34.88 | 22.3 GB | 2025-05-17 | DoboX の 2022 年点群を GMT triangulate で格子化（作業は `G:\GIS\pref-hiroshima-2022`） | 2（G:） |
| 広島 | `E:\GIS\pref-hiroshima-dem\csmap-py\hiroshima-dem.tif` | 1m（地理院 1m と重複） | 6671 | 132.01–133.48, 34.03–35.12 | 7.6 GB | 2025-05-17 | DoboX の 1m CSV グリッド | 3（H: ほか） |
| 宮城 | `E:\GIS\pref-miyagi\csmap-py\miyagi-dem.tif` | 1m（地理院 1m と重複） | 6678 | 140.26–141.60, 37.77–39.01 | 5.0 GB | 2025-06-11 | 宮城県_3次元点群データ_グリッドデータ_2023（1m CSV） | — |
| 和歌山 | `H:\GIS\pref-wakayama\wakayama-pointcloud\wakayamapc-dem.tif` | 1m（地理院 1m と重複） | 6674 | 134.98–136.02, 33.43–34.39 | 8.6 GB | 2024-03-24 | 和歌山県の点群から作った | 4 |
| 東京・区部 | `E:\GIS\tokyopc-23ku-2024\csmap-py\tokyopc-23ku-dem.tif` | 0.25m | 6677 | 139.56–139.92, 35.52–35.82 | 6.1 GB | 2025-05-24 | tokyopc-23ku-2024 の 0.25m グリッド | — |
| 東京・多摩 | `E:\GIS\tokyopc-tama-2023\csmap-py\tokyopc-tama-dem.tif` | 0.25m | 6677 | 138.94–139.60, 35.50–35.90 | 26.4 GB | 2025-05-24 | tokyopc-tama-2023 の 0.25m グリッド | — |
| 東京・島しょ | `D:\GIS-archive\tokyo-digitaltwin\tokyopc-shima-2023\tif\tokyopc-shima-01〜06-dem.tif` | 0.25m | 6677 | 伊豆諸島の 6 区分（大島〜青ヶ島） | 計 8.6 GB | 2025-05-25 | tokyopc-shima-2023 の 0.25m グリッド | 1（csmap-py） |
| 能登（2024） | `D:\rinya\noto-2024-csmap\csmap-py\noto-2024-dem.tif` | 0.5m | 6675 | 136.58–137.39, 36.59–37.87 | 12.7 GB | 2025-05-31 | 林野庁 r6_noto-peninsula-earthquake。Float64 版は `E:\GIS\rinya\noto-cs-2024\noto-dem-2024.tif` | 1 |
| 静岡・富士山と東部 | `H:\GIS\geospatial\shizuoka-pointcloud\shizuoka-mt-fuji-shizuoka-east\fuji-shizuoka-east-dem.tif` | 0.5m | 6676 | 138.51–138.90, 35.12–35.45 | 6.5 GB | 2024-02-24 | shizuoka-2021-pointcloud の 0.5m グリッド | 3857 版が同じフォルダにある |
| 静岡・中西部 | `C:\Users\yshiw\Documents\GIS\dem2tiles\output-shizuoka-fix\merged.tif` | 約 0.5m（5.3e-6°） | 4326 | 137.48–138.65, 34.59–35.12 | 0.6 GB | 2026-09-28 | dem2tiles の出力（元は VIRTUAL SHIZUOKA のグリッドとみられる） | 2（output、output-shizuoka-webp） |

### B. 小範囲・試作

| 地域 | パス | 解像度 | 座標系 | 備考 |
|---|---|---|---|---|
| 青ヶ島 | `C:\Users\yshiw\Documents\GIS\csmap-tile-pipeline\work\e2e-aogashima\aogashima-dem.tif` | 0.25m | 6677 | 東京島しょの一部。E: にも同じものがある |
| 新宿区 | `D:\GIS-archive\pref-tokyo-23ku\tokyopc-23ku-2024\dem_0.25m\shinjuku-ku-dem-025.tif` | 0.25m | 6677 | |
| 小河内ダム | `E:\GIS\tokyo-digitaltwin\tokyopc-tama-2023\tokyo-ogochi-dam-dem.tif` | 0.25m | 6677 | |
| 鳥取市付近 | `C:\Users\yshiw\Documents\GIS\naisui-risk-verification\data\interim\tottori\dem_1m.tif` | 1m（地理院 1m と重複） | 6673 | 内水リスク検証で 0.5m から作った |
| 輪島市熊野町 | `G:\GIS\geospatial\Noto-Earthquake\2024-notowest-ground\0.5mDEM\01_wajimashi-kumanomachi\wajimashi-kumanomachi-0.5mDEM.tif` | 0.5m | 不明（CRS なし） | 能登西部のグラウンド点群から。1m・2m・5m の試作もある |
| 能登東部の 1 図郭 | `H:\GIS\石川県\令和6年能登半島地震_能登東部3次元点群データ（発災前）\07ED5834_DEM.tif` | 0.25m | 6675 | |
| 埼玉・秩父の試作 | `D:\pref-saitama\las2dem\grd\merged_05m.tif` | 0.5m | 6677 | LAS から作った（9 図郭） |
| 対馬の試作 | `H:\GIS\open-nagasaki-tsusima-si\OLD\test-smrf\mergefile_grd_dem-6669.tif` | 1m（地理院 1m と重複） | 6669 | オープンナガサキの laz（174 GB）から SMRF で地表を抜いた試作 |
| 和歌山・WhiteboxTools の試作 | `H:\GIS\pref-wakayama\wakayama-pointcloud\OLD2\WhiteboxTools\` | 1m（地理院 1m と重複） | 6674 | |

### C. 気づいた点

- **0.5m 以上の結合 DEM がある地域**: 長野、山梨、京都、富山、鳥取、神奈川、埼玉（山間部）、岡山、広島（2022）、東京（区部・多摩・島しょは 0.25m）、能登、静岡（東部・中西部）。どれも Mapterhorn に入れると z17 以上になる
- **元は公開データ**なので、取り込むときは手元の結合 DEM を使うか、公開の図郭 tif から作り直すかを選べる。Mapterhorn の source は図郭単位の小さめのファイルを前提にしている（`source_to_cog.py` → `source_bounds.py`）。1 枚 20 GB 級の結合 DEM はそのまま渡すより、図郭に切り直すほうが扱いやすい
- **nodata の値がそろっていない**: -9999、0、-32767、1.70141e+38、なしが混在する。0 を nodata にしているもの（広島 1m の csmap-py 版、神奈川、岡山）は、海抜 0m の陸地も欠損扱いになるおそれがある
- **dem2tiles の出力（山梨・静岡中西部）は 4326 に投影し直したもの**。Mapterhorn に渡すなら、平面直角の元データのほうが再投影が 1 回で済む
