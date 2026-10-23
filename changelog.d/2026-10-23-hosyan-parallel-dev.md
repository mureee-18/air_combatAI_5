### 並行開発の土台（P1〜P7）

- ビルドに `--out` と `--preset` を追加し、zip には選んだ戦法が使うファイルだけを入れる
- 戦法を `specialists/` と `ideas/` から自動で見つける。提出できるのは `agent/args.json` か `agent/presets/` が名指しする戦法
- 評価結果を `results/runs/` に集め、`scripts/eval_pool.py` が相手プール（`opponents/`）と並列で対戦する
- `scripts/results_report.py` が集計表を作る。新しいアイデアの手順は `docs/PARALLEL_DEV.md`
- `agent/args.json` は昇格ルール（`scripts/check_promotion.py`）を通ったときだけ変える
- Claude 以外のエージェント向けの入口 `AGENTS.md` と、フォルダの分け方をまとめた `docs/REPO_LAYOUT.md` を追加
