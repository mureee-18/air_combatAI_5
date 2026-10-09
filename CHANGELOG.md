# CHANGELOG

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