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

コミット前に Ruff を自動で掛けたい場合は、任意で Lefthook を導入できる（`uv sync && uv run lefthook install`。一度だけ飛ばすときは `LEFTHOOK=0 git commit`）。詳細は [docs/dev/lefthook.md](docs/dev/lefthook.md)。

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
| 改善セッション | **次に打つコマンド**（実行場所つき・大型パネル）と5ステップの現在地、事実カード。読み取り専用 |
| git | ブランチ / 未コミット / ahead-behind / 直近コミット |
| コマンド | 主要コマンドのコピーリスト |
| ルール | コンペルール（採点式・対戦条件・提出ルール・要確認項目）。内容は `tools/state_dashboard/rules.json` |
| 軌跡 | 自作エージェントのログから復元したレーダースコープ再生（後述） |

ダッシュボードは `agent/` の提出物には含まれません（`tools/` は zip 対象外のため）。

## 改善セッションタブ（次に打つコマンドと事実カード）

タブの先頭に **「いま実行するコマンド」** が1つだけ大きく出る。実行場所（PowerShell／エディタ）と、
コマンド内の `<…>`（実際の値に差し替える目印、橙色）を併記し、コピーボタンでそのまま貼れる。
下に並べるのは5ステップの現在地（済 / 次 / 未）。

```
仮説（出所つき） → 1変数だけ変更 → 1戦で挙動確認 → seed 固定ペア評価 → 記録
```

現在地はデータから自動判定する（`session_state.json` の hypotheses / cycles / records、
`git status --porcelain -- agent`、記録は最後の validate より後の新しいものだけ「済」扱い）。

その下に**指標の読み先**（`renderMetricSources`）を 1 行で出す。「どのタブで見るか」だけ画面に出す。
判定は評価タブの `avg_score` / `avg_our_alive` / `avg_enemy_alive`、 時系列は軌跡タブ、
各機の行動はログタブ、採点式と制約はルールタブ。

`--source` は**出所**なので「どこから見たか」で決める（表はチャットに出さない）:

| 指標 | 読む場所 | `--source` |
|---|---|---|
| `avg_score` / `avg_our_alive` / `avg_enemy_alive` / win-draw-loss | 評価タブ / `workspace/paired/<label>.json` | `log`（対戦ログ / 計測値） |
| 初探知・初発射 t / 空白時間 / 発射数 / 消費弾 / 方位分散 | 軌跡タブ / `workspace/results*/**/log_*.json` | `log` |
| 敵探知・射撃指示・被弾警報・最近接距離 | ログタブ / 同上 | `log` |
| 復元式の検証値（一致誤差など） | 軌跡タブ / `tools/battle_analyzer/trajectory.py` | `analysis` |
| 採点式・初期配置・探知距離の制約 | ルールタブ / `workspace/src/fight.py` | `official` |
| `isLaunchableAt` / `maxSimulShot` などの実装制約 | `agent/strategy/agents/escort_hunter.py` | `code` |

その下に**仮説の書き方（立案方針）**（`renderPolicy`）を置き、`tools/state_dashboard/HYPOTHESIS_POLICY.md`
から読む。必ず守ること 8 項目、仮説に使える指標（判定 2 指標 + 補助 4 指標）、
そして現在の状況に合わせた**記入例**を、コピー可能な登録コマンド付きで出す。

#### 仮説ビルダー（選ぶだけで文とコマンドができる）

改善セッションタブ最下部の「仮説ビルダー」は、選ぶだけで仮説の文と
`improvement_session.py hypothesis` のコマンドを組み立てる（読み取り専用・登録はコピーのみ）。

| 欄 | 選ぶと入るのは |
|---|---|
| 事実 | 事実カードの短文（数値つき）。例: 初探知 t=45 に対し初発が t=199（空白 154 秒 / 総発射数 16） |
| 原因 | 既知の制約（`BATTLELOG_FORMAT.md`）から選んだ 1 行 |
| 変数 | 手で 1 変数だけ書く（例: maxSimulShot の上限を 4 → 6） |
| 挙動指標 | 独自指標の現在値 → 目標値（例: 総発射数が 16 発 から 12 発 になる） |
| 判定指標 | 選んだペア評価の `avg_score` / 敵生存（例: default の avg_score 0.235） |
| --source | 事実カードを選ぶと自動で入る（`log` / `analysis` / `code` / `official`） |

