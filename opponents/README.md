# 対戦相手プール

`scripts/eval_pool.py` が対戦に使う相手です。`pool.json` の `pool` が昇格ルールで使う相手一式です。

| 名前 | 中身 |
|---|---|
| BenchMark | 配布の初期行動判断モデル（sim の `Agents/BenchMark`） |
| MA | MA の default（温存弾版）。コミット `6866d8e` のコードと `MA/args.json` |
| EH | escort_hunt の既定設定。コミット `e7de27d` のコードと `EH/args.json` |
| O_RUSH | 4機で護衛対象機へ突撃する escort_hunt。コミット `cb5cdae` のコードと `O_RUSH/args.json` |
| O_GUARD | 1機で攻撃し、3機で自陣を守る escort_hunt。コミット `cb5cdae` のコードと `O_GUARD/args.json` |
| O_BMAGG | BenchMark の攻撃寄り設定。sim の BenchMark に `O_BMAGG/config.json` を重ねる |

## 相手の種類

- `"kind": "repo"` は、`commit` の `agent/` を `git archive` で取り出し、`args` のファイルで args.json を差し替えます。
- `"kind": "sim"` は、sim の `path` をコピーし、`config` があれば config.json を差し替えます。

相手を足すときは、`opponents/<名前>/` に args.json か config.json を置き、`pool.json` の `opponents` に1行足します。
昇格ルールに使う相手を変えるときは `pool` も変えます。`pool` を変えると、過去の昇格の比較がそろわなくなる点に注意してください。

## ワーカー数の決め方

`--workers` に上限はありません。既定は CPU 数です。1試合のメモリは最大で約 0.8 GB でした（2026-10-23、box で計測）。
空きメモリを 0.8 GB で割った数を上限の目安にしてください。CPU 数を超えると1試合あたりの時間が延びます。
シミュレータには1ステップ3秒の制限があります。極端に詰め込むと、タイムアウトでエラーになる試合が出るおそれがあります。
