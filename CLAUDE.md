# CLAUDE.md

## What this is

SIGNATE「第5回空戦AIチャレンジ」**ユース部門**（第5回 = R8）向けのエージェント開発リポジトリ。
提出物は「行動判断を行う Python モジュールを zip にまとめたもの」で、評価システムは
x86 CPU・Linux 上で初期行動判断モデル（BenchMark）と対戦させる。

- コンペ: https://user.competition.signate.jp/ja/competition/detail/?competition=42024ceef5064aa6a7f463aac3f26fc2&task=5564d022dac44dd498c97aa82efab260
- タスク（ユース部門）: `5564d022dac44dd498c97aa82efab260`

## Anti-Regression Rules (CRITICAL — これを破る変更はバグとみなす)

1. **提出されるのは `agent/` を zip 化した1モジュールのみ。** 提出用 specialist は現在 `baseline`。
   `default`（自作ルールベース）はローカル評価専用で、**絶対に提出してはならない**。
   `tools/hooks/pre_submit_gate.py` が `args.json` の `specialist` を検証して弾く。
2. **提出はユーザーの明示指示がある時のみ。** `signate submit` は環境変数
   `ATLA5_SUBMIT_CONFIRM=1` 付きで実行する（ゲートが無指示の提出をブロック）。
3. **スタンドアロンな実装を増やさない。** Agent 本体は `agent/strategy/agents/`、
   方針は `agent/strategy/specialists/`、`active.py` は switchboard として薄く保つ。
4. **ログ構造を毎回調べ直さない。** 改善セッション開始時に
   `tools/battle_analyzer/BATTLELOG_FORMAT.md` を必ず読む。
5. **改善は1変数ずつ。** 複数の変更を同時に入れたら、悪化時に原因を切り分けられない。

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

# 提出zipの単体検証（展開して4関数を呼ぶ）
docker exec atla5-cpu bash -lc "python /repo/scripts/zip_check.py /repo/submission/submit.zip"

# SIGNATE CLI（competition_key / task_key は tools/signate/config.json に固定済み）
python tools/signate/cli.py files
python tools/signate/cli.py submit submission/submit.zip --memo "..."

# テスト・lint（CI と同じ）
pytest tests/ -q
ruff check agent/ tools/ tests/ scripts/

# 改善セッション
python analysis/tools/improvement_session.py start --specialist default
python analysis/tools/improvement_session.py hypothesis "..." --specialist default
python analysis/tools/improvement_session.py verify --specialist default
python analysis/tools/improvement_session.py validate --specialist default --games 3
python analysis/tools/improvement_session.py record --specialist default --direction "..." --changes "..." --verification "..." --next-steps "..."
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
        ├── baseline.py      提出用: 配布の初期行動判断モデル BasicAACRuleBasedAgent01
        └── default.py      ローカル評価用: 自作ルールベース Policy
```

提出に必須の4関数: `getUserAgentClass` / `getUserAgentModelConfig` /
`isUserAgentSingleAsset` / `getUserPolicy`。
zip のルートに `__init__.py`・`args.json`・`config.json` が必要（それ以外は自由）。

## 改善の進め方（実測済みの前提）

- 判定は**勝率ではなく挙動指標**: `avg_score`（自陣営スコアの平均）、
  `avg_our_alive`（生存機数）、`avg_enemy_alive`（敵の生存機数＝減らせているか）。
  3戦でもノイズは大きいが、全滅（0.23）と互角（0.5〜0.6）は明確に区別できる。
- **A/B 比較は必ず seed 固定ペア評価で行う**（`local_test/run_eval_paired.py`）。
  `validate.py` は毎回シナリオが変わるため、通常の3戦比較は当てにならない。
  ペア評価では same seed 群 + Red/Blue 両面で比較するのが基本。
  再現性は「`match_config["seed"]` + グローバル RNG の seed」の両方を揃えて初めて得られる
  （初期配置と護衛対象機の周回方向が `np.random` を直接使うため）。実測: seed 7 を2回実行して完全一致。
- 変更前の流れ: `hypothesis` で数値予測を記録 → 1戦で挙動確認 → ペア評価で指標比較 → `record` で記録。
- 実績（同一 seed 1,2,3 × 両面 = 6戦）
  - `baseline`: win1 / draw4 / loss1、avg_score 0.500、avg_our_alive 2.50、avg_enemy_alive 2.50 … **提出中**
  - `default`（自作）: win0 / draw0 / loss6、avg_score 0.233、avg_our_alive 0.00、avg_enemy_alive 4.17
- 自作 Agent が負ける主因: `/sensor/track` に spec が無く護衛対象機を識別できないこと、
  MWS の探知距離が短く回避が間に合わないこと。詳細は BATTLELOG_FORMAT.md の「既知の制約」。
