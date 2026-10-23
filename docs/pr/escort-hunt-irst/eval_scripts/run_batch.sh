#!/bin/bash
# usage: run_batch.sh LABEL MODULE_PATH SEEDS(space sep) [JOBS]
LABEL=$1; MOD=$2; SEEDS=$3; J=${4:-8}
. /workspace/simenv.sh
cd /workspace/air_combatAI_5/workspace
OUT=/workspace/research/eval/$LABEL; mkdir -p $OUT
for c in Red Blue; do for s in $SEEDS; do echo "$c $s"; done; done | \
  xargs -P $J -n 2 sh -c 'PYTHONPATH=$PWD python /workspace/research/eval/run_one.py '"$MOD"' $0 $1 '"$OUT"'/${0}_${1}.json > '"$OUT"'/${0}_${1}.out 2>&1'
echo BATCH_DONE $LABEL
