#!/bin/bash
# usage: queue.sh JOBFILE   (lines: LABEL AGENT_DIR OPP) ; resumable, results in pool/LABEL_vs_OPP
cd /workspace/research/eval
S="$(seq -s ' ' 1 20)"
while read L A O; do [ -z "$L" ] && continue
  OPP=Agents/$O ./run_batch.sh pool/${L}_vs_$O Agents/$A "$S" 8 >/dev/null 2>&1
  python3 summarize.py pool/${L}_vs_$O
done < $1
echo QUEUE_DONE $1
