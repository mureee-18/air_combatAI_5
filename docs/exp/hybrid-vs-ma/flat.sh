#!/bin/bash
# flat job pool: lines "LABEL AGENT OPP COLOR SEED"; skips finished
. /workspace/simenv.sh; cd /workspace/air_combatAI_5/workspace
xargs -P 8 -L 1 sh -c 'O=/workspace/research/eval/pool/${0}_vs_$2; mkdir -p $O; [ -f $O/${3}_${4}.json ] && exit 0; OPP=Agents/$2 PYTHONPATH=$PWD python /workspace/research/eval/run_one.py Agents/$1 $3 $4 $O/${3}_${4}.json > $O/${3}_${4}.out 2>&1' < $1
echo FLAT_DONE
