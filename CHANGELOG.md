# CHANGELOG

## 2026-10-26

### CLAUDE.md: ドキュメントとコードが食い違うときの方針

- `CLAUDE.md` に「Documentation vs. code」節を追加: ドキュメントと既存コードが食い違うときは既存コードの慣習に従い、最終返信で見つけた食い違いを1件ずつ挙げる

## 2026-10-25

### コミット前チェック（Lefthook + Ruff、任意導入）

- `lefthook.yml` を追加: pre-commit でステージした `*.py` に `ruff check`、新規追加した `*.py` に `ruff format --check` を並列実行
- `pyproject.toml`: dev 依存に `lefthook` を追加、Ruff の exclude に `docs/pr`・`docs/exp`（証跡スクリプト）を追加。ルールは従来どおり `E`, `F`
- `docs/dev/lefthook.md`: 導入（`uv run lefthook install`）と飛ばし方（`LEFTHOOK=0` / `--no-verify`）

## 2026-10-17

### 護衛対象機の速度識別＋弾温存で ELIMINATION 勝利（default specialist）

- `escort_hunter.py`: 敵観測を5列→6列に拡張（6列目＝目標速度 km/s、`np.linalg.norm(tracks[i].vel())/1000`）
- `default.py`: `escortMaxSpeedKmps`（護衛候補を x≥110km かつ速度≤0.3km/s に限定）と `escortAmmoHold`（護衛対象機が射程内に入るまで発射を保留）を追加
- `args.json`: escortForwardXKm=110, escortFireMode=1, escortMaxSpeedKmps=0.3, escortAmmoHold=1
- ペア評価（seeds1-7×両面=14戦）: win11/draw2/loss1, avg_score 0.616, our_alive 3.0, enemy_alive 4.21 — baseline（0.500）を明確に上回る初の構成
- 護衛対象機への最接近が改善し、到達時の残弾0→6・護衛対象機≤50km での発射0→4/12発となり ELIMINATION を実現

### 発射整列ノブ・変数レジストリ・提出ゲート強化

- `default.py`: beamHoldWhileArmed / beamHoldFrames / fireAlignDeg / launchIntervalFrames / escortForwardXKm / escortFireMode を追加（N-140/141/142 は命中↑・生存↓で net 負けのため既定0で不活性、v2 を維持）
- 指標の誤認を訂正: ペア評価の hit_rate は**勝者のみ**（引き分けは常に0.0、敗戦時は相手の値）。N-140/141/142 の「命中0→改善」は相手が我々を撃墜した数だった（O-164）
- `improvement_session.py`: `--variable` を必須化、`tested-variable` サブコマンドと `tested_variables.json` レジストリを追加、未登録変数の仮説に警告
- `pre_submit_gate.py`: subprocess 出力を utf-8 デコード。uvx 失敗時はローカル ruff にフォールバック（uvx の PyPI DNS 失敗でゲートが不安定だった）
- dashboard: pending / variable_name を単一ソース化、仮説ビルダーが `--variable` を出力。`run_eval_paired.py` に hit_rate を追加
- tests: 141 通過

### 敵戦闘機への反撃＋護衛対象機用ミサイル温存（損失削減）

- `default.py`: `escortReserveMsls` を追加（敵戦闘機には通常反撃しつつ護衛対象機用に N 発を温存、護衛対象機が射程内なら予備も使用）。`escortNoBeam` / `escortIgnoreBreak`（護衛対象機が目標のときビーム・離脱判定を抑制）も追加
- `args.json`: escortAmmoHold=0, escortNoBeam=1, escortIgnoreBreak=1, escortReserveMsls=3
- ペア評価（seeds1-7×両面）: win9/draw5/loss0, avg_score 0.617, our_alive 3.21, enemy_alive 3.5
- Red seed4 の全滅負け（0-5）が反撃により1機生存で引き分けに改善。一方 Blue3/4/7 は護衛対象機撃破に全弾を要するため勝ち→引き分け（avg_score はノイズ範囲でほぼ横ばい）
- `escortReserveMsls` は 2/3/4/5 を走査し 3 を採用（4/5 は Blue4 が負けに転落）
- 上記構成を SIGNATE へ提出

