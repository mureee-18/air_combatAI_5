# hybrid V6（別解法）

`specialist: hybrid` + プリセット `agent/presets/hybrid_v6.json`。既定の `agent/args.json`（`default`）は変更しない。

## ビルド（SIGNATE 提出版 V6 と同一内容の zip）

```bash
python scripts/build_submission.py --args agent/presets/hybrid_v6.json
# -> submission/submit.zip （args.json だけプリセットに差し替わる）
ATLA5_SUBMIT_CONFIRM=1 python tools/hooks/pre_submit_gate.py --command "check"   # 提出指示がある時のみ
```

ローカル対戦に配置する場合は `--deploy` を付ける（`workspace/Agents/MyAgent`）。

## 図の再生成

`python docs/pr/hybrid-v6/make_charts.py docs/pr/hybrid-v6`（評価結果 `/workspace/research/eval` を読む）。
評価スクリプト・相手エージェント設定・全結果表は `docs/exp/hybrid-vs-ma/`。
