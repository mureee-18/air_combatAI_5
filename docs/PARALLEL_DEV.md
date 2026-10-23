# 並行開発の手順

複数の人やエージェントが、互いの作業を壊さずに新しい戦法（アイデア）を同時に試すための手順です。
アイデアは自分専用のディレクトリとプリセットだけを足し、評価結果は同じ PR に入れます。共有コードは変えません。
フォルダの分け方と、誰がどこを変えてよいかは [`REPO_LAYOUT.md`](REPO_LAYOUT.md) にあります。
Claude 以外のエージェントの入口は [`AGENTS.md`](../AGENTS.md) です。

## 名前の決まり

| もの | 形 | 例 |
|---|---|---|
| ブランチ | `idea/<作者>/<名前>` | `idea/hosyan/rushguard` |
| worktree | `/workspace/wt/<作者>-<名前>` | `/workspace/wt/hosyan-rushguard` |
| アイデア名 | `<作者>_<名前>` | `hosyan_rushguard` |

作者と名前は英小文字と数字だけです。アイデア名に作者を付けるので、別の人と名前がぶつかりません。

## アイデアが足すファイル

- `agent/strategy/ideas/<作者>_<名前>/__init__.py` に戦法の本体を書きます。同じディレクトリの別モジュールやデータファイルも zip に入ります
- `agent/presets/<作者>_<名前>.json` には、そのアイデアを選ぶ args（`"specialist": "<作者>_<名前>"`）を書きます
- `results/runs/<run_id>/` には評価結果を置きます。`eval_pool.py` が書きます
- `changelog.d/<YYYY-MM-DD>-<作者>-<名前>.md` は任意です。CHANGELOG に載せたいときに足します

`agent/args.json`、`agent/config.json`、`agent/strategy/agents/`、`agent/strategy/specialists/`、
`agent/strategy/active.py` は変えません。共有コードの挙動を変えたいときは、継承かコピーでアイデア側に書きます。

## 手順

1. 最新の master から自分の worktree を作ります。

   ```bash
   git fetch origin
   git worktree add -b idea/hosyan/rushguard /workspace/wt/hosyan-rushguard origin/master
   cd /workspace/wt/hosyan-rushguard
   ```

2. 雛形を作ります。同じ名前がローカルかリモートのブランチにあれば、終了コード1で止まります。

   ```bash
   python scripts/new_idea.py hosyan rushguard
   ```

3. `agent/strategy/ideas/hosyan_rushguard/__init__.py` を編集します。テストと lint を通します。

   ```bash
   uvx --with pytest pytest tests/ -q
   uvx ruff check agent/ tools/ tests/ scripts/
   ```

4. プール全体と対戦して結果を書きます。ワーカー数に上限はありません。マシンを分けるときは `--shard i/N` を使います。

   ```bash
   . /workspace/simenv.sh
   export ATLA5_SIM_DIR=/workspace/air_combatAI_5/workspace
   python scripts/eval_pool.py --preset hosyan_rushguard --opponents pool --seeds 1-20 --worker hosyan
   python scripts/results_report.py --out /tmp/leaderboard --candidate hosyan_rushguard
   ```

5. アイデア、プリセット、評価結果を1つの PR にまとめます。

   ```bash
   git add agent/strategy/ideas/hosyan_rushguard agent/presets/hosyan_rushguard.json results/runs
   git commit -m "idea: hosyan_rushguard"
   git push -u origin idea/hosyan/rushguard
   gh pr create --base master --fill
   ```

CI は、アイデア名に作者が付いているか、アイデアを足した PR に complete の run があるかを確かめます。
run が無ければ `idea 'hosyan_rushguard' has no complete run under results/runs/` で失敗します。
`results/runs/` の run は追記だけです。complete の run を書き換えると CI が失敗します。

## 提出

`agent/presets/` のプリセットはどれも提出できます。`python scripts/build_submission.py --preset hosyan_rushguard` で、
そのアイデアが使うファイルだけを入れた zip を作ります。提出はユーザーの明示指示があるときだけです。

## 既定（agent/args.json）を変える：昇格ルール

`agent/args.json` は昇格ルールを通ったときだけ変えます。このルールは「既定の `agent/args.json` は変えない」という
以前の決まりを置き換えます。昇格 PR では CI が `python scripts/check_promotion.py --base origin/master` を実行し、
次をすべて満たすときだけ通します。

1. 新しい `agent/args.json` と現行の既定（merge base の `agent/args.json`）の両方に、同じ args で作った
   complete の run が `results/runs/` にあり、seeds 1〜20 × 両色 × `opponents/pool.json` の pool 全部を覆う
2. pool の最小値（相手ごとの平均スコアの最小）が現行以上
3. 同じ相手・seed・色で突き合わせた pool 平均の差が、その標準誤差の2倍より大きい
4. どの相手でも、その相手だけで突き合わせた差の平均が −2×標準誤差 以上（大きく負ける相手がない）

run は次のように作ります。現行の既定は昇格 PR を作る前の master で `--default` を回します。
同じ args の complete run が `results/runs/` に既にあれば、それが使われるので回し直しは要りません。

```bash
python scripts/eval_pool.py --default --opponents pool --seeds 1-20   # master で現行の既定
python scripts/eval_pool.py --preset hosyan_rushguard --opponents pool --seeds 1-20
```

## 共有コアを変える

共有コアの変更は後方互換のものだけにします。`agents/`、`specialists/`、`active.py`、`config.json` を変えたら、
次を実行します。既定ビルドと全プリセットを merge base と HEAD で seeds 1〜3 × 両色、BenchMark と対戦させ、
1行でも結果が変われば失敗します。

```bash
python scripts/check_core_compat.py --base origin/master --workers 8
```

## スタックした PR のマージ

PR を積み重ねる（各 PR の base が1つ前の PR のブランチ）ときは、下から順に1本ずつ master に入れます。
そのまま次の PR のマージボタンを押すと、master ではなく1つ前の PR のブランチに入ります。

1. 一番下の PR（base が master）を「Create a merge commit」でマージします。squash と rebase は使いません。
2. 次の PR の base を master に付け替えます。`gh pr edit <次の番号> --base master`
3. 差分がその PR の分だけになり、CI が通ったのを確かめてからマージします。2 に戻って上まで繰り返します。

## CHANGELOG

`changelog.d/` に1件1ファイルで断片を足します。`python scripts/changelog.py` が CHANGELOG.md の先頭に書き出します。
詳しくは `changelog.d/README.md` を見てください。
