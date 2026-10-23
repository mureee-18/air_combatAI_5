#!/bin/bash
# usage: pool.sh LABEL SRC_WT 'json-args-patch' [OPPS]  -> runs vs BenchMark, MA, EH on seeds 1-20 x both colours
LABEL=$1; SRC=$2; PATCH=$3; OPPS=${4:-"BenchMark MA EH"}
D=/workspace/air_combatAI_5/workspace/Agents/H_$LABEL
rm -rf $D; mkdir -p $D; cp $SRC/agent/__init__.py $SRC/agent/args.json $SRC/agent/config.json $D/; cp -r $SRC/agent/strategy $D/
find $D -name __pycache__ -exec rm -rf {} +
python3 -c "
import json,sys;p='$D/args.json';a=json.load(open(p));a.update(json.loads(sys.argv[1]));json.dump(a,open(p,'w'),indent=1)" "$PATCH"
S="$(seq -s ' ' 1 20)"
for o in $OPPS; do OPP=Agents/$o /workspace/research/eval/run_batch.sh pool/${LABEL}_vs_$o Agents/H_$LABEL "$S" 8 >/dev/null 2>&1; python3 /workspace/research/eval/summarize.py /workspace/research/eval/pool/${LABEL}_vs_$o; done
echo POOL_DONE $LABEL
