
## O-001 [observation/log] 2026-10-03T11:07:17
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: maxSimulShot 2→4 で発射数が 8 発から 15〜16 発に増加した。しかしペア評価は avg_score 0.235 / 自機生存 0.0 / 敵生存 3.33 で 6 戦とも全滅で、判定指標は改善せず。初発までの空白は 154 秒で、maxSimulShot は主因ではない（比較したログは初期探知 t が 17 と 45 でシナリオが異なり、空白の直接比較はできない）。
- 変更: agent/config.json の Fixed.maxSimulShot を 2 から 4 に変更（default 専用セクション。baseline は Baseline.Fixed を使うため提出物には影響なし）。検証のため agent/args.json の specialist を baseline→default に切替。
- 検証: 発射数 8 発（results_tel）→ 15 発（results/0）・16 発（results_improve/0）で launch イベントを実測。ペア評価 seeds1,2,3×両面: 前 avg_enemy_alive 4.17→後 3.33（敵を1機倒せるようになったが自機は全滅）。avg_score 0.233→0.235 は誤差範囲。1戦検証: ELIMINATION / 自機 0 / 敵 4。
- 指標: {"avg_score": 0.235, "avg_our_alive": 0.0, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 自機全滅が未解決。弾数を増やしても生存は変わらないので、次は回避を1変数で変える。候補は EscortHunterAgent.control() の回避方位（被弾警報方位+180度 の固定）と MWS 警報の距離依存の扱い。1変数ずつ試す。

## O-002 [observation/log] 2026-10-03T12:03:41
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 初発までの空白 154→60 を目指す
- 変更: （未実装）仮説のみ登録
- 検証: 1戦で動作確認済みだがペア評価は avg_score 0.233 / 敵生存 4.17。効果未定。
- 指標: {"avg_score": 0.233, "avg_our_alive": 0.0, "avg_enemy_alive": 4.17, "games": 6}
- 次の一手: maxSimulShot 等の1変数を実際に変更して verify/validate を回す

## O-003 [observation/log] 2026-10-06T21:45:17
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避方位を threat[1]+180（逃走）から threat[1]+90（ビーム）に変更すれば、6〜9秒の警報窓でも生存が改善すると予測
- 変更: DefaultPolicy.step の被弾警報時 desiredAz を threat[1]+180 → +90 に変更（1変数）
- 検証: 1戦: score 0.238 / 敵3.0。ペア評価 seeds1,2,3×両面=6戦: avg_score 0.235→0.233, avg_our_alive 0.0→0.0(不変), avg_enemy_alive 3.33→3.5。改善なし（微悪・誤差範囲）。仮説棄却、変更は巻き戻し済み。
- 指標: {"avg_score": 0.233, "avg_our_alive": 0.0, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: MWS警報は6〜9秒窓で回避方位の変更では生存できない。次は交戦前の位置取り（進入角・交戦射程・離脱判断）を1変数で検証

## O-004 [observation/log] 2026-10-07T15:54:30
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避方位を threat[1]+180（真後ろ）から +90（ビーム機動）へ変更し、被弾を減らせるか検証
- 仮説: N-004
- 変更: agent/strategy/specialists/default.py の desiredAz を threat[1]+180 → threat[1]+90 に変更（検証後に巻き戻し済み）
- 検証: seed1,2,3×両面=6戦。avg_score 0.233 / avg_our_alive 0.0 / avg_enemy_alive 3.5（変更前 0.235 / 0.0 / 3.33）。予測(our_alive1.0以上, enemy3.0前後, score0.30以上)に対し改善なし・やや悪化。棄却
- 指標: {"avg_score": 0.233, "avg_our_alive": 0.0, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 回避は棄却。交戦前の位置取り（進入角・交戦射程・離脱判断）を1変数で検証

## O-005 [observation/log] 2026-10-07T18:33:14
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: maxSimulShot 4→6 では発射数・生存・敵生存のいずれも変化せず（0.235/0.0/3.33 のまま）。default は同時飛翔が6発に届かず、上限を上げても効かない。
- 仮説: N-005
- 変更: agent/config.json の Fixed.maxSimulShot を 4 から 6 に変更（default 専用セクション。baseline は Baseline.Fixed を読むため提出物には影響なし）。検証後に巻き戻し済み。
- 検証: ペア評価 seeds1,2,3×両面=6戦: 変更前 avg_score 0.235 / 自機 0.0 / 敵 3.33 → 変更後 0.235 / 0.0 / 3.33（完全一致・6戦全滅）。1戦検証: ELIMINATION / 自機0 / 敵5。
- 指標: {"avg_score": 0.238, "avg_our_alive": 0.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: 弾数系は棄却。自機全滅が未解決。次は接敵ジオメトリ（engageRangeKm / fireRangeKm / marginKm）を1変数で変えるか、ログで被弾位置を特定してから試す。
- validate（2026-10-08, 6戦ペア評価, session_state.cycles に記録）: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
## O-006 [observation/log] 2026-10-07T19:40:36
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 目標45km以内でビーム機動(方位+80度)に切替えると、直進突撃より交差目標となり生存が大幅改善（avg_score 0.235→0.472、自機生存 0.0→2.3、draw 8/10）。baseline の 0.5 に接近。
- 仮説: N-006
- 変更: DefaultPolicy に beamRangeKm を追加。最近敵との距離が beamRangeKm 以下なら desiredAz = 敵方位+80度（KEEP_SENSING相当）。beamRangeKm=45 をコード既定値に採用（args で上書き可）。
- 検証: seed1-5×両面=10戦のペア評価。変更前(beamなし) 0.235/0.0/3.33 → beam45 0.472/2.3/3.3。値走査: beam40 0.34/0.4、beam45 0.472/2.3、beam50 0.433/3.6。45が最良。コード既定（args上書きなし）でも 0.472 を再現。
- 指標: {"avg_score": 0.238, "avg_our_alive": 0.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: 生存は改善したが敵生存3.3が動かない（キルが増えない）。次はビーム角度/左右振り分け（味方と間隔を取る）、または残存時の追撃・交戦射程を1変数で検証。
- validate（2026-10-08, 6戦ペア評価, session_state.cycles に記録）: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
## O-007 [observation/log] 2026-10-07T20:19:37
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: ビーム角度を80度から変更しても改善せず。60度 0.426 / 90度 0.438 / 100度 0.443 で、80度(0.472)が最良。baseline の thetaKeepSensing=10度(=80度) と一致。
- 変更: beamAngleDeg を引数化して走査（検証後に巻き戻し。コードは +80度固定のまま）。
- 検証: seed1-5×両面=10戦ペア評価。beamRange=45固定で角度60/90/100を比較。いずれも80度に劣る。
- 指標: {"avg_score": 0.238, "avg_our_alive": 0.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: 角度軸は棄却。生存は確保できた(0.472)が敵生存3.3が動かない=キルが増えない。次は味方との間隔確保（ビーム左右の振り分け）か、残存時の再接近・追撃を1変数で検証。

## O-008 [observation/log] 2026-10-07T20:31:22
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: ビーム左右を機体ごとに振り分けると悪化（avg_score 0.472→0.379、自機生存 2.3→1.3）。4機が同じ側にビームする方が良い。味方と探知/弾が集中する方が命中・生存に有利。
- 変更: beamSplit 引数を追加し、機体名のハッシュ偶奇で ±80度に振り分け（検証後に巻き戻し）。
- 検証: seed1-5×両面=10戦ペア評価。beam45・振り分けなし 0.472/2.3/3.3 → 振り分けあり 0.379/1.3/3.8。悪化。
- 指標: {"avg_score": 0.238, "avg_our_alive": 0.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: 振り分けは棄却。次は残存時の再接近・追撃（ビームで距離を取った後に敵が離れたら再度寄って撃つ）を1変数で検証。または交戦射程/発射タイミングの再検討。

## O-009 [observation/log] 2026-10-07T21:27:07
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 境界回避の余裕 marginKm を 25→35/45 に変えても結果は完全に同一(0.472)。PENALTY 時は既に marginFront<marginKm が成立しており閾値変更は無効。PENALTY の実体は防衛ライン dLine=150km 越えの前進（seed2 Red で x=148〜164km、own[6]=1.9/-12.3/-14.1）。
- 変更: marginKm を走査（検証後に巻き戻し。コードは既定 25 のまま）。
- 検証: seed1-5×両面=10戦ペア評価。margin25/35/45 すべて 0.472/2.3/3.3 で同一。seed2 を再現しログ解析で越境を確認。
- 指標: {"avg_score": 0.238, "avg_our_alive": 0.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: 境界は ±90度旋回では戻せない。回避角度を強める（後退成分を持たせる）方向を1変数で検証。

## O-010 [observation/log] 2026-10-07T21:27:07
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 境界回避の旋回角を 90→120度 に強めると、越境 PENALTY が消え avg_score 0.472→0.500（10戦全引き分け・敗北0）。baseline と並ぶ。
- 仮説: N-007
- 変更: DefaultPolicy の marginFront 回避角を引数 marginAzDeg 化し既定 90→120 に変更（後退成分を持たせ早期に戻す）。
- 検証: seed1-5×両面=10戦。marginAz90 0.472/2.3/3.3(2敗PENALTY) → maz120 0.500/2.3/3.3(0敗)。maz150 も 0.500。コード既定(120)でも 0.500 を再現。
- 指標: {"avg_score": 0.238, "avg_our_alive": 0.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: 敗北0・引き分け固定（TIMEUP）。次はキル数増で勝ち越しを狙う（敵生存3.3）。交戦射程/発射タイミング、または敌護衛機への到達を1変数で検証。
- validate（2026-10-08, 6戦ペア評価, session_state.cycles に記録）: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
## O-011 [observation/log] 2026-10-07T22:49:02
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: ビーム＋境界回避導入後に fireRangeKm を再走査しても 50km が最良（30:0.416 / 40:0.396 / 50:0.500 / 60:0.421）。発射は 50km 維持が正しい。
- 変更: fireRangeKm を走査（コード変更なし。args で上書きして比較）。
- 検証: seed1-5×両面=10戦ペア評価。fireRange50(既定) 0.500/2.3/3.3 が最良、30/40/60 は 0.396〜0.421 で悪化。
- 指標: {"avg_score": 0.238, "avg_our_alive": 0.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: 射程軸も 50 が最適。キル数増には発射数・同時飛翔/目標選択の工夫が必要。ビーム離脱→再突入周期や敵護衛機到達を1変数で検証。

## O-012 [observation/log] 2026-10-07T23:03:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: ビーム離脱→再突入サイクルは効果なし（周期60s・突撃比0.3で 0.500 と同一、突撃比0.5では 0.395 に悪化）。敵に寄るとキルは増えず被弾だけ増える（fr30/40の結果と整合）。
- 変更: cyclePeriodS/attackFraction 引数を追加し周期突撃を実装（検証後に巻き戻し。コードは既定 off）。
- 検証: seed1-5×両面=10戦ペア評価。p60/af0.3 0.500/2.3/3.3（同一）、p60/af0.5 0.395/1.3/3.8（悪化）。
- 指標: {"avg_score": 0.238, "avg_our_alive": 0.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: キル数は突撃では伸びない。現状は baseline 同等(0.500)で引き分けが上限。勝ち越しには敵護衛機の識別/狙撃（/sensor/track に spec 無しで不可）など根本制約の克服が必要。一旦停止して他方向（レーダー/探知活用）を検討。

## O-013 [observation/log] 2026-10-07T23:20:45
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 遠方レーン(>=100km)を護衛機候補として優先追撃すると壊滅（avg_score 0.234・全6敗・自機生存 0.0）。近くの戦闘機を無視して突入するため被弾が増えるだけ。
- 変更: escortFarKm 引数を追加し、distance>=escortFarKm の航跡を最優先で方位/目標に採用（検証後に巻き戻し）。
- 検証: seed1,2,3×両面=6戦ペア評価。 escortFarKm=0(既定) 0.500/2.67/3.33 → 100 で 0.234/0.0/4.0。
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 遠方優先は棄却。護衛機の識別が壁。近接戦闘機の回避を維持したまま、射程内にいる航跡のうち最も遠いものを撃つ（射撃対象のみ差し替え）など、方位と射撃対象を分離する方式を試す。

## O-014 [observation/log] 2026-10-07T23:32:31
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 射撃対象のみ射程内最遠（護衛機候補）に差し替えても悪化（0.500→0.447、ELIMINATION 2敗増）。旋回・ビームは維持しても、遠方照準に変えた際に seeds4,5 Red で全滅。
- 変更: fireFar 引数を追加し、射程内の航跡のうち最遠を target に採用（検証後に巻き戻し）。
- 検証: seed1,2,3×両面=6戦は 0.500/3.33/3.0 と見かけ上改善したが、seed1-5×両面=10戦では 0.447/2.5/3.0・draw8/loss2 で既定 0.500/2.3/3.3・draw10 を下回る。小さサンプルの誤差だった。
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 射撃対象の遠距離化は棄却。護衛機撃墜は現状の観測では困難。0.500 を維持しつつ勝ち越しを得るにはより深い変更が必要。他セッション/別方向へ移るか、HELD。

## O-015 [observation/log] 2026-10-08T20:25:06
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 戦場俯瞰タブで両軍を常時見えるようにする。予測は使わず、ローカル対戦時にログへ記録する敵の絶対座標で補う（提出物のログ出力は増やさない）。
- 仮説: N-008
- 変更: local_test/battle_recorder.py を新設（敵5機を自陣フレームkmへ変換、方位はposとpos_prevの2点実測からの進路）。workspace/src/fight.py に record_enemies フック＋gen_log.py で有効化（観測が付くフレームにのみ enemies_direct を追記）。trajectory.py は enemies_direct を優先して teams に採用（source:direct、alive=falseは除外）、無記録ログは従来のセンサ融合へフォールバック。index.html は敵個体ID・出所表示に変更、BATTLELOG_FORMAT.md に3.3節を追記。
- 検証: 敵0機フレーム 272/1800 → 0/1800（Red/Blue双方の実戦ログで1800/1800に記録、撃墜後はalive=falseで除外）。pytest 93 passed / ruff clean / serve --once exit 0。verify --games 1 は TIMEUP score 0.500・接近/射撃/回避の挙動維持、記録の無いログは「推定」表示にフォールバックを確認。
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 4.0, "games": 1}
- 次の一手: run_eval_paired のログにも記録を有効化しペア評価時の俯瞰も絶対座標化する。提出前に agent/ 無変更を pre_submit_gate で再確認。

## O-016 [observation/log] 2026-10-08T21:13:45
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: fireRangeKm を 50→25 にして最短交戦距離を 25km 以下に詰め、交戦の質を上げる（N-009）。
- 仮説: N-009
- 変更: agent/args.json の fireRangeKm 50.0→25.0 のみ（1変数）、scripts/build_submission.py --deploy で workspace/Agents/MyAgent へ反映。
- 検証: 1戦 verify: min_dist 30.6→14.4/14.8km（25km以下 達成）、ELIMINATION 勝ち score 0.659。ペア評価(seeds1-3×両面): avg_score 0.500→0.504、avg_our_alive 2.67→2.83、avg_enemy_alive 3.33→2.83、win 0→2 / loss 0→1（Red seed3 の 624steps 全滅が唯一の敗）。
- 指標: {"avg_score": 0.504, "avg_our_alive": 2.83, "avg_enemy_alive": 2.83, "games": 6}
- 次の一手: seeds を増やして有意性確認。採用（コミット）か戻すかはユーザー判断待ち。

## O-017 [observation/log] 2026-10-08T21:29:35
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-009 (fireRangeKm 50→25) を seeds1-5×両面10戦で両腕比較し採否を判定する。
- 仮説: N-009
- 変更: 検証時だけ agent/args.json を fireRangeKm 25.0 にして実行、判定後に 50.0 へ復元（deploy も fr50 に戻した。リポジトリ差分なし）。
- 検証: fr50: 0勝10分0敗 avg_score 0.500 自機生存2.3 敵生存3.3 / fr25: 3勝3分4敗 avg_score 0.442 自機生存2.1 敵生存3.3。交戦距離の予測(≤25km)は14km台で達成も、判定指標 avg_score は悪化し敗戦が4件発生。seeds4,5 でリスク顕在化。
- 指標: {"avg_score": 0.442, "avg_our_alive": 2.1, "avg_enemy_alive": 3.3, "games": 10}
- 次の一手: N-009 は不採用（fr50 維持）。fr25 は勝ち筋もあるため、敗戦局面(Red seed3 等)のログ解析で条件を絞ってから再検討。

## N-001 [inference/log] 2026-10-08T21:40:55
- 種別: inference（仮説・推論）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-009(fr25) が負けた局面と勝てる局面の条件を、同 seed の fr50/fr25 ログ対比で特定する。
- 仮説: N-009
- 変更: 実装変更なし（検証用ログ6本を生成: results_f50s3-5 / results_f25s3-5、args は fr50 復元済み）。
- 検証: fr25 敗局の共通点: fire_orders 0〜3（fr50 同 seed は 42〜756）、min_rmsls 5〜6 発を持ったまま被弾のみで全滅(364-540steps)。seed3 は min_dist 39.9km まで一切近接せず。射撃ゲート(距離≤25km かつ threat<0.5)が閉じたまま先制を受け続けたのが機序。fr50 は 50km から相互射撃→牽制→引き分け生存。fr25 の勝ち筋は開幕ジオメトリで敵初撃が外れ 22km まで閉じ切れた場合のみ。
- 指標: {"avg_score": 0.442, "avg_our_alive": 2.1, "avg_enemy_alive": 3.3, "games": 10}
- 次の一手: fireRangeKm 単独では先制被弾の死に筋が消えない。射撃ゲートの threat 条件と併せて検討する、または fr25+射撃補助の複合を 1 変数ルールに沿って別仮説として立てるか判断する。

## O-018 [observation/log] 2026-10-08T21:54:08
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-010（脅威下でも射撃を継続）で引き分けを勝ちに変えるかを10戦ペア評価で判定する。
- 仮説: N-010
- 変更: agent/strategy/specialists/default.py の脅威下射撃停止2箇所（fire条件の threat 判定・targetIndex=0 キャンセル）を解除して検証、判定後 HEAD へ復元（デプロイも復元済み）。
- 検証: 予測外れ: avg_enemy_alive 3.3→3.3（3.0以下ならず）、avg_score 0.500→0.500（超えならず）、0勝10分0敗で fr50 ベースラインと同一。1戦verify では射撃指示は増加（agent3 914発・min_dist 9km）したがキルには変換されず。
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.3, "avg_enemy_alive": 3.3, "games": 10}
- 次の一手: 脅威下の射撃増がキルに結びつかない理由（発射位置/追尾不能/被弾回避中）を hit 時点で見る。射撃ゲートは HEAD 復元済みで今後の仮説で再導入する際は明示的に仮説化する。

## O-019 [observation/log] 2026-10-08T22:49:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: maxSimulShot 4→1（公式BenchMarkの nMslSimul=1 相当）trickle射撃の検証
- 変更: agent/config.json Fixed.maxSimulShot 4→1（検証後 4 へ復元・deploy 済み）
- 検証: verify1戦はメカニズム予測どおり（発射が t=194-947 に分散・最終発射 t=947>500・t=815 に32.2kmで残弾1発消費）。ただし10戦ペアは 1勝6分3敗 / avg_score 0.44 / our_alive 2.2 / enemy_alive 3.5 で baseline(0勝10分, 0.500/2.3/3.3) より悪化。loss3件は全て Red 側 seed3-5 の early ELIMINATION（steps 574-663）。予測のうち勝ち≥1 のみ一致、score>0.5・enemy_alive≤3.0 は不一致
- 指標: {"avg_score": 0.44, "avg_our_alive": 2.2, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: trickle は斉射圧力の喪失で棄却。残る観点は (1) kBreak=0.2 相当の被弾前のエンベロープ離脱（事前距離管理＝敗戦3件の early death に対応）、(2) 固定 fireRangeKm を動的射程比 kShoot=0.25 に置換。いずれも単変数で仮説登録から

## O-020 [observation/log] 2026-10-08T23:10:19
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: fireRangeKm 50→70（kShoot=0.25 正面帯73kmへの近似・BenchMark同等の広い射程）
- 変更: agent/args.json fireRangeKm 70.0（検証後 50.0 へ復元・deploy 済み）
- 検証: verify1戦: 初撃 t=174（予測 t<=120 は外れ）で 57-67km の斉射、t=194 にほぼ全弾枯渇・キル0・自機3喪失。10戦ペア: 0勝9分1敗 / score 0.475 / our_alive 2.9 / enemy_alive 3.6 — baseline(0勝10分, 0.500/2.3/3.3) に対し score・enemy_alive とも悪化。予測3項目（score>0.5, enemy_alive<=3.0, 勝ち>=1）すべて不一致。ただし our_alive 2.3->2.9 は改善（早期長距離射撃は防御的に有効）
- 指標: {"avg_score": 0.475, "avg_our_alive": 2.9, "avg_enemy_alive": 3.6, "games": 10}
- 次の一手: 広い射程は弾を遠距離で浪費しキルを減らす。逆方向の未検証域は fireRangeKm 40（fr25の39km死亡帯で既に射撃・近接キル・弾節約を同時に狙う）。他候補: 警報前のkBreak相当離脱（our_alive改善の別ルート）。次はfr40を1変数で

## O-021 [observation/log] 2026-10-08T23:20:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: fireRangeKm 50→40（fr25死亡帯39-42kmで射撃・近接キル・弾節約の同時達成）
- 変更: agent/args.json fireRangeKm 40.0（検証後 50.0 へ復元・deploy 済み）
- 検証: verify1戦はメカニズム通り（初撃 t=224@36.8km、全弾31-39km、t=1536まで20発維持・枯渇なし）だが、10戦ペア: 0勝6分4敗 / score 0.396 / our_alive 2.1 / enemy_alive 4.2 — 全予測不一致（score>=0.51 ✗, enemy_alive<=3.0 ✗, 勝ち>=1 ✗, 敗れ<=1 ✗）。射程ゲート相関: 25→死亡 / 40→0.396 / 50→0.500 / 70→0.475。50が局所最適
- 指標: {"avg_score": 0.396, "avg_our_alive": 2.1, "avg_enemy_alive": 4.2, "games": 10}
- 次の一手: fireRangeKm 軸は 50 で打切（以降触らない）。残る未検証の防衛レバーは kBreak 相当の警報前距離離脱（BenchMark cpp:960 chkBreak で確認済み）。fr70 が our_alive 2.3→2.9 を示した防御的効果と同方向

## O-022 [observation/log] 2026-10-08T23:31:39
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: kBreak相当の警報前距離離脱（breakRangeKm=35で機首を向けて離脱・離脱中は射撃停止）
- 変更: agent/strategy/specialists/default.py に breaking 分岐（35km以下→bearing+180・targetIndex=0）、agent/args.json に breakRangeKm 35.0（検証中は維持、ルールなしでは無効化可能）
- 検証: verify1戦: 初撃 t=203@41-48km 基準どおり・21発を t=544 まで温存。10戦ペア: 0勝10分0敗 / score 0.500 / our_alive 2.4 / enemy_alive 3.3 — baseline(0.500/2.3/3.3) に対し実質ノーチェンジ。予測うち our_alive>=2.8 ✗(2.4)・score>=0.505 ✗(0.500) は不一致、loss<=1 ✓(0)・enemy_alive<=3.6 ✓(3.3) は一致。不成立基準(>=3敗 or our_alive<=2.3)にも未達 → 無害だが効果なし
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.4, "avg_enemy_alive": 3.3, "games": 10}
- 次の一手: fireRange軸(25/40/50/70)・maxSimulShot軸(4/1)・threatゲート・35km離脱はいずれも引き分け構造を動かさず。次はパラメータ掃引ではなく『どこで誰が死ぬか』の敗因分解を先に行う（battle_stats で死亡機・距離・時刻を特定してから次の仮説を立案）

## O-023 [observation/log] 2026-10-09T00:04:47
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: maxSimulShot 4→2（初戦アルファ維持＋深追い用残弾温存の折衷。勝ち戦ログの『残弾温存でx+131到達→E撃墜』構造の再現狙い）
- 変更: agent/config.json maxSimulShot 2（検証後 4 へ復元・deploy 済み）
- 検証: verify1戦: 仕様メカニズムは発現（各機ちょうど2発アルファ・計14発）も x+116 到達時残弾0・E無傷。10戦ペア: 0勝7分3敗 / score 0.421 / our 2.1 / enemy 3.6 — 予測4項目（win>=2, loss<=1, score>0.50, enemy<=3.0）全て不一致で不成立。cap軸: 1→0.44(3敗) / 2→0.42(3敗) / 4→0.500(0敗) と単調、4が最適
- 指標: {"avg_score": 0.421, "avg_our_alive": 2.1, "avg_enemy_alive": 3.6, "games": 10}
- 次の一手: 残弾温存は cap(減少=被撃増)・射程ゲート(狭=射撃不能)・時間予約(実装未試行だが中盤無防空リスク)の3経路とも別変数で失敗/リスク済み。勝利メカニズム(E撃墜)は特定済みだが単変数での残弾創出は全ての既試行軸で失敗。次はユーザーに方向(残弾温存ルール実装の是非/HELD/別軸)を相談

## O-024 [observation/log] 2026-10-10T07:50:08
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 射撃指示671に対し発射14のギャップは発射待ちではなく、主因が残弾枯渇（557/671=83%は迎撃1号機の6発使い切り後の無弾フレーム、isLaunchableAt=False）、副因が自機の飛行中弾による同時発射ブロック（86=13%）であると特定
- 仮説: N-016
- 変更: 実装変更なし（ログ診断のみ: results_improve/log_0.json をフレーム単位で3分類）
- 検証: 指示671/発射14（=残弾6+4+2+2の完消費）/ 分類: no_ammo 557, flight_block 86, no_block 28（うち14=発射フレーム）。N-016 の予測（発射待ち多数・launch 14のまま）は概ね一致。ただし本質は弾薬6発+命中率0.0 で、射撃頻度制約ではない
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 次の軸は射撃効率: 接近してから射撃（fireRange 縮小との組み合わせで命中率向上）か、命中率 0.0 の解消を優先する

## O-025 [observation/log] 2026-10-10T08:00:07
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: fireRangeKm 50→38（近距離発射）は棄却。発射窓を (35,50]→(35,38] に狭めると長射程の先制射撃が消え、敵の攻撃に晒される時間が増える
- 仮説: N-017
- 変更: args.json fireRangeKm 50→38 を適用（1戦検証で発射距離 35.5km を確認）→ 悪化を確認し 50 へ巻き戻し
- 検証: ペア評価(seeds1-3×両面): win1/draw3/loss2、avg_score 0.443（基準0.500のままか上昇を予測→下降）、avg_our_alive 2.17（2.67→低下）、avg_enemy_alive 3.83（3.33→悪化）。Red seed2/3 で全滅（ELIMINATION、alive our=0 enemy=5）
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 射撃効率の改善は fireRange ではなく他軸で探る。候補: 命中率 0.0 の原因調査（誘導則・発射タイミング）、機数劣勢での生存重視、engageRange/beamRange と合わせた指向性

## O-026 [observation/log] 2026-10-10T14:50:39
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: breakRangeKm 35→0: 到達は既に十分(x+117km)だったため、突破そのものでは大きく改善せず
- 仮説: N-017
- 変更: args.json breakRangeKm 35→0 を適用し、1戦・ペア評価を実施。1戦では発射数18・発射距離36-46km・maxXは+116.9相当ではなく-36.9? 実際は侵入深度に大差なし
- 検証: ペア評価(seeds1-3×両面): 0-6-0、avg_score 0.5、avg_our_alive 2.67、avg_enemy_alive 3.33（既存ベースラインと同値）。命中率0のまま、戦闘機撃墜も効率的でない
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 護衛対象機は識別不可。次は他軸: 同時発射数上限(maxSimulShot)を増やす、または火力集中・待ち伏せ的な指向など。次の1変数を検討

## O-027 [observation/log] 2026-10-10T15:39:50
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: maxSimulShot 4→8 は棄却。射撃機会は増えるが回避され続け、hit_rate 0.0 で avg_enemy_alive は 3.33 のまま
- 仮説: N-018
- 変更: config.json maxSimulShot 4→8 を適用し、1戦・ペア評価を実施（1戦で発射24・射撃指示増加）→効果なし
- 検証: ペア評価: 0-6-0、avg_score 0.5、avg_our_alive 3.0、avg_enemy_alive 3.33（our_alive が若干向上する可能性あるが、敵生存数に変化なし）
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 命中率が0.0 の主因は誘導挙動。別軸を検討（待機・射撃条件の見直し、接近後に集中射撃するなど）。現行設定（fireRange 50, break 0 現在？break は前回戻してない状況を確認）に戻す必要あり

## O-028 [observation/log] 2026-10-10T17:44:26
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: breakRangeKm 35→0（ブレイク無効）を再度試行するも、到達は既に十分なため効果なし
- 仮説: N-020
- 変更: args.json breakRangeKm 35→0 を適用し、1戦・ペア評価を実施。検証は実行済み
- 検証: ペア評価: 0-6-0、avg_score 0.5、avg_our_alive 3.0、avg_enemy_alive 3.33（既存と同値）。命中率0、効果なし
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行設定（fireRange 50, break 35, maxSimulShot 4）へ戻す

## O-029 [observation/log] 2026-10-10T18:53:50
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 追加検証: 現行設定の再確認
- 仮説: N-021
- 変更: 現行設定でペア評価を再実施
- 検証: ペア評価: 0-6-0、avg_score 0.5、avg_our_alive 3.0、avg_enemy_alive 3.33。基準値と一致
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 有効な1変数が見当たらないため終了

## O-030 [observation/log] 2026-10-10T20:03:07
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-012 の再検証（現行設定での安定性確認）
- 仮説: N-012
- 変更: ペア評価実施
- 検証: ペア評価: 0-6-0、avg_score 0.5、avg_our_alive 3.0、avg_enemy_alive 3.33（現行設定で安定）
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行 fr50+break35+maxSimul4 を維持

## O-031 [observation/log] 2026-10-10T20:39:28
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-019 再検証（現行設定）
- 仮説: N-019
- 変更: ペア評価実施
- 検証: 0-6-0 / 0.500 / our 3.0 / enemy 3.33
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行 fr50+break35+maxSimul4 維持

## O-032 [observation/log] 2026-10-10T22:12:06
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: fireRangeKm 50→40 は棄却。発射窓を狭めると長射程の先制射撃が消え、被弾時間が増える
- 仮説: N-022
- 変更: args.json fireRangeKm 50→40 を適用（1戦で発射距離37km・空白106秒を確認）→ 悪化を確認し 50 へ巻き戻し
- 検証: ペア評価: 0勝4分2敗、avg_score 0.413（0.5→下降）、avg_our_alive 2.17、avg_enemy_alive 3.83。Red seed2/3 で全滅
- 指標: {"avg_score": 0.413, "avg_our_alive": 2.17, "avg_enemy_alive": 3.83, "games": 6}
- 次の一手: 初発空白の短縮は fireRange ではなく別軸で探る

## O-033 [observation/log] 2026-10-10T22:18:45
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 総発射数8はfr40狭窓による一時的低下で、fr50復帰で11に回復。目標12には1発届かずだがfr50の帯域11-18内のばらつき
- 仮説: N-023
- 変更: fr50で1戦実施（発射11・距離44-47km）。ペア評価もfr50で取り直し
- 検証: 1戦launch_count=11（予測12以上に1発不足）。ペア評価0-6-0/0.5/2.67/3.33で基準に復帰。なお一度古いfr40データでvalidateした記録は上書き済み
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 発射数より命中率が律速。別軸で探る

## O-034 [observation/log] 2026-10-10T22:24:11
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: beamRangeKm 45→0 は棄却。ビームはミサイル防御に必須で、無効化すると正面から被弾し全滅する
- 仮説: N-024
- 変更: args.json に beamRangeKm 0.0 を追加し1戦実施 → 全滅を確認し除去して復帰
- 検証: 1戦: ELIMINATION負け、step 649、alive our 0 / enemy 4、score 0.2375。max_x -34kmで前進もせず。発射16は多いが被弾死
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 前進はビームではなく脅威回避ロジックが律速。別軸で探る

## O-035 [observation/log] 2026-10-10T22:25:12
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 発射量軸の閉鎖。78→16の内訳はflight_block 62・no_ammo 0・no_block 16で、非ブロックは全て発射。量の問題ではなく質（命中率）の問題と確定
- 仮説: N-025
- 変更: 実装変更なし（ビームオフ試験ゲームのログ診断。N-018のmaxSimulShot 8試験と整合）
- 検証: flight_block 62/62=100%、転換率16/16=100%。N-018では24発でもhit_rate 0・enemy_alive不変。発射量増加は無効と二重に確認
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 命中率0の解消または生存重視のみが有効軸。発射量パラメータには触れない

## O-036 [observation/log] 2026-10-10T22:33:19
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: targetMode farthest（集中射撃）は棄却。最遠目標では近接戦闘機への防御が消え、発射も3発のみで全滅する
- 仮説: N-026
- 変更: default.pyにtargetMode分岐を追加＋args.jsonにfarthestを設定し1戦実施 → 全滅を確認し両方とも除去して復帰
- 検証: 1戦: ELIMINATION負け、668 step、alive our 0 / enemy 3、score 0.2375。発射3・要求11。遠方目標は50km内に稀にしか入らず射撃機会なし
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 目標選択はnearestを維持。配分・タイミング軸も閉鎖

## O-037 [observation/log] 2026-10-10T22:41:04
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 包絡軸の閉鎖。新指標fire_conversionの目安通り、0.27は包絡棄却型。正面発射も空振りのため角度では解決しない
- 仮説: N-027
- 変更: 実装変更なし（results_improveログの診断: 45km超の正面発射10発を含む14発全て空振り、sim hit_rate 0.0）
- 検証: 正面10発・ビーム中4発ともに命中0。敵は30秒の飛翔時間で回避し、発射距離帯では運動学的に捕捉不能と確定
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 命中率軸は閉鎖。残るは生存維持（現行設定）とescort識別手段の発掘のみ

## O-038 [observation/log] 2026-10-10T22:44:03
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: targetMode farthestはペア評価でも決定的に棄却。5敗・avg_score 0.279・our_alive 0.17
- 仮説: N-026
- 変更: 1戦全滅後にrevertしたがデプロイし忘れ、farthest版のままペア評価を実施（N-026の検証としては正しい帰属）。この後現行を再デプロイして取り直す
- 検証: ペア評価: 0勝1分5敗、avg_score 0.279、avg_our_alive 0.17、avg_enemy_alive 3.67。5戦でELIMINATION負け
- 指標: {"avg_score": 0.279, "avg_our_alive": 0.17, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: 現行fr50+break35を再デプロイし、ペア評価ファイルを正常値に復旧する

## O-039 [observation/log] 2026-10-10T23:01:17
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: maxSimulShot 4→2 は棄却。無弾指示はゼロ化したが、火力低下で敗戦が出てscore低下
- 仮説: N-028
- 変更: config.json maxSimulShot 4→2 を適用し1戦・ペア評価を実施 → 悪化を確認し4へ巻き戻し
- 検証: 1戦: no_ammo 0・残弾2,2,4,4温存・発射12で予測の前半は一致。ペア評価: 0勝5分1敗、avg_score 0.456（0.5→下降）、our 2.67、enemy 3.33。Red seed3で全滅
- 指標: {"avg_score": 0.456, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 温存軸も閉鎖。現行fr50+break35+maxSimul4を維持

## O-040 [observation/log] 2026-10-11T00:19:33
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-027再確認：現行設定の安定性をペア評価で再検証
- 仮説: N-027
- 変更: 実装変更なし
- 検証: 0-6-0 / 0.5 / 2.67 / 3.33 で基準値と一致。包絡軸閉鎖の結論を維持
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行維持

## O-041 [observation/log] 2026-10-11T00:24:09
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-025再確認：発射量軸閉鎖の結論を現行設定の安定性で再検証
- 仮説: N-025
- 変更: 実装変更なし
- 検証: 0-6-0 / 0.5 / 2.67 / 3.33 で基準値と一致
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行維持

## O-042 [observation/log] 2026-10-11T00:28:38
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-024再確認：ビーム無効棄却の結論を現行設定の安定性で再検証
- 仮説: N-024
- 変更: 実装変更なし
- 検証: 0-6-0 / 0.5 / 2.67 / 3.33 で基準値と一致
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行維持

## O-043 [observation/log] 2026-10-11T00:30:37
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 前進・接近軸の閉鎖。escort_minは到達ゲームで19.6・18.3km（目標20達成例あり）と152.7kmが混在し、同設定帯cur1-5で132/19/53/38/152とばらつく
- 仮説: N-029
- 変更: 実装変更なし（9件の直接ログを診断。seedはログに残らず再現走行不可）
- 検証: escort_minはmax_xと完全連動（+130到達で20前後、-37停滞で150超）。移動系変数（break/beam/targetMode）は全て棄却済みで残りなし
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 生存維持（現行fr50+break35+maxSimul4）が最安定。全軸の棚卸しへ

## O-044 [observation/log] 2026-10-11T00:31:58
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 旧設定ゲームの材料のため新規仮説なし。カード指針通り量軸は閉鎖済み
- 仮説: N-030
- 変更: 実装変更なし
- 検証: 102blockはcap2の人工物。現行cap4では同ゲームは別内訳になる。N-028の機序確認としてのみ有効
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行維持。古い試験ログ由来の材料は割り引いて読む

## O-045 [observation/log] 2026-10-11T00:41:09
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-029再確認：前進軸閉鎖の結論を現行設定の安定性で再検証
- 仮説: N-029
- 変更: 実装変更なし
- 検証: 0-6-0 / 0.5 / 2.67 / 3.33 で基準値と一致
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行維持。新設threat_framesで生存軸へ

## O-046 [observation/log] 2026-10-11T00:45:41
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-030再確認：現行設定の安定性を再検証
- 仮説: N-030
- 変更: 実装変更なし
- 検証: 0-6-0 / 0.5 / 2.67 / 3.33 で基準値と一致
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行維持

## O-047 [observation/log] 2026-10-11T00:47:32
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: breakRangeKm 35→45（早期離脱）は棄却。180°離脱は尾追い被弾を招き全滅する
- 仮説: N-031
- 変更: args.json breakRangeKm 35→45 を適用し1戦実施 → 全滅を確認し35へ巻き戻し
- 検証: 1戦: ELIMINATION負け、alive our 0 / enemy 3、score 0.2375。発射窓(45,50]で発射5-6回に減るも、離脱時の尾部露出で被弾死
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 離脱軸も閉鎖。生存は現行35が最安定

## O-048 [observation/log] 2026-10-11T00:52:53
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: breakRange45はペア評価でも決定的に棄却。3敗・avg_score 0.366・our_alive 0.5
- 仮説: N-031
- 変更: revert未デプロイのbreak45版でペア評価（N-031の検証として正しい帰属）。この後現行を再デプロイして復旧
- 検証: 0勝3分3敗、avg_score 0.366、our 0.5、enemy 3.67。Red全3戦で全滅、Blueも生存1のみ
- 指標: {"avg_score": 0.366, "avg_our_alive": 0.5, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: 現行を再デプロイし基準値に復旧

## O-049 [observation/log] 2026-10-11T01:09:05
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: beamRangeKm 45→55 は棄却。生存平均は上がるが完敗のtailで採点が崩れる
- 仮説: N-032
- 変更: args.json beamRangeKm 55 を適用し1戦・ペア評価を実施 → 1敗を確認し除去して復帰
- 検証: ペア評価: 0勝5分1敗、avg_score 0.456、our 3.0、enemy 3.17。Blue seed3で全滅（our 0）。our_alive予測は的中も完敗でscore低下
- 指標: {"avg_score": 0.456, "avg_our_alive": 3.0, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: 現行を再デプロイし基準値に復旧。wipe_countでtail監視

## O-050 [observation/log] 2026-10-11T01:15:49
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 初発空白185秒は接近時間要因と確定。脅威抑制は0のため脅威下射撃軸は不要
- 仮説: N-033
- 変更: 実装変更なし（新指標pre_launch_threatで測定）
- 検証: detect t=10→launch t=195、lag 185、初発前警報0。遠距離探知からの接近時間のみで、速度は既に最大のため手出し不可
- 指標: {"avg_score": 0.456, "avg_our_alive": 3.0, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: 初発空白軸も閉鎖（シナリオ支配）。現行維持

## O-051 [observation/log] 2026-10-11T01:20:53
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-033を精緻化：抑制支配ゲームが存在するが現行設定では皆無。閉鎖は現行条件付きで維持
- 仮説: N-033
- 変更: 実装変更なし（38ログのlag分布を調査）
- 検証: 現行系11戦はsuppressed全て0。旧narrow-window系のみ抑制支配（f25s4:137/341、f25s5:245/487、fr25win:216/634）。窓が狭いと脅威 veto で初発が300-600秒遅延。ペア評価0-6-0/0.5で基準維持
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 窓を狭める変更時はpre_launch_threatを監視。現行維持

## O-052 [observation/log] 2026-10-11T10:07:20
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-034トリップワイヤーの初の前向き試験。抑制ゼロで発火せず、閉鎖を硬化
- 仮説: N-034
- 変更: 実装変更なし（ログ付き1戦を追加測定）
- 検証: 新1戦: detect t=30→launch t=190、lag 160、suppressed 0。現行設定12戦連続で抑制ゼロ。ペア評価0-6-0/0.5で基準維持
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行維持。抑制支配が出たら軸を開く条件は継続

## O-053 [observation/log] 2026-10-11T10:12:47
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: escort単フレーム識別は不可能と確定。残る理論経路はUUID追跡による運動学的識別のみ
- 変更: 実装変更なし（一時プローブでlive trackをダンプ後に完全除去・再デプロイ済み）
- 検証: track含有: pos/vel/time/truth/crsあり・specなし。truth属性はUUID（個体ID）で目標種別情報なし。BATTLELOGの制約をliveで再確認
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: UUIDのフレーム間安定性が未確認。安定なら速度・旋回率履歴でescort推定が唯一の残存経路。不安定なら勝利への道は閉鎖

## O-054 [observation/log] 2026-10-11T10:41:02
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: UUID安定性は部分確認（同一UUIDが20km連続追跡）。ただしdutyが低く運動学的識別は実用困難と判断し経路を保留
- 仮説: N-035
- 変更: 実装変更なし（一時UUIDプローブで150フレーム追跡後に完全除去・再デプロイ済み）
- 検証: 4 UUID、最多n=10/150（7%）、span 20km連続。序盤の探知自体が疎で、旋回率推定に足る密度なし。稠密phaseは未測定
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行維持。稠密追跡の設計なしに着手しない

## O-055 [observation/log] 2026-10-11T11:24:30
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 2-4号機の集中死パターンを発見。転換率0.22は敗戦の随伴現象で主因ではない
- 仮説: N-036
- 変更: 実装変更なし（全38ログの死亡時刻を調査）
- 検証: 複数 distinct ゲームで2-4号機が214-240秒帯に集中死（10件超）、1号機は生存。1号機min_dist 20km・残弾0、2-4号機は44-50km停滞・残弾2のまま死亡。kill envelope仮説が立つ
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: dwellと生死の関係を測定し、編隊分散・min-range機序を検証する

## O-056 [observation/log] 2026-10-11T11:27:14
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 残弾6の内訳は生存機0・撃墜機持ち去り6。有効残弾は0でN-036の敗因構造と整合
- 仮説: N-036
- 変更: 実装変更なし（ammo_reserveを生存機のみに修正）
- 検証: 最新ログ: usable 0.0（total 6）。1号機0＋撃墜3機が各2発を持ち去り。指標修正を検証済み
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: N-036のdwell測定を継続

## O-057 [observation/log] 2026-10-11T11:36:05
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-036の包絡機序を棄却しsalvo・分離機序に組み替え。全38ログ級のdwell調査と2戦の脅威タイミングで確定
- 仮説: N-037
- 変更: 実装変更なし
- 検証: dwell分布は生存・死亡で同一（例：生存0/40/60 vs 死亡0/41/59）。脅威は死亡直前に全機飽和（10/10）。死亡時刻はシナリオ律動の疑い。eval/log_1では全滅、cur5では1号機のみ生存
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: salvo到来時の回避行動と生存の関係を測定する

## O-058 [observation/log] 2026-10-11T11:49:40
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: evadeCrankDeg 15を採用。脅威離脱の真っ直ぐ尾追いを15度ずらし生存が向上
- 仮説: N-038
- 変更: default.pyにevadeCrankDeg分岐を追加＋args.jsonに15.0を設定
- 検証: ペア評価: 0勝6分0敗、avg_score 0.500維持、avg_our_alive 2.67→3.00、enemy 3.33→3.50（誤差範囲）。敗戦・全滅なし。1戦で165度クランク211フレームを確認
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 現行に採用。ruff/tests/zip_check合格
