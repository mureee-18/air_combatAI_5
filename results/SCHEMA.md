# results/ の形式（schema 1）

評価結果の正本です。1回の評価を1つの run として `results/runs/<run_id>/` に置きます。
run は追加だけで、`complete` になった run は書き換えません。

## run_id

`<UTC 時刻>-<worker>-<short sha>-<乱数6文字>` です。例は `20261023T013000Z-hosyan-acc30b6-k3f9qz` です。
`scripts/results_store.py` の `new_run_id()` が作ります。別のワーカーや別のブランチが同時に作っても重なりません。

## ファイル

```
results/runs/<run_id>/
  manifest.json      # run の情報。形式は schema/manifest.schema.json
  games/<相手>_<色>_<seed>.json   # 実行中だけ。1試合1ファイル
  games.jsonl        # complete 後。1行1試合。形式は schema/game.schema.json
```

- 実行中は `write_game()` が1試合ずつ `games/` に書きます。一時ファイルに書いてから rename するので、途中で止まっても壊れたファイルは残りません。
- `finish_run()` が `games/` を `games.jsonl` にまとめ、`manifest.json` の `status` を `complete` にし、行数と `games_sha256` を記録します。
- `status` は `running`、`complete`、`aborted` のどれかです。集計は `complete` を使い、`aborted` は件数つきで別に扱います。

## manifest.json の主な項目

| 項目 | 内容 |
|---|---|
| `candidate.name` | プリセット名（例 `hybrid_v6`）、または既定ビルドなら `default` |
| `candidate.args` / `args_sha256` | ビルドに使った args.json とそのハッシュ |
| `candidate.code_sha256` | 配置したエージェントのファイル一式のハッシュ |
| `opponents[]` | 相手の名前、コードのコミット、args とコードのハッシュ |
| `protocol` | seeds、colors、youth、make_log |
| `git` | 評価したコミット、ブランチ、未コミット変更の有無 |
| `imported` | 過去の結果を取り込んだ run なら true。`source` に元の場所 |

## 試合の行

`opponent`、`seed`、`color`、`result`（win / draw / loss）、`score`、`endReason`、`step_count`、
`our_alive`、`enemy_alive`、`our_launched`、`our_hits`、`enemy_launched`、`enemy_hits`、
`enemy_escort_killed`、`our_escort_killed`、`error`、`wall_s`（任意）です。

## コマンド

```bash
python scripts/results_store.py validate results/
python scripts/results_store.py import-legacy /workspace/research/eval/pool --rename V6=hybrid_v6
```

対戦ログやリプレイは大きいので results/ に入れません。
