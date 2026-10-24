#!/bin/sh
# 鳥取（鳥取市〜砂丘）の検証を Mapterhorn の pipelines で回す
# 使い方: sh run.sh <段階>   段階は source / bounds / vshift / aggregation / downsampling / bundle
# クローン（../../mapterhorn/pipelines）は読み取り専用でマウントし、作業物は ./work に置く
# 環境変数: WORK（作業フォルダ、既定 work）、SOURCES（source 段階で処理するソース）、
#           CPUS（コンテナが使う CPU 数とプロセス数。既定は制限なし）
set -eu
cd "$(dirname "$0")"
HERE=$(pwd -W 2>/dev/null || pwd)
STAGE=${1:?stage}
WORK=${WORK:-work}
SOURCES=${SOURCES:-jptottori jpdem1a jpdem5a jpdem5b jpdem10b glo30}
CPUS=${CPUS:-}
ZERO_FILLED="dem_05lb753.tif dem_05lb964.tif"

dr() {
  MSYS_NO_PATHCONV=1 docker run --rm ${CPUS:+--cpus=$CPUS -e MAPTERHORN_CPUS=$CPUS} \
    -e PYTHONPATH=/limit:/pipelines \
    -v "$HERE/$WORK:/work" \
    -v "$HERE/limit:/limit:ro" \
    -v "$HERE/../scripts:/scripts:ro" \
    -v "$HERE/../grids:/grids:ro" \
    -v "$HERE/../../mapterhorn/pipelines:/pipelines:ro" \
    -w /work mapterhorn-pipelines:local sh -c "$1"
}

PY=/opt/venv/bin/python
# aggregation_run / downsampling_run は downloader.py が tmp-store/queue を ready へ移すのを待つ。
# 同じコンテナで裏に回しておく（ファイルはコピーせずリンクで渡す）
DL="MAPTERHORN_SOFTLINK_DOWNLOADS=1 $PY /pipelines/downloader.py > /work/downloader.log 2>&1 &"
case "$STAGE" in
  source)
    for s in $SOURCES; do
      # jptottori の一部の図郭は NoData 値がない。混ざると gdalbuildvrt で図郭の外が 0 になるので、COG 化の前に付ける。
      # 弓ヶ浜半島の 2 枚はデータのない所を 0 で埋めているので、先にその 0 を NoData にする（#3）
      if [ $s = jptottori ]; then
        present=$(cd $WORK/source-store/jptottori && ls $ZERO_FILLED 2>/dev/null | sed 's/\.tif$//' | tr '\n' ' ' || true)
        [ -n "$present" ] && dr "$PY /scripts/source_zero_to_nodata.py $s -9999 $present"
        dr "$PY /pipelines/source_set_nodata.py $s -9999 | tail -1"
      fi
      dr "$PY /pipelines/source_to_cog.py $s > /dev/null && $PY /pipelines/source_bounds.py $s | tail -1"
    done
    ;;
  bounds)
    for s in $SOURCES; do
      dr "$PY /pipelines/source_bounds.py $s | tail -1"
    done
    ;;
  vshift)
    # 標高改定前の jptottori を、水準点の補正量で測地成果2024 にそろえる（source の後に回し、bounds を取り直す）
    dr "$PY -u /scripts/source_vertical_shift.py jptottori /grids/hyokorevBM_jgd2024.tif && $PY /pipelines/source_bounds.py jptottori | tail -1"
    ;;
  aggregation)
    dr "$DL $PY -u /pipelines/aggregation_covering.py && $PY -u /pipelines/aggregation_run.py"
    ;;
  downsampling)
    # aggregation が tmp-store/source に残したリンクを消す。downloader.py は毎回 tmp-store の容量を数えるので、
    # 数万本残っていると Docker Desktop の共有フォルダ越しでは数え終わらず、downsampling が待ち続ける
    dr "find /work/tmp-store/source -type l -delete 2>/dev/null; $DL $PY -u /pipelines/downsampling_covering.py && $PY -u /pipelines/downsampling_run.py"
    ;;
  bundle)
    dr "TMPDIR=/tmp $PY /pipelines/bundle.py 1"
    ;;
  *) echo "unknown stage: $STAGE"; exit 1 ;;
esac
