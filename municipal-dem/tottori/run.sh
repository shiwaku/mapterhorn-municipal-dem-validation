#!/bin/sh
# 鳥取（鳥取市〜砂丘）の検証を Mapterhorn の pipelines で回す
# 使い方: sh run.sh <段階>   段階は source / aggregation / downsampling / bundle
# クローン（../../mapterhorn/pipelines）は読み取り専用でマウントし、作業物は ./work に置く
set -eu
cd "$(dirname "$0")"
HERE=$(pwd -W 2>/dev/null || pwd)
STAGE=${1:?stage}

dr() {
  MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$HERE/work:/work" \
    -v "$HERE/../../mapterhorn/pipelines:/pipelines:ro" \
    -w /work mapterhorn-pipelines:local sh -c "$1"
}

PY=/opt/venv/bin/python
# aggregation_run / downsampling_run は downloader.py が tmp-store/queue を ready へ移すのを待つ。
# 同じコンテナで裏に回しておく（ファイルはコピーせずリンクで渡す）
DL="MAPTERHORN_SOFTLINK_DOWNLOADS=1 $PY /pipelines/downloader.py > /work/downloader.log 2>&1 &"
case "$STAGE" in
  source)
    for s in jptottori jpdem1a jpdem5a jpdem5b jpdem10b glo30; do
      dr "$PY /pipelines/source_to_cog.py $s > /dev/null && $PY /pipelines/source_bounds.py $s | tail -1"
    done
    ;;
  aggregation)
    dr "$DL $PY -u /pipelines/aggregation_covering.py && $PY -u /pipelines/aggregation_run.py"
    ;;
  downsampling)
    dr "$DL $PY -u /pipelines/downsampling_covering.py && $PY -u /pipelines/downsampling_run.py"
    ;;
  bundle)
    dr "TMPDIR=/tmp $PY /pipelines/bundle.py 1"
    ;;
  *) echo "unknown stage: $STAGE"; exit 1 ;;
esac
