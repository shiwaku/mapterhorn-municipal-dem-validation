#!/bin/sh
# source の補正後に aggregation から比較まで回し直す
set -eu
cd "$(dirname "$0")"
sh run.sh aggregation > aggregation.log 2>&1
sh finish.sh
