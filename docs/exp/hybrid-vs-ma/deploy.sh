#!/bin/bash
# usage: deploy.sh AGENT_NAME SRC_WT 'json-args-patch'
NAME=$1; SRC=$2; PATCH=$3
D=/workspace/air_combatAI_5/workspace/Agents/$NAME
rm -rf $D; mkdir -p $D; cp $SRC/agent/__init__.py $SRC/agent/args.json $SRC/agent/config.json $D/; cp -r $SRC/agent/strategy $D/
find $D -name __pycache__ -exec rm -rf {} +
python3 -c "
import json,sys;p='$D/args.json';a=json.load(open(p));a.update(json.loads(sys.argv[1]));json.dump(a,open(p,'w'),indent=1)" "$PATCH"
