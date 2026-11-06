# CLAUDE.md

## What this is

SIGNATE「第5回空戦AIチャレンジ」**ユース部門**（第5回 = R8）向けのエージェント開発リポジトリ。
提出物は「行動判断を行う Python モジュールを zip にまとめたもの」で、評価システムは
x86 CPU・Linux 上で初期行動判断モデル（BenchMark）と対戦させる。

- コンペ: https://user.competition.signate.jp/ja/competition/detail/?competition=42024ceef5064aa6a7f463aac3f26fc2&task=5564d022dac44dd498c97aa82efab260
- タスク（ユース部門）: `5564d022dac44dd498c97aa82efab260`

## Anti-Regression Rules (CRITICAL — これを破る変更はバグとみなす)

1. **提出されるのは `agent/` を zip 化した1モジュールのみ。** 提出用 specialist は現在 `default`
   （自作ルールベース。seeds1-5×両面の10戦ペア評価で avg_score 0.500 ＝ `baseline` と同値、
   敗戦0（10/10 引き分け）だったため 2026-10-07 に切り替え）。
   `tools/hooks/pre_submit_gate.py` が `args.json` の `specialist` を検証し、
   `baseline` / `default` のいずれでもないもの（ローカル評価専用の実験）は弾く。
2. **提出はユーザーの明示指示がある時のみ。** `signate submit` は環境変数
   `ATLA5_SUBMIT_CONFIRM=1` 付きで実行する（ゲートが無指示の提出をブロック）。
3. **スタンドアロンな実装を増やさない。** Agent 本体は `agent/strategy/agents/`、
   方針は `agent/strategy/specialists/`、`active.py` は switchboard として薄く保つ。
4. **ログ構造を毎回調べ直さない。** 改善セッション開始時に
   `tools/battle_analyzer/BATTLELOG_FORMAT.md` を必ず読む。
5. **改善は1因果メカニズムずつ。** 同一メカニズムに属する複数ノブの同時変更は可（例: 射撃整列 = fireAlignDeg + beamHoldFrames）。無関係なメカニズムを同時に変えると、悪化時に原因を切り分けられない。
6. **可視化はログ再構築のみ。** 公式ビューア（`visualize=1`）は headless で画像/GIFを
   生成せず、`env.manager` の生状態は `getEntityByName` で core dump するため使わない。
   軌跡は `tools/battle_analyzer/trajectory.py` の復元式
   （`enemy = own + dist·(cos bearing, sin bearing)`、陣営座標系 x=+ が敵陣方向）を正とする。

## Documentation vs. code

When a repository's documentation and its existing code disagree, follow the conventions used in the existing code, and in your final reply point out each inconsistency you found between the documentation and the code.

## Environment

| 役割 | 内容 |
|---|---|
| 実行環境 | Docker Desktop（WSL2）上の `atla5-cpu` / `atla5-gpu` コンテナ（`docker-compose.yml`） |
| コンテナ | Ubuntu 22.04 / Python 3.10 / torch 2.7.0 / TF 2.13.0 / ray 2.46.0 / ASRCAISim1 2.0.1 |
| マウント | `./workspace → /workspace`（配布シミュレータ本体）、リポジトリルート `→ /repo` |
| ホスト | Windows。配布データは `data/`、展開先は `workspace/`（いずれも gitignore） |

`workspace/` と `data/`、`submission/` はコミットしない。

## Commands

