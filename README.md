# air_combatAI_5

SIGNATE「第5回空戦AIチャレンジ」**ユース部門**（第5回 = R8）向けのエージェント開発リポジトリ。

- コンペ: https://user.competition.signate.jp/ja/competition/detail/?competition=42024ceef5064aa6a7f463aac3f26fc2
- タスク（ユース部門）: `5564d022dac44dd498c97aa82efab260`

提出物は「行動判断を行う Python モジュール一式を zip にまとめたもの」で、評価システムは
x86 CPU・Linux 上で初期行動判断モデル（BenchMark）と対戦させる。

## 構成

```
agent/                     提出モジュール本体（zip 化される）
├── __init__.py            必須4関数 → strategy.active に委譲
├── args.json              4関数に渡る引数（`specialist` で方針を切替）
├── config.json            modelConfig（specialist ごとにセクションを分ける）
└── strategy/
    ├── active.py          switchboard: specialist の選択と modelConfig の解決
    ├── agents/            Agent クラス本体（S方式: 1機に1エージェント）
    └── specialists/       方針（Policy）と Agent クラスの組
submission/                生成された提出物（gitignore）
workspace/                 配布シミュレータの展開先（gitignore）
data/                      配布データ（gitignore）
local_test/                seed 固定のペア評価ハーネス
tools/
├── battle_analyzer/       ログ解析とログ仕様書
├── hooks/                 提出前ゲート
├── log_cleanup/           ログの世代管理
└── signate/               SIGNATE CLI ラッパー
analysis/                  改善セッションの記録
```

## セットアップ

```bash
# 1. SIGNATE CLI（認証まで）
uv tool install signate
python tools/signate/cli.py login

# 2. 配布データの取得と展開
python tools/signate/cli.py download 59e1d84df60542d6bee39ccba66ecc70 --path=data/simulator_dist.zip
python -c "import zipfile; zipfile.ZipFile('data/simulator_dist.zip').extractall('workspace')"

# 3. コンテナ（Docker Desktop / WSL2）
docker compose build cpu        # GPU を使う場合は gpu
docker compose up -d cpu

# 4. 動作確認
docker exec atla5-cpu bash -lc "cd /workspace && python validate.py --youth 1 --num-validation 1"
```

## 主なコマンド

| 目的 | コマンド |
|---|---|
| 提出 zip の生成 | `python scripts/build_submission.py --deploy` |
| zip の単体検証 | `docker exec atla5-cpu bash -lc "python /repo/scripts/zip_check.py /repo/submission/submit.zip"` |
| 通常の対戦（3戦） | `python scripts/run_eval.py --games 3` |
| パラメータ走査 | `python scripts/run_eval.py --games 3 --sweep fireRangeKm=25,35,50` |
| **seed 固定ペア評価** | `docker exec atla5-cpu bash -lc "cd /workspace && python /repo/local_test/run_eval_paired.py --seeds 1,2,3 --colors both --out /workspace/paired/baseline.json"` |
| ログから挙動指標 | `python tools/battle_analyzer/battle_stats.py workspace/results/0/log_0.json` |
| ログから軌跡を復元 | `python tools/battle_analyzer/trajectory.py workspace/results_tel/0/log_0.json` |
| ログの整理 | `python tools/log_cleanup/cleanup.py`（`--execute` で削除） |
| **ダッシュボード** | `python tools/state_dashboard/serve.py --open`（http://127.0.0.1:8765） |
| 環境の定期点検 | `python tools/ops/healthcheck.py`（結果を `analysis/ops/heartbeat.log` に追記） |
| 提出 | `ATLA5_SUBMIT_CONFIRM=1 python tools/signate/cli.py submit submission/submit.zip --memo "..."` |
| テスト / lint | `pytest tests/ -q` / `ruff check agent/ tools/ tests/ scripts/ analysis/` |

評価は**勝率ではなく挙動指標**（`avg_score` / `avg_our_alive` / `avg_enemy_alive`）で判定する。
同一 seed 群での A/B 比較ができるので、改善は必ずペア評価で確認する。

## ダッシュボード

開発状況を1画面で可視化するローカルダッシュボード（依存ゼロ・オフライン動作）。

```bash
python tools/state_dashboard/serve.py --open        # http://127.0.0.1:8765
python tools/state_dashboard/serve.py --once        # JSON を標準出力（CI/スクリプト用）
python tools/state_dashboard/cache_bump.py          # ブラウザのキャッシュを確実に飛ばす
```

タブ構成:

| タブ | 内容 |
|---|---|
| 環境 | Docker コンテナ、シミュレータ配置、`workspace/Agents/MyAgent` と repo の**ドリフト検出**、サイズ |
| 提出 | 現在の specialist（提出可否）、`submit.zip` の有無とルートファイル、`pre_submit_gate.py` の判定 |
| 評価 | `workspace/paired/*.json` の比較（★ が `avg_score` 最良）、平均スコアバー、明細（色/seed/結果/スコア） |
| ログ | `workspace/results*/` の世代とサイズ、最新ログの挙動指標（`battle_stats` と同じ値） |
| 改善セッション | `analysis/agents/*/session_state.json` の仮説・前提・サイクル数 |
| git | ブランチ / 未コミット / ahead-behind / 直近コミット |
| コマンド | 主要コマンドのコピーリスト |
| ルール | コンペルール（採点式・対戦条件・提出ルール・要確認項目）。内容は `tools/state_dashboard/rules.json` |
| 軌跡 | 自作エージェントのログから復元したレーダースコープ再生（後述） |

ダッシュボードは `agent/` の提出物には含まれません（`tools/` は zip 対象外のため）。

## 軌跡リプレイ

公式シミュレータのビューアは headless（Docker）環境では画像や GIF を生成しないため、
**ログの own / enemy / threat / actions から軌跡を復元して表示する**。復元式は実測で検証済み
（4機が独立に探知した敵の推定位置が平均 0.07 km で一致した）。

```
enemy_x = own_x + dist * cos(bearing)      # 陣営座標系[km]、x=+ は敵陣方向
enemy_y = own_y + dist * sin(bearing)      # bearing は反時計回りが正
```

```bash
python tools/battle_analyzer/trajectory.py workspace/results_tel/0/log_0.json          # 要約
python tools/battle_analyzer/trajectory.py workspace/results_tel/0/log_0.json --json   # JSON
```

制約（重要）:

- **自作エージェントのログのみ対象**。baseline / BenchMark のログは observation がスカラーで位置を持たない。
- 敵の点は「そのフレームで当該機が探知していた敵」だけ。探知していない敵は表示されない（実位置の復元ではない）。
- 高度はユース部門で固定のため平面表示。`own` が旧 8 列世代のログは残弾・燃料の列が無いため発射イベントを検出できない。
- 発射は残弾数の減少で検出する（`isLaunchableAt()` の都合で射撃指示回数と発射数は一致しない）。

## 提出ルール

- 提出用 specialist は現在 `baseline`。`default`（自作）はローカル評価専用。
- `python tools/signate/cli.py submit ...` は環境変数 `ATLA5_SUBMIT_CONFIRM=1` がないと
  `tools/hooks/pre_submit_gate.py` にブロックされる。
- 詳細は `CLAUDE.md`、ログ仕様は `tools/battle_analyzer/BATTLELOG_FORMAT.md` を参照。
