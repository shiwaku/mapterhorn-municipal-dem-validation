#!/bin/sh
# downsampling → bundle → 本家版との比較 を続けて回す
set -eu
cd "$(dirname "$0")"
HERE=$(pwd -W 2>/dev/null || pwd)
sh run.sh downsampling > downsampling.log 2>&1
sh run.sh bundle > bundle.log 2>&1
ls -la work/bundle-store
cmp() { MSYS_NO_PATHCONV=1 docker run --rm -v "$HERE/work:/work" -v "$HERE:/t:ro" -v "$HERE/../../japan:/japan:ro" -w /work mapterhorn-pipelines:local /opt/venv/bin/python /t/compare.py "$@"; }
OLD=/japan/6-55-25.pmtiles; NEW=/work/bundle-store/6-55-25.pmtiles
mkdir -p work/compare
for z in 13 14 15 16 17; do cmp stats $OLD $NEW $z 134.10 35.40 134.30 35.55; done
for f in old new; do P=$OLD; [ $f = new ] && P=$NEW
  cmp render $P 17 134.225 35.535 134.250 35.545 /work/compare/dune-z17-$f.png
  cmp render $P 16 134.20 35.49 134.25 35.52 /work/compare/city-z16-$f.png
done