```bash
# コンテナ起動 / 停止
docker compose up -d cpu
docker compose down

# 提出物のビルド（submission/submit.zip）+ workspace/Agents/MyAgent への配置
python scripts/build_submission.py --deploy

# ローカル対戦（ユース部門・BenchMark 相手）
docker exec atla5-cpu bash -lc "cd /workspace && python validate.py --youth 1 --num-validation 3 --visualize 0"

# 3戦の集計・パラメータ走査
python scripts/run_eval.py --games 3
python scripts/run_eval.py --games 3 --sweep fireRangeKm=25,35,50

# seed 固定ペア評価（同一 seed 群で A/B を比較。判断はこれを基準にする）
docker exec atla5-cpu bash -lc "cd /workspace && python /repo/local_test/run_eval_paired.py --seeds 1,2,3 --colors both --label baseline --out /workspace/paired/baseline.json"

# 対戦ログの整理（dry-run が既定）
python tools/log_cleanup/cleanup.py --keep 3

# 1戦のログから挙動指標
python tools/battle_analyzer/battle_stats.py workspace/results/0/log_0.json

# 1戦のログから軌跡を復元（自作エージェントのログのみ。ダッシュボードの「軌跡」タブでも再生）
python tools/battle_analyzer/trajectory.py workspace/results_tel/0/log_0.json

# 開発状況ダッシュボード（環境・提出可否・ペア評価・ログ・軌跡・git を1画面）
# 改善セッションタブは読み取り専用。事実カード・指標の出典表・仮説立案方針とコピー用コマンドだけを出す（書き込みはしない）
# 仮説はタブ最下部の「仮説ビルダー」で事実/原因/変数/指標を選ぶと文と hypothesis コマンドができる（コピーして Terminal で実行）
# 評価タブの独自指標は tools/state_dashboard/custom_metrics.json に定義し、add_metric.py で追加・更新する
python tools/state_dashboard/serve.py --open
python tools/state_dashboard/serve.py --once   # JSON を標準出力（CI/スクリプト用）
python tools/state_dashboard/cache_bump.py     # ブラウザのキャッシュを確実に飛ばす

# 開発環境の定期点検（dashboard / Docker / git / JSON / 空き容量 → analysis/ops/heartbeat.log）
python tools/ops/healthcheck.py
python tools/ops/healthcheck.py --restart     # 明示したときだけ dashboard を再起動

# 提出zipの単体検証（展開して4関数を呼ぶ）
docker exec atla5-cpu bash -lc "python /repo/scripts/zip_check.py /repo/submission/submit.zip"

# SIGNATE CLI（competition_key / task_key は tools/signate/config.json に固定済み）
python tools/signate/cli.py files
python tools/signate/cli.py submit submission/submit.zip --memo "..."

# テスト・lint（CI と同じ）
pytest tests/ -q
ruff check agent/ tools/ tests/ scripts/

# 改善セッション（記録は「種別＋出所」の型制約つき。kind=rule は source=official のみ）
python analysis/tools/improvement_session.py start --specialist default
python analysis/tools/improvement_session.py hypothesis "..." --specialist default --source log
python analysis/tools/improvement_session.py verify --specialist default --games 1
# 判定はペア評価。validate --paired はその JSON を validate サイクルとして記録するだけ
python analysis/tools/improvement_session.py validate --specialist default \
    --paired workspace/paired/default.json
python analysis/tools/improvement_session.py record --specialist default \
    --kind observation --source log \
    --direction "..." --changes "..." --verification "..." --next-steps "..."
```

## Architecture

```
agent/
├── __init__.py              提出エントリ（必須4関数）→ strategy.active に委譲
├── args.json                4関数に渡る引数。`specialist` で使用方針を切替
├── config.json              modelConfig（specialist ごとにセクションを分ける）
└── strategy/
    ├── active.py            switchboard: specialist の選択と modelConfig の解決
    ├── agents/              Agent クラス本体（S方式: 1機に1エージェント）
    │   └── escort_hunter.py makeObs / deploy / control
    └── specialists/         方針（Policy）と Agent クラスの組
        ├── baseline.py      比較基準: 配布の初期行動判断モデル BasicAACRuleBasedAgent01
        └── default.py      提出用: 自作ルールベース Policy（ビーム機動＋境界回避）
```

提出に必須の4関数: `getUserAgentClass` / `getUserAgentModelConfig` /
`isUserAgentSingleAsset` / `getUserPolicy`。
zip のルートに `__init__.py`・`args.json`・`config.json` が必要（それ以外は自由）。

提出物に含まれるのは `agent/` 配下のみ。`tools/`・`scripts/`・`local_test/`・
`analysis/`・`tests/` は開発用で zip には入らない。

開発状況の可視化:

