#!/usr/bin/env bash
# Mapterhorn の日本域の z13+ サブピラミッド（6-x-y.pmtiles）を上流から落とし、md5 を照合する。
#
#   bash download.sh            # このフォルダに落とす。ログは download.log に追記
#
# files.txt … 対象の「名前 サイズ md5」。download.mapterhorn.com/download_urls.json から、
#             bbox 122.9,20.4,154.0,45.6（与那国島〜南鳥島、沖ノ鳥島〜宗谷岬）に掛かるものを抜き出した（2026-10-11）
# 途中で止まっても再実行すれば続きから。照合済みのファイルには .ok を付けて飛ばす。
# 2 つ同時に動かすと同じファイルに追記し合って壊れるので、ロック（.lock フォルダ）で防ぐ。
# planet-japan（z0-12）は検証に要らないので落とさない（.ok だけ残してある）。
set -uo pipefail
cd "$(dirname "$0")"
mkdir .lock 2>/dev/null || { echo "別の download.sh が動いている（止まっているなら .lock を消す）"; exit 1; }
trap 'rmdir .lock' EXIT
exec >>download.log 2>&1
echo "== 開始 $(date '+%F %T')"

get() { # name size md5
  local n=$1 s=$2 m=$3 a got h
  if [[ -f "$n.ok" ]]; then echo "[skip] $n"; return 0; fi
  # curl の --retry は使わない。切れるとファイルをその回の開始時点まで切り詰めて取り直すので、
  # 長いダウンロードでは進んだ分を捨ててしまう。ここで呼び直せば -C - が今の大きさから続ける
  for a in $(seq 50); do
    curl -fsS -C - -o "$n" "https://download.mapterhorn.com/$n" && break
    echo "[retry $a] $n $(stat -c %s "$n" 2>/dev/null) bytes $(date '+%T')"; sleep 30
  done
  got=$(stat -c %s "$n" 2>/dev/null || echo 0)
  [[ "$got" == "$s" ]] || { echo "[NG size] $n $got != $s"; return 1; }
  h=$(md5sum "$n" | cut -d' ' -f1)
  [[ "$h" == "$m" ]] || { echo "[NG md5] $n $h != $m（消した。再実行で取り直す）"; rm -f "$n"; return 1; }
  touch "$n.ok"; echo "[ok] $n $got bytes $(date '+%T')"
}
export -f get

# 小さい順に 3 本並行
grep '^6-' files.txt | sort -k2 -n | xargs -P 3 -L 1 bash -c 'get "$0" "$1" "$2"'
echo "== 終了 $(date '+%F %T')  照合済み $(ls 6-*.pmtiles.ok | wc -l) / $(grep -c '^6-' files.txt)"
