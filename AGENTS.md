# AGENTS.md

Claude 以外のコーディングエージェント（Cursor、Codex など）が最初に読むファイルです。
ここには要点だけを書きます。正本は次の3つです。食い違ったら正本に従ってください。

- [`CLAUDE.md`](CLAUDE.md)：守るルール（Anti-Regression Rules）、環境、コマンド一覧
- [`docs/PARALLEL_DEV.md`](docs/PARALLEL_DEV.md)：アイデアを並行して進める手順、昇格ルール、共有コアの変え方
- [`docs/REPO_LAYOUT.md`](docs/REPO_LAYOUT.md)：フォルダの分け方と、誰がどこを変えてよいか

## 必ず守ること

1. **提出はユーザーの明示指示があるときだけ。** 自分の判断で `signate submit` を実行しません。
   `tools/hooks/pre_submit_gate.py` が、`ATLA5_SUBMIT_CONFIRM=1` の無い提出を止めます。
2. **zip に入る戦法は、プリセットが名指ししたものだけ。** `agent/args.json`（既定）か
   `agent/presets/<名前>.json` が `specialist` で名指しした戦法と、それが import するファイルだけが入ります。
3. **`agent/args.json` は昇格ルールを通ったときだけ変える。** CI が `scripts/check_promotion.py` で確かめます。
   条件は `docs/PARALLEL_DEV.md` の「昇格ルール」にあります。
4. **共有コアは後方互換の変更だけ。** `agent/strategy/agents/`、`agent/strategy/specialists/`、
   `agent/strategy/active.py`、`agent/config.json` を変えたら `scripts/check_core_compat.py` を通します。
5. **アイデアは `agent/strategy/ideas/<作者>_<名前>/` に置く。** プリセットは `agent/presets/<作者>_<名前>.json` です。
6. **`results/runs/` は追記だけ。** complete になった run は書き換えず、新しい run を足します。

## 並列数に上限はない

エージェントは何体同時に動かしてもかまいません。衝突しないのは、次のように書く場所が分かれているからです。

- 1体につき、git worktree とブランチを1つずつ使います（`idea/<作者>/<名前>`）。
- 書くのは自分のアイデアのフォルダと、自分のプリセットと、新しい run のフォルダだけです。
- run のフォルダ名には時刻、ワーカー名、コミット、乱数が入るので、同時に書いても重なりません。
- CHANGELOG は `changelog.d/` に1件1ファイルで足します。

そのため、2体のエージェントが同じファイルに書くことはありません。

## 新しいアイデアを始める

```bash
git fetch origin
git worktree add -b idea/<作者>/<名前> /workspace/wt/<作者>-<名前> origin/master
cd /workspace/wt/<作者>-<名前>
python3 scripts/new_idea.py <作者> <名前>   # ideas/<作者>_<名前>/ と presets/<作者>_<名前>.json を作る
```

作者と名前は英小文字と数字だけです。同じ名前のブランチがあれば `new_idea.py` が止まります。

## 評価する

評価は決まった seed で回すので、同じコードなら何度回しても同じ結果になります。
seeds 1〜20 × 両色 × `opponents/pool.json` の相手全部で回し、結果は `results/runs/<run_id>/` に書かれます。

```bash
. /workspace/simenv.sh
export ATLA5_SIM_DIR=/workspace/air_combatAI_5/workspace
python3 scripts/eval_pool.py --preset <作者>_<名前> --opponents pool --seeds 1-20 --worker <作者>
python3 scripts/results_report.py --out /tmp/leaderboard --candidate <作者>_<名前>
```

`--workers` に上限はありません（既定は CPU 数）。複数のマシンで分けるときは `--shard i/N` を使います。

## PR を出す前に

CI と同じ確認を手元でも通します。

```bash
uvx --with pytest pytest tests/ -q
uvx ruff check agent/ tools/ tests/ scripts/
python3 scripts/new_idea.py --check origin/master          # アイデアの名前と run があるか
python3 scripts/check_core_compat.py --base origin/master  # 共有コアを変えたときだけ
python3 scripts/check_promotion.py --base origin/master    # agent/args.json を変えたときだけ
```

提出を頼まれたときは、提出の前に次も通します。

```bash
python3 scripts/build_submission.py --preset <作者>_<名前>
python3 scripts/zip_check.py submission/submit.zip
# sim の workspace で validate.py --youth 1 を回す（コマンドは CLAUDE.md）
python3 tools/hooks/pre_submit_gate.py
```

PR には、アイデア、プリセット、評価の run を1つにまとめます。master へのマージはユーザーが決めます。