## 2026-10-16

### 護衛対象機への安全接近（escortSeekDistKm、default specialist）

- `default.py`: `escortSeekDistKm=150` を追加（脅威なし・ビーム範囲外・離脱中でないときのみ遠方コンタクトへ旋回。射撃/ビーム/離脱は不変）
- ELIMINATION 4変種（v1-v4: 0.315 / 0.500 / 0.474 / 0.500）を測定し、安全変種（v2）に復帰: 0.500 / 敗戦0 / our_alive 3.67
- `HYPOTHESIS_POLICY.md`: 深掘り由来の仮説を要求し、変数変更なしの validate を禁止
- improvement.md: O-098〜O-102

### breakRangeKm スイープ（未検証仮説の一掃）

- breakRangeKm 25/20/45 を検証: 45 は悪化（avg_score 0.456）、25/20 は 0.500 を維持し生存が微改善。35 を維持
- improvement.md: O-103（N-054〜N-098 の軸を閉鎖）。残る未検証仮説なし（検証済みまたは重複）

## 2026-10-15

### dashboard: 事実カードの深掘りワークフロー（deepen）

- 事実カードを命中指標付きで深掘りする `deepen` ワークフローを `improvement_session.py` に追加
- `custom_metrics.json` に指標を追加し、`serve.py` / `index.html` を更新
- improvement.md: O-095〜O-097（trackConfirmFrames の検証、avg_score 0.500 を維持）

## 2026-10-13

### ベースライン完全復帰・実験コード削除（default specialist）

- 実験コード（護衛対象機識別・hit-and-run・30°ビーム・最遠距離狙い等）を全削除し、純粋なベースライン実装に復帰
- `agent/args.json`: fireRangeKm=50, breakRangeKm=35, marginKm=25 に復帰（実験パラメータ `beamRangeKm` `escortDetectRangeKm` `escortClearRatio` `hitAndRunFrames` 等を削除）
- `default.py`: 80°ビーム@45km・最近接優先・最大速度・evadeCrankDeg 削除の純粋ベースライン実装に復帰
- ペア評価（seeds 1-3 × 両面 = 6戦）: 0勝6分0敗 / avg_score 0.500 / avg_our_alive 3.0 / avg_enemy_alive 3.17 でベースライン確認
- 全実験変種（fireRange 60/80, beamRange 30/40, hit-and-run, 護衛機切替閾値, 最遠距離狙い等）を試し、0.500 を超える改善はなし

### PR #4 マージ・dashboard 更新

- PR #4 本文修正・ヘッダー SHA 更新（bda530b）し、マージ可能状態に
- dashboard: 未試験軸カード自動生成・設計の方向カード追加等

## 2026-10-12

### 改善サイクル（default specialist、提出物は fr50+break35 のまま）

- 護衛対象機軸（N-047/N-048）・守勢軸（N-049/N-049b/N-050）を検証し全敗、棄却・巻き戻し（O-084〜O-087）
- 探知duty率から非探知時の方位を直近の敵方位保持に変える形態（N-051）は交戦を減らし
  avg_enemy_alive 3.33→3.67 と悪化・avg_score 0.500 不変で棄却（O-088）
- ペア評価の基準値 0-6-0 / 0.500 / our 2.67 / enemy 3.33 を維持

### dashboard（仮説タブ・指標整理）

- MWS の被弾警報フレーム数（threat_frames）カードを除去。仕様側センサ約10km固定で
  agent 側の 1 変数では短縮できない（O-083）
- 探知duty率カードと可否の自動分岐を除去。識別可否の条件指標であり単独では改善軸に使わない（O-089）
- 最短交戦距離（min_dist_km）の目標25を解除（参考値化）。接近は引き分けで採点に無関係・
  接近軸は N-029 で閉鎖済み（O-090）

