#!/bin/sh
# 鳥取県全体（図郭 1,291 枚）を source〜bundle まで回し、段階ごとの時間と容量を work-full/stages.tsv に残す
# 使い方: sh run-full.sh [最初の段階]   PC の負荷を抑えるため、既定で CPUS=4 にする
# 前提: work-full/source-store/jptottori に図郭を取り出してあること（extract_tiles.py）、地理院の各ソースは COG 化と bounds 済み
set -eu
cd "$(dirname "$0")"
export WORK=work-full CPUS=${CPUS:-4} SOURCES=jptottori
FROM=${1:-source}
LOG=$WORK/stages.tsv
[ -f $LOG ] || printf 'stage\tstart\tseconds\twork_size\n' > $LOG
go=0
for st in source vshift aggregation downsampling bundle; do
  [ $st = $FROM ] && go=1
  [ $go = 1 ] || continue
  t0=$(date +%s)
  sh run.sh $st > $WORK/$st.log 2>&1
  t1=$(date +%s)
  printf '%s\t%s\t%s\t%s\n' $st "$(date -d @$t0 '+%F %T')" $((t1 - t0)) "$(du -sh $WORK | cut -f1)" >> $LOG
done
ls -la $WORK/bundle-store