- 選択を変えると「組み立てた仮説」とコピーボタンのコマンドが**即時に**再計算される。
- 数値が無い欄は `<…>` のまま残るので、Terminal 側で書き換える。
- 入力欄は手で書き直してよい（選択し直すとその値に戻る）。
- 実行は Terminal に貼り付けるだけ。`--source` は「どこから見たか」なので、
  事実が対戦ログなら `log` のまま使う（実装を読んだ仮説なら `code`）。

### 評価タブの独自指標

評価タブには**自分で定義した指標**（`renderCustomMetrics`）が並ぶ。定義は
`tools/state_dashboard/custom_metrics.json` に集約し、ダッシュボードは読み取り専用なので
`add_metric.py` で追加・更新する。

```bash
# 定義の一覧
python tools/state_dashboard/add_metric.py --list

# 追加（--from が数値の出所、--source が improvement_session.py --source に渡す値）
python tools/state_dashboard/add_metric.py --label "初発までの空白" \
    --from trajectory --direction lower --target 60 --unit 秒 --source log \
    --note "長いほど攻撃機会を逃している"

# 目標値だけ更新 / 削除
python tools/state_dashboard/add_metric.py --id fire_orders --target 80
python tools/state_dashboard/add_metric.py --remove first_launch_lag
```

`--from` で数値の出所を選ぶ。

| --from | 数値 | 読む場所 |
|---|---|---|
| `paired` | `avg_score` / `avg_our_alive` / `avg_enemy_alive` / `win` / `draw` / `loss` / `games` | 評価タブ / `workspace/paired/<label>.json` |
| `trajectory` | `first_detect` / `first_launch` / `first_launch_lag` / `launch_count` / `min_dist_km` / `bearing_spread` / `ammo_used` / `lost_range_km` / `aircraft` | 軌跡タブ / `trajectory.py` |
| `logstats` | `fire_orders` / `enemy_seen` / `alerts` / `min_dist_km` | ログタブ / `battle_stats.py` |

`direction` は `higher`（高いほど良い）か `lower`（低いほど良い）。`target` を省くと参考値扱いで
到達判定しない。表の「判定」列は 到達 / 未達 / 値なし を示す。

その下に**事実カード**（観測された事実だけ）を並べる。読み取り専用で書き込みAPIはなく、
実際の登録は `analysis/tools/improvement_session.py` にコピーしたコマンドで行う。
各カードには「判定指標」と「出典（タブ / ファイル）」を併記する。

| 事実カード | 出所 | 中身 |
|---|---|---|
| ペア評価の差分 | ログ | 最良/最悪の `avg_score`・生存数・対戦数。どこで負けたか |
| 軌跡の時系列 | ログ | 初探知 / 初射撃指示 / 初発射 / 空白時間 / 発射数 / 消費弾 / 方位分散 |
| 最新ログの挙動指標 | ログ | 機体ごとの敵探知・射撃指示・最近接距離（射撃指示と発射は別） |
| 既知の制約 | コード | `BATTLELOG_FORMAT.md` の制約を `assumption` 登録するコマンド付き |
| 採点式 | 公式 | TIMEUP=0.5、0.6+ は撃墜時のみ。目標値の根拠 |

`kind=rule` のカードは `source=official` 固定で、ログ由来の数値と混ぜない。

### validate の判定基準

判定は **seed 固定ペア評価**（`local_test/run_eval_paired.py`）で、`validate.py` を直接叩くと
シナリオが毎回変わるため使わない。ペア評価を実行したら、その JSON をそのまま記録する:

```bash
python analysis/tools/improvement_session.py validate --specialist default \
    --paired workspace/paired/default.json
```

`--paired` を省略すると従来どおり `validate.py` を実行する（非推奨。出力に案内が出る）。

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
