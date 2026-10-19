#!/bin/sh
# 地理院 DEM を範囲ぶん取得し、COG にして source-store/<ソース> に足す（既にあるファイルは取らない）
# 使い方: sh gsi_fetch.sh   一覧は gsi-lists/download-full.txt（gsi_list.py で作る）。WORK・CPUS は run.sh と同じ
set -eu
cd "$(dirname "$0")"
export WORK=${WORK:-work-full}
SRCS="jpdem1a jpdem5a jpdem5b jpdem10b"
for s in $SRCS; do mkdir -p $WORK/source-store/new-$s; done
# 本体か new- に既にあるファイルは取らない（ファイルごとに sh を起こすと Windows では遅いので、ここでまとめて判定する）
while read s u; do
  f=${u##*/}
  [ -f $WORK/source-store/$s/$f ] || [ -f $WORK/source-store/new-$s/$f ] || echo "$s $u"
done < gsi-lists/download-full.txt > gsi-lists/download-new.txt
# 同時接続は 8 本に抑える
awk -v w=$WORK '{print w "/source-store/new-" $1 "\n" $2}' gsi-lists/download-new.txt \
  | xargs -r -n2 -P8 sh -c 'curl -sSf --retry 3 -o "$0/${1##*/}" "$1" || echo "FAIL $1"'
# COG にしてから本体のソースへ移し、bounds を取り直す
SOURCES="$(for s in $SRCS; do printf 'new-%s ' $s; done)" sh run.sh source
for s in $SRCS; do
  mv $WORK/source-store/new-$s/*.tif $WORK/source-store/$s/ 2>/dev/null || true
  rm -rf $WORK/source-store/new-$s
done
SOURCES="$SRCS" sh run.sh bounds
