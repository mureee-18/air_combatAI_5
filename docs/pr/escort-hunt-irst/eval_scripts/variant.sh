# usage: variant.sh LABEL 'json-args-patch' SEEDS JOBS
LABEL=$1; PATCH=$2; SEEDS=$3; J=${4:-8}
D=/workspace/air_combatAI_5/workspace/Agents/V_$LABEL
rm -rf $D; cp -r /workspace/air_combatAI_5/workspace/Agents/MyAgentNew $D
python3 -c "
import json,sys;p='$D/args.json';a=json.load(open(p));a.update(json.loads(sys.argv[1]));json.dump(a,open(p,'w'),indent=1)" "$PATCH"
rm -rf /workspace/research/eval/$LABEL
/workspace/research/eval/run_batch.sh $LABEL Agents/V_$LABEL "$SEEDS" $J > /dev/null 2>&1
python3 /workspace/research/eval/summarize.py /workspace/research/eval/$LABEL
