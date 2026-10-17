# 評価スクリプト（PR「escort_hunt」用・参考）

PR の数値を出したときに使った評価用スクリプトです。リポジトリ本体のコードではなく、
**検証環境（Linux, `/workspace` 配下）用にパスを直書き**しています。使うときは各ファイル先頭のパスを読み替えてください。

| ファイル | 内容 |
|---|---|
| `simenv.sh.example` | シミュレーター（ASRCAISim1 v1.1.0）用 venv を有効化 |
| `deploy_new.sh` | `agent/` を `workspace/Agents/MyAgentNew` にコピーし、`args.json` の `specialist` を `escort_hunt` にする |
| `run_one.py` | 1 試合（自エージェント vs `Agents/BenchMark`、色・シード指定）を回し、スコア・命中・護衛機撃墜などを JSON 出力 |
| `run_batch.sh` | `run_one.py` を 赤/青 × 指定シードで並列実行 |
| `variant.sh` | `MyAgentNew` をコピーして `args.json` にパラメータを上書きし、`run_batch.sh` で評価 |
| `summarize.py` / `compare2.py` | 集計／同じ（色, シード）のペア差分の平均と標準誤差 |
| `make_pr_charts.py` | この PR の図（`chart_*.png`）を生成 |

`local_test/run_eval_paired.py` は 24 行目に Windows のパスが直書きされているため、`run_one.py` 側で必要な関数だけを import して使っています（元ファイルは未変更）。
