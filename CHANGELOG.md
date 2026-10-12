# CHANGELOG

## 2026-10-11

### 改善サイクル（default specialist、提出物は fr50+break35 のまま）

- N-016〜N-035 を検証。発射量・包絡・温存・配分・前進・接近・離脱の各軸は棄却または閉鎖
- escort 識別の live プローブ：track に spec なし、`truth` は UUID と確定。単フレーム識別は不可能
- UUID 安定性の実測：持続するが duty 7% で運動学的識別は実用困難、経路を保留
- ペア評価の基準値 0-6-0 / 0.500 / our 2.67 / enemy 3.33 を維持

### dashboard（仮説タブ・git タブ）

- 新指標：発射転換率（内訳の自動仮説文付き）、被弾警報フレーム数、全滅戦数、探知duty率（可否の自動判定付き）
- lag 系カードに抑制シェアの自動分岐を追加
- 定期整理ルーティンを確立し、`avg_enemy_alive` と `pre_launch_threat` のカードを除去
- git タブに文書レビュー（文字化け・最新性、コピー釦付き）を追加

## 2026-10-10

### agent: breakRangeKm 35 離脱ルール（default specialist）

- `agent/args.json` に `breakRangeKm: 35.0` を追加
- `default.py`: 敵が 35 km 以内に接近したら敵から 180° 方向へ逃避し、逃避中は射撃を停止
- ペア評価（seeds 1-3 × 両面 = 6戦）: 0勝6分0敗 / avg_score 0.500 / avg_our_alive 2.67 / avg_enemy_alive 3.33

### dashboard: 仮説登録タブの整理（事実確認カード撤去とコピー動作の刷新）

- 独自指標3件（最大進出 x / 護衛対象機への最短距離 / 最終残弾）を追加し、評価タブと metric カードに反映
- trajectory / win_path / logstats の「確認しました」で終わるだけの事実確認カードを仮説登録タブから撤去
- コピー動作を意図で分類（事実確認 / 仮説の材料 / 前提登録 / 仮説登録）
  - 独自指標・条件トリガー・scoring: 「仮説の材料」コピー（値・目標・達成/未達を前提に仮説を1本立てる）
  - constraints（既知の制約）: 前提（assumption）登録のコピー
  - 仮説ビルダー: 仮説登録のコピー