### 開発基盤（CI・ペア評価ハーネス・gitignore）

- ペア評価データの無い環境で `test_session_evidence_paired_card_reflects_metrics` が失敗していたのを、
  件数不足時に `pytest.skip` するガードで修正
- `run_eval_paired.py` の workspace パス解決を `/workspace` 優先にし、コンテナで PYTHONPATH 不要に
- `.gitignore` に `local_test/simulator/`, `local_test/src/`, `baseline_paired_raw.txt`,
  `paired_baseline_raw.txt` を追記

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
## 2026-10-18

- docs: add CHANGELOG entries for 2026-10-15/16/17
- dashboard: reanalyze stranded-ammo card as direction (reserve x early loss); record N-149
- Hold escort fire until 35 km so the reserve is spent at hit range
- Merge pull request #4 from mureee-18/feature/hypothesis-tab-copy
- reject approach-flank geometry: seed4 wins but no net gain (N-164/N-006/N-007)
- reject role-separated flank: two wingmen still cost Blue1's escort (N-008)

## 2026-10-20

- docs: record fireAlignOnlyDeg gate rejection and log key renumbering
- feat: バースト指標と事実カードを追加し見送りカードを整理
- fix: maxSimulShot=1 不採用のため args.json から削除し現行構成を確定
- feat: バースト行動カードと現行構成安定カードを追加
- fix: burstHeadAlignDeg 不採用のため revert し現行構成を確定
- feat: バースト初弾命中0の改善軸を事実カードに整理
- feat: ダッシュボード方向カードにバースト初弾命中0の改善軸を追加し表示整合を確保

## 2026-10-21

- feat: card_fill.json の事実カードを動的 evidence に追加しダッシュボード表示を確保
- feat: バースト初弾命中0の改善軸を3枚の事実カードに整理
- feat: 動き・射撃対象選定・護衛接近の事実カードを追加
- fix: metric:target_selection を仮想登録可能に
- fix: 事実カードを未処理3枚に集約し見送りをゼロに
- fix: escort_approach_dist 不採用のため revert し現行構成を確定
- fix: dashboard verification tab showing already-verified hypotheses
- fix: dashboard pending hypothesis logic

## 2026-10-22

- fix: set variable_name on open fact cards to stop placeholder in dashboard hypothesis button
- docs: codify dashboard 2-instruction rule (implementation belongs to verify flow)
- feat: verify tab emits full implement->deploy->gate->paired->validate->record command chain
- fix: verify tab step 5/6 bind --hypothesis to selected id so pending clears
- fix: prune pending of tried-axis and same-variable duplicates

## 2026-10-23

- fix: pending drops same-variable old duplicates when a var is validated
- feat: verify tab step 1 (implement) becomes a copy button like the other rows
- fix: protect card_fill open/direction variables from pending exclusion
- fix: allow re-registering open/direction card variables in hypothesis
- fix: pending protects only open-card variables, not direction cards
- fix: stop hypothesis re-registration loop and close exhausted approach axis
- docs: record escort_approach_dist verification result (N-190, O-185)
- fix: verify tab record command uses valid kind/source values
- fix: target_selection_rule rejected, close selection axis (O-187, N-193)
- fix: evade_beam_break_timing=3 rejected, close evasion-direction axis (O-188, N-192)
- fix: hit_count 軸の再検証で外れ量の機構を特定し軸を閉鎖 (O-189, N-159)
- fix: dashboard fact-card rendering and test expectations
- feat: add agents tab showing the submission package contents
- feat: show agent package files as a directory tree
- feat: add observation/decision/action tab and config.json view
- refactor: split decision trace into separate observation/decision/action modules
- chore: remove superseded single-file decision_trace.py

## 2026-10-24

- fix: show the real submission package (zip) contents and correct the source heading
- fix: derive package contents and firing thresholds from data instead of hard-coding
- Merge remote-tracking branch 'origin/master' into feature/hypothesis-tab-copy
- refactor: split dashboard JavaScript into per-tab modules and fix asset serving