```
tools/
├── signate/                SIGNATE CLI ラッパー（config.json に key 固定）
├── hooks/                  提出前ゲート（明示確認・specialist・zip・ruff）
├── battle_analyzer/        ログ仕様書 BATTLELOG_FORMAT.md / battle_stats.py / trajectory.py（軌跡復元）
├── log_cleanup/            ログの世代管理（dry-run 既定）
├── ops/                    定期ヘルスチェック（heartbeat.log は analysis/ops/ Exclude）
└── state_dashboard/        開発状況ダッシュボード（serve.py / index.html / cache_bump.py）
    ├── custom_metrics.json  評価タブの独自指標定義（add_metric.py で追加・更新）
    └── HYPOTHESIS_POLICY.md 仮説の立案方針（セッションタブに描画する）
```

## 改善の進め方（実測済みの前提）

- 判定は**勝率ではなく挙動指標**: `avg_score`（自陣営スコアの平均）、
  `avg_our_alive`（生存機数）、`avg_enemy_alive`（敵の生存機数＝減らせているか）。
  3戦でもノイズは大きいが、全滅（0.23）と互角（0.5〜0.6）は明確に区別できる。
- **A/B 比較は必ず seed 固定ペア評価で行う**（`local_test/run_eval_paired.py`）。
  `validate.py` は毎回シナリオが変わるため、通常の3戦比較は当てにならない。
  ペア評価では same seed 群 + Red/Blue 両面で比較するのが基本。
  再現性は「`match_config["seed"]` + グローバル RNG の seed」の両方を揃えて初めて得られる
  （初期配置と護衛対象機の周回方向が `np.random` を直接使うため）。実測: seed 7 を2回実行して完全一致。
- 変更前の流れ: `hypothesis` で数値予測を記録 → **実装** → 1戦で挙動確認 → ペア評価で指標比較 → `record` で記録。
- 実績（同一 seed 1,2,3 × 両面 = 6戦）
  - `baseline`: win1 / draw4 / loss1、avg_score 0.500、avg_our_alive 2.50、avg_enemy_alive 2.50 … **提出中**
  - `default`（自作）: win0 / draw0 / loss6、avg_score 0.233、avg_our_alive 0.00、avg_enemy_alive 4.17
- 自作 Agent が負ける主因: `/sensor/track` に spec が無く護衛対象機を識別できないこと、
  MWS の探知距離が短く回避が間に合わないこと。詳細は BATTLELOG_FORMAT.md の「既知の制約」。

## ダッシュボードからの2指示（原則・CRITICAL）

ユーザーはダッシュボードから **2種類だけ** の指示を出す。AIはこれ以外を要求したり「実装するか？」と尋ねたりしない。

1. **事実カード → 仮説登録**（`card_fill.json` の open/direction カードの「仮説登録」ボタンが生成する `improvement_session.py hypothesis ...`）
   - この段階は**登録のみ**。実装しない。pending に仮説が積まれるだけ。
2. **仮説 → 検証**（検証タブで仮説を選ぶと生成される一連コマンド）
   - **実装はこの指示に含める**。順序:
     ①`args.json`/`default.py` に対象メカニズムを**1つだけ実装**（同一メカニズム内の複数ノブを含めてよい） →
     ②`build_submission.py --deploy` →
     ③1戦ゲート（`validate.py --num-validation 1`。悪化なら即 revert）→
     ④seed固定ペア評価（`run_eval_paired.py --label <変数label>`）→
     ⑤`improvement_session.py validate --paired ...` で仮説IDと紐付け消化 →
     ⑥`record` で記録。

### 実装の归属＝検証側（確定ルール）

- 検証は「変数を実装した後」の挙動を測る工程なので、実装・デプロイ・revert は検証フローの一部。
- 現行構成の `default.json` を validate しても pending は消化されない（仮説IDが紐付かないため）。
  pending を消すには「実装 → その label でペア評価 → validate」まで行う。
- 「実装するか？」「どちらのカードから？」といった選択の質問い返しは禁止。
  事実カード・仮説の選択はユーザーがダッシュボードで行う。AIは受けた指示を実行して結果を報告するのみ。
- 複数カードの仮説登録を繰り返して pending が累加するループを避けるため、
  検証指示が来たら必ず上記①〜⑥まで完走して pending を消化する。
