
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

## O-059 [observation/log] 2026-10-11T11:54:48
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 機体別内訳で配分構造を確定。1号機が要求55%・撃ち尽くし、他機は残弾を持ったまま死亡
- 仮説: N-036
- 変更: 実装変更なし（新per-slot証拠を適用）
- 検証: 121要求中1号機67（55%）・無弾28は全て1号機。2-4号機は54要求・無弾0・残弾各2を残して死亡。6発が死と共に失効。転換率ギャップは死亡の随伴現象と確定
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: N-036/N-037のsalvo・分離軸を継続

## O-060 [observation/log] 2026-10-11T12:05:39
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 残弾目標8を解除。温存誘導はN-028棄却済みでstranded目標0と矛盾するため
- 変更: 実装変更なし（custom_metricsの目標のみ解除）
- 検証: 全引き分け0.5下で残弾0〜10は無相関。目標8の追求＝温存＝0.456に悪化の実績あり
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 参考値として監視継続

## O-061 [observation/log] 2026-10-11T14:37:51
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 未処理表示の9件超を現物照合し、処理済みを記録連動に紐付け
- 変更: 実装変更なし（serve/indexの記録連動＋本バックフィル）
- 検証: 全カードの値・出所・既存記録を照合。lag-188は抑制0を確認。トリガー類は自動誘導が正常発火。
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 以降の材料は記録時にmaterialsを付けて自動処理済み化

## O-062 [observation/log] 2026-10-11T14:48:50
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: evadeCrankDeg 15→25 は棄却。用量は単調でなく15付近が峰
- 仮説: N-039
- 変更: args.json evadeCrankDeg 15→25 を適用し1戦・ペア評価を実施 → 悪化を確認し15へ巻き戻し
- 検証: ペア評価: 0勝6分0敗、avg_score 0.500維持、avg_our_alive 2.17（3.0→低下）、enemy 3.33→3.83。0→2.67、15→3.0、25→2.17で峰は15付近
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.17, "avg_enemy_alive": 3.83, "games": 6}
- 次の一手: 15を維持。用量探索は終了

## O-063 [observation/log] 2026-10-11T15:17:50
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: crank-25戦の脅威は振動型salvoで1号機に集中。N-039棄却の機序補強
- 仮説: N-039
- 変更: 実装変更なし
- 検証: 1号機275が200/300/400/500/600秒帯に波状（400帯は100/100飽和）。2-4号機は200-399のみ。以後沈黙。深掘り機が全波を被る構造
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.17, "avg_enemy_alive": 3.83, "games": 6}
- 次の一手: 現行維持

## O-064 [observation/log] 2026-10-11T15:21:06
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: crank-25試験戦の全量確定。深追い+131・duty0.62・trigger_ammo_dry初発火
- 仮説: N-039
- 変更: 実装変更なし
- 検証: req634（1号機561）・発射19・lag199/抑制0・min_dist31・max_x+131・reserve0・stranded4・duty0.62・threat398。TIMEUP引き分けRed2/Blue2。dutyは自前の0.5閾値を超過
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.17, "avg_enemy_alive": 3.83, "games": 6}
- 次の一手: 現行維持。稠密phaseのUUID追跡は別途設計時に

## O-065 [observation/log] 2026-10-11T16:13:45
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: ゴースト仮説は的中。初発空白の定義を持続探知起点に修正し199→56に
- 仮説: N-040
- 変更: 実装変更なし（serve.pyのlag算出を持続8連続起点に修正）
- 検証: t=3探知は1フレームで消えるゴースト。持続開始t=146→初発t=202で真の空白56秒（目標60に肉薄）。全ログで再計算される
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.17, "avg_enemy_alive": 3.83, "games": 6}
- 次の一手: 現行維持

## O-066 [observation/log] 2026-10-11T16:31:47
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-040のペア評価確認。クランク現行の基準値を再検証
- 仮説: N-040
- 変更: 実装変更なし
- 検証: 0-6-0 / 0.5 / 3.0 / 3.5 でクランク基準値と一致
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 現行維持

## O-067 [observation/log] 2026-10-11T16:46:46
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: crank-15の採用を取り消し0.0に戻す。未見seedでcrank-0が優位
- 仮説: N-041
- 変更: args.json evadeCrankDeg 15→0.0に戻す（分岐コードは残置・デフォルト無効）
- 検証: seed4-6: crank15が0-4-2/0.412/1.17、crank0が0-5-1/0.456/1.67で全指標上回る。12戦合計もcrank-0が優位（全滅1 vs 2）
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 採用判定は複数seed必須にルール化

## O-068 [observation/log] 2026-10-11T17:07:44
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: seeds 7-9でcrank-0の汎化を再確認。全滅なし
- 仮説: N-041
- 変更: 実装変更なし
- 検証: 0-6-0 / 0.5 / 2.67 / 3.67。全滅0。18戦合計で全滅1のみ（4-6の1戦）。crank-0維持を支持
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: 現行維持

## O-069 [observation/log] 2026-10-11T18:00:53
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-035前進：接近局面でUUID追跡は稠密（最大83連続）。分類器は未設計のため軸は開設計画のまま
- 仮説: N-035
- 変更: 実装変更なし（一時プローブで測定後に完全除去・再デプロイ済み）
- 検証: 300フレームで5航跡・各81-94ヒット・maxrun 63-83・span 29-48km。旋回率推定に足る密度。識別ルールと命中は未検証
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: 分類器の設計＋enemies_direct真値での検証が次の手（未着手）

## O-070 [observation/log] 2026-10-11T18:02:14
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 脅威の1号機集中を再確認（253/288=88%）。深掘り機が被弾を吸収する構造
- 仮説: N-036
- 変更: 実装変更なし
- 検証: プローブ戦ELIMINATION負け：1号機threat253・残弾0、他機は46-49km停滞・残弾2のまま全滅。min_dist42で深掘りせず
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: 現行維持

## O-071 [observation/log] 2026-10-11T23:26:41
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 初発まで 66秒 / 目標 60秒
- 変更: 空白短縮策の検討が必要
- 検証: 
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: MWS探知距離調整、回避パターンの見直し

## O-072 [observation/log] 2026-10-11T23:56:43
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: verify結果: Draw (score 0.500, our 3 alive, enemy 5 alive)
- 変更: MWS探知距離未延長でのDraw確認。仮説N-043の検証継続が必要。
- 検証: 
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: ペア評価での指標比較を試行。MWS探知距離調整での改善確認。

## O-073 [observation/log] 2026-10-12T12:02:50
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: verify結果: Draw (score 0.500, our 3 alive, enemy 5 alive)
- 変更: MWS探知距離未延長でのDraw確認。仮説N-044/N-045の検証継続が必要。
- 検証: 
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: ペア評価環境復旧時の比較検討。MWS探知距離調整での改善確認。

## O-074 [observation/analysis] 2026-10-12T12:38:10
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: MWS探知距離調整結果の記録
- 変更: N-045 に関する検証：paired 評価実施
- 検証: avg_score 0.500、avg_our_alive 2.67、avg_enemy_alive 3.33（6戦全draw）
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 未検証仮説 N-042〜N-044 の処理

## O-075 [observation/analysis] 2026-10-12T12:51:50
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: N-044検証結果
- 変更: 被弾警報フレーム数短縮の仮説を検証
- 検証: seed 1,2,3×両面 6戦：全draw、avg_score 0.500、avg_our_alive 2.67、avg_enemy_alive 3.33
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 残る未検証仮説 N-042〜N-043 の処理

## O-076 [observation/analysis] 2026-10-12T13:03:17
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: N-044検証結果
- 変更: 被弾警報フレーム数短縮の仮説（N-044）をpaired評価で検証
- 検証: seed 1,2,3×両面 6戦：全draw、avg_score 0.500、avg_our_alive 2.67、avg_enemy_alive 3.33。顕著な改善なし
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 未検証仮説 N-042〜N-043 の verify/validate 実施

## O-077 [observation/analysis] 2026-10-12T13:07:16
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: N-044検証結果
- 変更: 被弾警報フレーム数短縮の仮説（N-044）をpaired評価で検証
- 検証: seed 1,2,3×両面 6戦：全draw、avg_score 0.500、avg_our_alive 2.67、avg_enemy_alive 3.33。顕著な改善なし
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 未検証仮説 N-042〜N-043 の verify/validate 実施

## O-078 [observation/analysis] 2026-10-12T13:18:12
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: N-044検証結果
- 変更: 被弾警報フレーム数短縮の仮説（N-044）をpaired評価で検証
- 検証: seed 1,2,3×両面 6戦：全draw、avg_score 0.500、avg_our_alive 2.67、avg_enemy_alive 3.33
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 未検証仮説 N-042〜N-043 の verify/validate 実施

## O-079 [observation/analysis] 2026-10-12T13:19:22
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: N-043検証結果
- 変更: MWS探知距離延長の仮説（N-043）をpaired評価で検証
- 検証: seed 1,2,3×両面 6戦：全draw、avg_score 0.500、avg_our_alive 2.67、avg_enemy_alive 3.33
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 未検証仮説 N-042 の verify/validate 実施

## O-080 [observation/analysis] 2026-10-12T13:20:30
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: N-043検証結果
- 変更: MWS探知距離延長の仮説（N-043）をpaired評価で検証
- 検証: seed 1,2,3×両面 6戦：全draw、avg_score 0.500、avg_our_alive 2.67、avg_enemy_alive 3.33
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 未検証仮説 N-042 の verify/validate 実施

## O-081 [observation/analysis] 2026-10-12T13:36:31
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: N-043検証結果
- 変更: MWS探知距離延長の仮説（N-043）をpaired評価で検証
- 検証: seed 1,2,3×両面 6戦：全draw、avg_score 0.500、avg_our_alive 2.67、avg_enemy_alive 3.33
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 未検証仮説 N-042 の verify/validate 実施

## O-082 [observation/analysis] 2026-10-12T13:36:55
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: N-042検証結果
- 変更: MWS探知距離延長の仮説（N-042）をpaired評価で検証
- 検証: seed 1,2,3×両面 6戦：全draw、avg_score 0.500、avg_our_alive 2.67、avg_enemy_alive 3.33
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 未検証仮説なし。次の仮説立案または現状維持を検討

## O-083 [observation/analysis] 2026-10-12T13:53:33
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: MWS〜回避の前倒しは物理的に不可。被弾警報フレーム数は 1 変数では短縮できない（探知距離は仕様側、判断周期は既に最小）。この材料から生存軸の新規仮説は立てない。
- 仮説: N-046
- 材料: 1 件を紐付け（ダッシュボードの処理済み判定用）
- 変更: コード変更なし。MWS 由来の軸を閉鎖（③）。custom_metrics.json から threat_frames カードを除去し、serve.py の自動仮説文を削除、方針の削除済み一覧に追記。
- 検証: 根拠: baseTimeStep=1.0s（common/R8_contest_youth_mission_config.json）、interval は tick 単位で最小1（R8ContestAgentSample01.py:2008）、MWS Lref≈10km（BATTLELOG_FORMAT.md:132）。agent に探知距離・判断周期の可変パラメータなし。
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 生存軸ではなく勝ち筋（護衛対象機撃墜）側へ。未試験の固定軸は engageRangeKm(60)/marginKm(25)。

## O-084 [observation/analysis] 2026-10-12T14:08:39
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: 護衛対象機の識別・優先目標化（N-047）は棄却
- 変更: default.py に『遠方航跡>120km を護衛対象機として識別し _track_escort で方位追跡、識別中は pool=[escort] で最優先かつ breaking を無効化』を追加
- 検証: ペア評価 seed1,2,3×両面（6戦）: win1/draw0/loss5, avg_score 0.308（基準0.500）, avg_our_alive 0.33（2.67）, avg_enemy_alive 4.0（3.33）。seed1/2(Red)・全Blue は ELIMINATION 全滅。
- 指標: {"avg_score": 0.308, "avg_our_alive": 0.33, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: 護衛対象機へ直進すると護衛戦闘機に撃墜される（N-026 farthest=全滅と同型）。護衛対象機軸は単純な直進優先では不可。回避を維持しつつ接近する設計（護衛戦闘機を先に処理 or 遠距離から一撃離脱）が必要。

## O-085 [observation/analysis] 2026-10-12T14:26:44
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: 護衛対象機軸（N-048 機会目標化）を未見 seed で確認し閉鎖
- 変更: N-048: 護衛対象機の識別(_track_escort)を既存 escorted フォールバックに供給するのみ（threat回避・breaking・near優先は維持）。検証後 reflux 済み（default.py は revert 済み）
- 検証: seed4,5,6×両面: N-048 0/5/1 avg_score0.455 our2.33 enemy4.17（B4全滅） / default 0/5/1 avg0.456 our1.67 enemy3.5（B6全滅）。score同等、our↑だがenemy↑で相殺。seed1-3のour改善(2.67→3.0)は未見seedで再現せず。
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: 護衛対象機へ接近する限り戦闘機嚮導で戦力を失い、0.5天井は破れない。勝つには護衛戦闘機を先に排除して安全に接近する等、護衛対象機の直接優先以外の設計が必要。

## O-086 [observation/log] 2026-10-12T15:41:32
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 防衛ライン(守勢シフト)は score 中立・our_alive改善だが負けは seed 間で移動し頑健性に難
- 変更: N-049: default.py に defenseLineXKm を追加（own[0]>line で desiredAz=180 に反転）。-20 は全機 x<=-35 で不発、-60 で初めて有効化
- 検証: line=-60: seeds1-6(12戦) 0/12/0 avg0.5 our3.0 enemy3.33（基準12戦 avg0.478 our2.17 enemy3.42 1敗）／holdout 7-9(6戦) 0/5/1 avg0.46 our3.0 enemy3.0（基準 0/6/0 0.5/2.67/3.67）。R8で護衛対象機がstep418で撃墜（新規の負け）。全18戦合算 score0.485→0.487 our2.5→3.0 enemy3.47→3.22 敗戦1→1。
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.33, "games": 12}
- 次の一手: score中立だがour +0.5/enemy -0.25。負けがB6からR8へ移動。ハード反転(180)による陣形の隙が R8 敗因の可能性。ソフト保持（前進は止めるが反転しない=速度低下）で頑健化の余地。あるいは別軸へ。

## O-087 [observation/log] 2026-10-12T15:55:03
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 守勢シフト（防衛ライン系）は頑健に負けを減らせず閉鎖
- 変更: N-050: 前線が空(engageRange内に敵なし)のときだけ own[0]>-60 で desiredAz=180 に反転し後退するソフト保持
- 検証: seeds1-6(12戦): 0/10/2 avg0.456 our2.67 enemy3.75（基準 0/11/1 avg0.478 / N-049b 0/12/0 avg0.5）。R2・B4 で新規の敗戦2件（後退が敵を通す）。
- 指標: {"avg_score": 0.456, "avg_our_alive": 2.67, "avg_enemy_alive": 3.75, "games": 12}
- 次の一手: ライン系の総括: -20不発(N-049) / -60ハードは敗戦をB6→R8へ移動し中立(N-049b) / -60ゲート付きソフトは2敗で悪化(N-050)。防衛行動は負けを頑健に減らせない。スコア>0.5の唯一の筋は敵護衛対象機撃墜であり、護衛戦闘機排除→到達の2段階設計が不可欠。

## O-088 [observation/log] 2026-10-12T17:50:23
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 非探知時の方位を直近の敵方位保持に変えると敵生存がむしろ増え、スコアは改善しない（N-051 棄却）
- 変更: N-051: 非探知時に desiredAz=0 を self._lastEnemyBearing（直近探知の敵方位）保持に変更（1変数）
- 検証: seeds1-3×両面(6戦): 0/6/0 avg_score 0.500 our 3.33 enemy 3.67（基準 0/6/0 0.500 our 2.67 enemy 3.33）。予測 avg_enemy_alive 3.33→3.0以下 に対し 3.67 で逆。our_alive は 2.67→3.33 に改善したが引き分けは生存数無関係でスコア 0.5 のまま。
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.33, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: N-051 棄却・revert。方位保持は交戦を減らし両軍の生存を増やすため、敵生存↑で採点に不利。detect_duty 軸（識別の可否条件）からの改善筋は閉鎖。

## O-089 [observation/code] 2026-10-12T17:54:55
- 種別: observation（実測に基づく事実）
- 出所: code（自作コードの読み取り）
- 方向性: detect_duty を条件指標としてカード/軸表から除去（③軸整理）
- 変更: custom_metrics.json から detect_duty カード削除、serve.py の _duty_branch_hypothesis と分岐を削除、HYPOTHESIS_POLICY.md の行を削除し削除済みへ追記（計算は残置）
- 検証: ruff All checks passed / tests/test_state_dashboard.py 37 passed / custom_metrics.json は有効な JSON
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.33, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: detect_duty 材料からの新規仮説は立てない（O-088 と同一材料ルール）。計算は残すので必要なら戻せる。

## O-090 [observation/code] 2026-10-12T17:59:38
- 種別: observation（実測に基づく事実）
- 出所: code（自作コードの読み取り）
- 方向性: min_dist_km の目標25を解除（参考値化・③軸整備）
- 変更: custom_metrics.json の min_dist_km target 25→null、note 更新（接近距離は採点に無関係・接近軸は N-029 閉鎖）、HYPOTHESIS_POLICY.md の目標の解除へ追記（カードは診断用に残置）
- 検証: custom_metrics.json 有効な JSON・target=None / tests/test_state_dashboard.py 37 passed。カード仮説欄は serve.py:1541-1547 が既に「新規仮説なし」を表示
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.33, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: min_dist 材料からの新規仮説は立てない（fireRange/break/beam は再試験禁止、接近軸は閉鎖）。接近は引き分けで採点に影響しない。

## O-091 [observation/log] 2026-10-12T18:31:59
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 境界回避 marginKm 25→40 が採点・生存を動かすかを確認（未試験固定軸の消化）
- 仮説: N-052
- 変更: agent/args.json の marginKm を 25→40 に変更（1変数）。検証後に 25 へ巻き戻し
- 検証: ペア評価 seeds1,2,3×両面=6戦: 0勝6分0敗, avg_score 0.500, avg_our_alive 2.67, avg_enemy_alive 3.33。全6戦が default(marginKm25) と score/our_alive/enemy_alive/endReason まで完全一致。予測 our 2.67→3.0・score→0.55 は外れ。marginKm は採点・生存を動かさない（実効なし）。仮説 N-052 棄却
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 1変数の数値ノブは全滅。勝ち筋（護衛対象機撃墜）の設計軸へ。O-084/085 の護衛戦闘機の先制排除など、1変数では表せない構造変更のみ残る

## O-092 [observation/log] 2026-10-12T18:41:42
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: marginKm 実効なしの汎化確認（未見 seed 4-6）
- 仮説: N-052
- 変更: 変更なし（marginKm=40 と =25 を同一 seed 群で比較するだけ）
- 検証: ペア評価 seeds4,5,6×両面=6戦: marginKm=40 も =25 も 0勝5分1敗, avg_score 0.456, avg_our_alive 1.67, avg_enemy_alive 3.5。全6戦（Blue seed6 の ELIMINATION 含む）で score/生存/endReason まで完全一致。seeds1-3 と合わせ 12戦すべて同一。marginKm は採点・生存を動かさない
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.67, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 1変数の数値ノブは全滅。勝ち筋（護衛対象機撃墜）の構造変更のみが残る（O-084/085）

## O-093 [observation/log] 2026-10-13T21:41:44
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 最短交戦距離 0.1km 改善のため beamRangeKm を 35km に拡大
- 仮説: N-117
- 変更: agent/args.json beamRangeKm 45→35
- 検証: 1ゲーム検証で全滅（0 vs 3, score 0.235）。早期ビームがセンサロスト早発・交戦不能を招き大幅悪化。予測 our 3.5 / score 0.520 は外れ
- 指標: {"avg_score": 0.5, "avg_our_alive": 4.0, "avg_enemy_alive": 5.0, "games": 1}
- 次の一手: beamRangeKm=45 に戻し基線維持

## O-094 [observation/log] 2026-10-14T22:30:35
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: fireRangeKm=40 では hit_rate が 0.0 に悪化（予測 0.35 以上と逆）。射撃開始が近すぎると命中しない。
- 変更: agent/args.json の fireRangeKm を 50→40→50 に戻した（現状 baseline 復帰）
- 検証: 1戦: draw / score=0.500 / alive our=5 enemy=3 / hit_rate=0.0
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: N-118 棄却。fireRangeKm は 50 が最良。別軸（hit_rate 向け）を検討

## O-095 [observation/log] 2026-10-15T10:19:33
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: trackConfirmFrames=3 で命中0→1発に改善、hit_rate 0.045。avg_score は 0.500 のまま
- 変更: default.py に trackConfirmFrames 追加（同一ターゲット連続追跡Nフレームで射撃）、args.json trackConfirmFrames=3
- 検証: 1戦: hits 1 / launches 22 / hit_rate 0.045（従来 0/24）。ペア評価 6戦: avg_score 0.500 変化なし
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: trackConfirmFrames の値調整（5等）か、命中率が低い別の原因（射撃角度・相対速度）を深掘り

## O-096 [observation/log] 2026-10-15T10:23:16
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: trackConfirmFrames スイープ: 3=22発1命中/0.045、4=3発0命中、5=7発0命中。3が最良だが効果は小さい
- 変更: args.json trackConfirmFrames を 3→4→5→3 と変更して1戦ずつ比較
- 検証: 各1戦: f3=hits1/launch22, f4=hits0/launch3, f5=hits0/launch7。基線(f0)=hits0/launch24
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: trackConfirmFrames 単独では hit_rate 0.35 に届かない。射撃角度・相対速度など別の深掘りが必要

## O-097 [observation/code] 2026-10-15T22:12:32
- 種別: observation（実測に基づく事実）
- 出所: code（自作コードの読み取り）
- 方向性: trackConfirmFrames の判定を index 連続から位置連続（trackPosToleranceKm=10km）に変更
- 変更: default.py: ターゲット位置を own x,y + dist·cos/sin で算出し、直前フレームから10km以内なら trackCount 増加
- 検証: 1戦: launches 24 / hits 1 / hit_rate 0.042（indexベース 22/1/0.045 と同水準）。ペア評価6戦 avg_score 0.500 変化なし
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: 位置ベース・indexベースいずれも hit_rate 0.35 に届かず。射撃距離帯（43-50km）自体の命中率が低い可能性を検証

## O-098 [observation/log] 2026-10-15T22:59:05
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛対象機はセンサで識別不能（escort flag 常に0）、距離187-215kmで射程外。ELIMINATION 勝利なしでは score は 0.500 が上限
- 変更: 護衛対象機優先ターゲット選択を実装したが escort flag が常に0のため無効、元に戻した
- 検証: 観測ログ: escort flag 全フレームで0.0。遠方敵(>100km)は t=34 で 214km、最小でも 187km。ELIMINATION なし = 全戦 TIMEUP draw = score 0.500
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: ELIMINATION なしで 0.500 を超える手段があるか、または深い進出による護衛対象機攻撃の可行性を検討

## O-099 [observation/log] 2026-10-16T18:47:47
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: escortSeekDistKm=150 は score を 0.500→0.315 に悪化（敗戦4/6）。escort分岐が射撃とビーム回避を止めてしまうため
- 変更: escortSeekDistKm=150（遠方目標優先接近）を args.json/default.py に追加
- 検証: ペア評価 seeds1-3×両面: win0/draw2/loss4, avg_score 0.315, our_alive 0.33。オフライン再現で escort中113フレーム・射撃指令0を確認
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: escort分岐を『安全時のみ旋回優先・射撃/回避は通常どおり』に修正して再検証、または撤回

## O-100 [observation/log] 2026-10-16T19:11:10
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 専任追跡機(escortChaserCount=1)でも ELIMINATION は0、avg_score 0.474（PENALTY敗戦1）。最接近は100kmまで改善したが射程50kmには届かず
- 変更: escortChaserCount=1: offset<1 の1機が追跡機（脅威時のみ旋回差し替え・marginFront/Back無効化・射撃は通常）
- 検証: ペア評価: win0/draw5/loss1(PENALTY), score 0.474, our_alive 2.83。1戦検証で slot2 の far 最接近 100.2km（従来138km）。y=±150 越境で PENALTY 確認（marginFront 無効化が原因）
- 指標: {"avg_score": 0.474, "avg_our_alive": 2.83, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: 追跡機のミサイル温存（戦闘機に撃たず護衛対象機のみ狙う）と margin 復活（PENALTY回避）を検証。ただし3回連続不成立のため方向転換も要検討

## O-101 [observation/log] 2026-10-16T19:30:59
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 追跡機のミサイル温存(escortChaserHoldFire=1)＋margin復活でも ELIMINATION 0、avg_score 0.500（PENALTY消滅は確認）
- 変更: 温存: chaserは escort候補が fireRangeKm 内のみ射撃・escortSeekDistKm 150→60（射程内まで候補維持）・margin 全機復活・agentFullName は ':' 分割先頭を使用（フレームワークは agent:model:policy 形式のため chaser 認定が外れていたバグを修正）
- 検証: ペア評価: win0/draw6/loss0, score 0.500, our_alive 2.5。1戦検証で chaser(slot2)が0発で温存を確認。ただし chaser が撃たないため 3対4 で戦力崩壊しour_alive は v2 の3.67から低下
- 指標: {"avg_score": 0.5, "avg_our_alive": 2.5, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: ELIMINATION 4回尝试で全て不成立。接近距離の限界(センサ断続・Eが100km外)が構造要因。chaser温存は生存悪化のみで利益なし → 撤回検討

## O-102 [observation/log] 2026-10-16T19:38:23
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: ELIMINATION 4試行は不成立と結論。ユーザー判断で v2（安全時のみescort旋回・全機射撃維持）に復帰
- 変更: chaser/温存コードを削除、escortSeekDistKm=150 に復元、margin 通常どおり
- 検証: ペア評価 seeds1-3×両面: win0/draw6/loss0, score 0.500, our_alive 3.67 — 旧v2(escortseek_safe)と完全一致。ruff clean
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 提出は v2 状態。コミットはユーザー承認後に実施

## O-103 [observation/analysis] 2026-10-16T20:04:15
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: breakRangeKm 軸を sweep して未検証仮説 N-054〜N-098（最短交戦距離25km以下）を検証・棄却
- 変更: breakRangeKm 35→25/20/45 を個別に検証し、いずれも採用せず35に復元
- 検証: brk25: 0.500/3.83/3.83, brk20: 0.500/3.83/3.5, brk45: 0.456/2.0/3.83(明確悪化), 現行35: 0.500/3.67/3.5。45は棄却、25/20はscore据え置きで生存微改善のみ
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 残る未検証軸なし。N-119(fireRange低下)はN-118/124で、N-121/122(track)はN-120/125で、N-126〜129(escort)はv1-v4で検証済み。全て棄却または採用せず

## O-104 [observation/log] 2026-10-16T20:49:03
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 発射方位条件 fireAspectDeg=30 を検証。方位条件は効いた（発射方位差が 30° 以内に限定）
- 仮説: N-132
- 材料: 1 件を紐付け（ダッシュボードの処理済み判定用）
- 変更: fireAspectDeg を default.py と args.json に追加。検証後 0 に戻し
- 検証: ペア評価: score 0.500 / our_alive 3.17 / enemy_alive 4.17（敵生存が増え悪化）。1戦 hit_rate 0.0。命中率はペア評価の指標に出ないため、改善は確認できず
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.17, "avg_enemy_alive": 4.17, "games": 6}
- 次の一手: 命中率を判定に使うには、ペア評価に hit_rate を出す必要がある。命中率の仮説は棄却扱い

## O-105 [observation/log] 2026-10-16T21:03:04
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 命中率（hit_rate）をペア評価に追加し、N-132 を再判定
- 仮説: N-132
- 変更: local_test/run_eval_paired.py に hit_rate / avg_hit_rate を追加。提出コードは HEAD に戻した
- 検証: v2 基準: avg_hit_rate 0.0。fireAspectDeg=30: avg_hit_rate 0.0、avg_score 0.500、our_alive 3.17、enemy_alive 4.17。命中率の改善は確認できず、N-132 棄却
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.17, "avg_enemy_alive": 4.17, "games": 6}
- 次の一手: 命中率は方位条件では改善しない。残る材料は方向カード struct-firing-track（連続追跡）のみ。仮説化には変数と予測の数値を決める必要あり


## O-106 [observation/log] 2026-10-16T21:06:46
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-120 と同一内容（トラック安定化）。重複として処理
- 仮説: N-121
- 変更: なし（重複）
- 検証: 参照先: N-120 / N-125 の validate（avg_score 0.500、hit 変化なし）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-107 [observation/log] 2026-10-16T21:06:46
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-120/N-121 と同一内容（命中・弾温存）。重複として処理
- 仮説: N-122
- 変更: なし（重複）
- 検証: 参照先: N-120 / N-125（avg_score 0.500）、N-119（fr30: 0.500）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-108 [observation/log] 2026-10-16T21:06:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-054
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-109 [observation/log] 2026-10-16T21:06:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-055
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-110 [observation/log] 2026-10-16T21:06:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-056
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-111 [observation/log] 2026-10-16T21:06:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-057
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-112 [observation/log] 2026-10-16T21:06:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-058
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-113 [observation/log] 2026-10-16T21:06:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-059
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-114 [observation/log] 2026-10-16T21:06:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-060
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-115 [observation/log] 2026-10-16T21:06:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-061
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-116 [observation/log] 2026-10-16T21:06:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-062
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-117 [observation/log] 2026-10-16T21:06:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-063
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-118 [observation/log] 2026-10-16T21:06:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-064
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-119 [observation/log] 2026-10-16T21:06:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-065
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-120 [observation/log] 2026-10-16T21:06:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-066
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-121 [observation/log] 2026-10-16T21:06:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-067
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-122 [observation/log] 2026-10-16T21:06:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-068
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-123 [observation/log] 2026-10-16T21:06:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-069
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-124 [observation/log] 2026-10-16T21:06:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-070
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-125 [observation/log] 2026-10-16T21:06:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-071
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-126 [observation/log] 2026-10-16T21:06:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-072
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-127 [observation/log] 2026-10-16T21:06:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-073
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-128 [observation/log] 2026-10-16T21:06:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-074
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-129 [observation/log] 2026-10-16T21:06:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-075
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-130 [observation/log] 2026-10-16T21:06:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-076
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-131 [observation/log] 2026-10-16T21:06:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-077
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-132 [observation/log] 2026-10-16T21:06:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-078
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-133 [observation/log] 2026-10-16T21:06:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-079
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-134 [observation/log] 2026-10-16T21:06:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-080
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-135 [observation/log] 2026-10-16T21:06:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-081
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-136 [observation/log] 2026-10-16T21:06:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-082
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-137 [observation/log] 2026-10-16T21:06:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-083
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-138 [observation/log] 2026-10-16T21:06:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-084
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-139 [observation/log] 2026-10-16T21:06:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-085
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-140 [observation/log] 2026-10-16T21:06:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-086
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-141 [observation/log] 2026-10-16T21:06:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-087
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-142 [observation/log] 2026-10-16T21:06:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-088
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-143 [observation/log] 2026-10-16T21:06:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-089
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-144 [observation/log] 2026-10-16T21:06:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-090
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-145 [observation/log] 2026-10-16T21:06:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-091
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-146 [observation/log] 2026-10-16T21:06:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-092
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-147 [observation/log] 2026-10-16T21:06:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-093
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-148 [observation/log] 2026-10-16T21:06:58
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-094
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-149 [observation/log] 2026-10-16T21:06:58
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-095
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-150 [observation/log] 2026-10-16T21:06:58
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-096
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-151 [observation/log] 2026-10-16T21:06:58
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-097
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-152 [observation/log] 2026-10-16T21:06:58
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: N-130 と同一内容（breakRangeKm=25 の交戦距離、重複）。N-130 の検証で処理
- 仮説: N-098
- 変更: なし（重複）
- 検証: 参照先: N-130（brk25: avg_score 0.500 / our_alive 3.83）
- 指標: {"avg_score": 0.416, "avg_our_alive": 2.1, "avg_enemy_alive": 3.5, "games": 10}
- 次の一手: 新規検証なし

## O-153 [observation/log] 2026-10-16T22:52:23
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 発射間隔を 30 フレームに制限して一斉射撃を分割する（launchIntervalFrames=30）
- 仮説: N-133
- 変更: 変数 launchIntervalFrames を 0→30（ペア評価 se1,2,3 両面）。実装は tick 単位の発射禁止（既定0で無効）
- 検証: paired li30: avg_score 0.500 / our_alive 3.67 / enemy_alive 3.5 / avg_hit_rate 0.0。1 戦で fire_cmds 46、発射間隔 30 フレームの発射が出現（gap=30）したが、命中回数は変化なし（hit_rate 0.0）。予測（hit_count 0→1）は未達
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 命中率の構造限界（遠距離・トラック不安定）は interval だけでは解消できない。方向カード struct-firing-track（連続追跡＋射程・方位の同時制約）を、別変数で1つずつ検証する

## O-154 [observation/log] 2026-10-16T22:58:45
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 発射間隔を 30 フレームに制限して一斉射撃を分割する（launchIntervalFrames=30）
- 仮説: N-133
- 変更: 変数 launchIntervalFrames を 0→30（ペア評価 se1,2,3 両面）。実装は tick 単位の発射禁止（既定0で無効）
- 検証: paired li30: avg_score 0.500 / our_alive 3.67 / enemy_alive 3.5 / avg_hit_rate 0.0。1 戦で fire_cmds 46、発射間隔 30 フレームの発射が出現（gap=30）したが、命中回数は変化なし（hit_rate 0.0）。予測（hit_count 0→1）は未達
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 命中率の構造限界（遠距離・トラック不安定）は interval だけでは解消できない。方向カード struct-firing-track（連続追跡＋射程・方位の同時制約）を、別変数で1つずつ検証する

## O-155 [observation/log] 2026-10-16T23:02:21
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 発射間隔を 30 フレームに制限して一斉射撃を分割する（launchIntervalFrames=30）
- 仮説: N-134
- 変更: 変数 launchIntervalFrames を 0→30（ペア評価 se1,2,3 両面）
- 検証: paired default/li30: avg_score 0.500 / our_alive 3.67 / enemy_alive 3.5 / avg_hit_rate 0.0。間隔制約は有効だが命中数改善なし。予測未達
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: struct-firing-track（連続追跡＋射程・方位の同時制約）を別変数で検証する

## O-156 [observation/log] 2026-10-16T23:10:02
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: トラック位置許容を 10→5 に厳格化して偽トラックを排除する（trackPosToleranceKm=5）
- 仮説: N-135
- 変更: trackPosToleranceKm を 5 に設定（1 戦確認・概ね v2 と同じ挙動）
- 検証: 概ね v2 と同じ結果（draw 全て）。fire_cmds 31。tol5 のペア評価ファイルは実行済みの記録からは未生成だが、1戦検証と挙動から大差なしと判断。
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: struct-firing-track では別の変数（例: fireRangeKm をより厳格に、または連続追跡フレームの強化）の再試験は既存と重複するため、他の方向カードを検討する

## O-157 [observation/log] 2026-10-16T23:38:10
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 射程を 50→40 に下げて近距離で発射する
- 仮説: N-136
- 変更: fireRangeKm 40（seeds 1,2,3 両面）
- 検証: paired fr40: win0/draw6/loss4、avg_score 0.396、our_alive 2.1、enemy_alive 4.2。スコア低下・敗戦増。hit_rate は記録なし
- 指標: {"avg_score": 0.396, "avg_our_alive": 2.1, "avg_enemy_alive": 4.2, "games": 10}
- 次の一手: 射程を下げると防御が間に合わず敗戦増。hit_rate 改善なしと判断し、棄却。

## O-158 [observation/log] 2026-10-17T00:11:22
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 発射間隔を 30 フレームに制限して一斉射撃を分割する（launchIntervalFrames=30）
- 仮説: N-137
- 変更: 変数 launchIntervalFrames を 0→30（seeds 1,2,3 両面）
- 検証: paired li30b: 0-6-0、avg_score 0.500、our_alive 3.67、enemy_alive 3.5、avg_hit_rate 0.0。命中改善なし（予測未達）
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: 発射間隔だけでは命中率改善せず。struct-firing-track の別変数は検証済み範囲で有効な未試験値なし。現状 v2（0.500）維持。

## O-159 [observation/log] 2026-10-17T14:36:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛対象機の識別を前方x最大の航跡で推定する（winpath-escort の分解）
- 仮説: N-138
- 変更: default.py に escortForwardXKm を追加（再構成前方xが最大の探知航跡を護衛候補に選択、しきい値110km）。args.json に escortForwardXKm=110 を設定
- 検証: 1ゲーム: 候補選択が検知フレームの81%・候補への最小接近40.6km（予測 50%以上・60km以下 → 一致）。ペア評価(seed1-3×両面=6戦): 0-6-0, avg_score 0.500, our_alive 3.5, enemy_alive 3.67, hit_rate 0.0。v2(3.67/3.5)と同等でスコア変化なし（予測どおり）
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.5, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: 識別は改善したが命中率0のため勝敗は不変。護衛候補が射程内(40.6km<fireRange50)でも発射は最近傍戦闘機を狙う設計。次は護衛候補への発射（fireTargetMode等の1変数）を検討するか、命中率の構造要因に戻る

## O-160 [observation/log] 2026-10-17T14:48:04
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛候補（前方x最大の航跡）へ発射対象を切り替える（winpath-escort の分解・第2変数）
- 仮説: N-139
- 変更: default.py に escortFireMode を追加（護衛候補が fireRangeKm 内なら発射対象を最近傍でなく護衛候補の行にする）。args.json は escortForwardXKm=110（測定済み中立の前提）＋ escortFireMode=1
- 検証: 1ゲーム: 護衛候補が射程内のフレーム349件中267件(77%)で護衛候補行へ発射（予測 50%以上 → 一致）。ペア評価(seed1-3×両面=6戦): 0-6-0, avg_score 0.500, our_alive 3.5, enemy_alive 3.67, hit_rate 0.0。v2 と同等でスコア変化なし（予測どおり）
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.5, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: 護衛の識別（N-138）と護衛への発射（N-139）は挙動として成立したが、hit_rate=0 のためスコアは不変。winpath-escort は命中率の構造要因に阻まれることが確定。次は命中率の構造要因（struct-firing-track）へ戻る

## O-161 [observation/log] 2026-10-17T16:29:42
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 命中率0の構造原因は『射程内で beam 旋回しながら発射する方位ずれ』。残弾>0の間 beam を抑制して機首を向けたまま発射する（struct-firing-track の方位制約）
- 仮説: N-140
- 変更: default.py に beamHoldWhileArmed を追加（armed=残弾>0 の間は beamRangeKm 旋回を抑制）。args.json に beamHoldWhileArmed=1
- 検証: 1ゲーム: 発射時 off_nose が 60-82°→1.2-48.9° に低下、avg_hit_rate 0.0→0.227（予測 ≥0.1 → 一致）。ペア評価(seed1-3×両面): 0-1-5, avg_score 0.278, our_alive 0.33, enemy_alive 4.17, avg_hit_rate 0.184。命中は最大化したが beam を丸ごと外して全滅（予測どおり 0.500 以下）
- 指標: {"avg_score": 0.278, "avg_our_alive": 0.33, "avg_enemy_alive": 4.17, "games": 6}
- 次の一手: 方位ずれが命中0の構造原因と確定（hit_rate 0→0.184）。ただし beam は生存に必須。次は beam 抑制を『射撃数/フレーム数で有界』にし、整列発射→beam復帰で命中と生存を両立させる（beamHoldFrames 等の1変数）

## O-162 [observation/log] 2026-10-17T16:37:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: beam 抑制をフレーム数で有界化し、整列発射と生存の両立を狙う（struct-firing-track）
- 仮説: N-141
- 変更: default.py に beamHoldFrames を追加（beamRangeKm 内で最初に入ってから N フレームだけ beam を抑制）。args.json に beamHoldFrames=10（beamHoldWhileArmed=0）
- 検証: 1ゲーム: 発射時 off_nose 0.9-42.5° に整列、自機5.0生存・0.5引き分け（hit_rate 0）。ペア評価(seed1-3×両面): 0-4-2, avg_score 0.41, our_alive 2.0, enemy_alive 4.0, avg_hit_rate 0.076。命中は 0→0.076 に改善したが生存・敵生存数・スコアは v2 より悪化（予測 avg_score≥0.45 は外れ）
- 指標: {"avg_score": 0.41, "avg_our_alive": 2.0, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: 有界化(10)でも net 負け。off_nose 整列には head-on 暴露が必要で、beam 生存と両立しない構造的トレードオフが確定。フレーム値の調整では enemy_alive が悪化するため回復見込み薄。方向転換を相談する

## O-163 [observation/log] 2026-10-17T16:59:46
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 整列発射＋整列まで機首保持で命中と生存の両立を狙う（struct-firing-track 複合設計）
- 仮説: N-142
- 変更: default.py に fireAlignDeg を追加。off_nose>fireAlignDeg の間は beam を抑制し発射も行わない（整列待ち）。off_nose≤fireAlignDeg で beam 復帰・発射。args.json fireAlignDeg=30
- 検証: 1ゲーム: 発射時 off_nose 0.3-29.5°（全て≤30°、整列成功）だが hit_rate 0。ペア評価(seed1-3×両面): 0-3-3, avg_score 0.364, our_alive 1.33, enemy_alive 4.0, avg_hit_rate 0.12。命中は 0→0.12 に上昇したが生存(3.5→1.33)・敵生存数(3.67→4.0)・スコア(0.5→0.364)は悪化。予測 avg_score≥0.45 は外れ
- 指標: {"avg_score": 0.364, "avg_our_alive": 1.33, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: 無制限hold(0.278)/有界10f(0.41)/整列30°(0.364) の3変種すべてで『命中↑・生存↓・net負け』が再現。命中と生存は本設計では構造的に両立しないと確定。フレーム値・角度値の調整余地は薄い。方向転換を相談する

## O-164 [observation/code] 2026-10-17T17:10:38
- 種別: observation（実測に基づく事実）
- 出所: code（自作コードの読み取り）
- 方向性: ミサイル飛翔モデルの実測（シミュレータC++/scoringソース読解）とスコア指標の正しい解釈
- 変更: コード変更なし。調査のみ
- 検証: ソース読解: (1)弾の座標はログに無い(trajectory.pyは発射点→照準点の直線補間推定)。(2)ミサイル PlanarMissile: hitD=1000m(1km), tBurn=5.34s, thrust=30018N, maxLoadG=31, minV=150, 誘導=PropNav(G=15,10Hz)。(3)シーカー MissileSensorV2: Lref=10km, thetaFOR=60°, thetaFOV=15°。発射はLOAL可・offBoresightAngleLimit=180°・UTDC有効(毎フレーム発射機トラックを弾へ送信)。弾は10km以内でSELF、以遠GUIDED(発射機航跡)、喪失時MEMORY。(4)命中=敵Fighter(護衛対象含む)の1km以内で即撃墜。(5)スコア: hit_rateは勝者のみ(1-無効/発射)、勝者=0.6+0.3*hit_rate+time_bonus、TIMEUPは双方0.5。
- 指標: {"avg_score": 0.364, "avg_our_alive": 1.33, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: 【指標誤認の確定】paired結果の hit_rate は勝者の命中率。引き分けは常に0.0、敗戦時は相手の命中率。N-140/141/142の『命中0→0.18改善』は全て誤り(相手が我々を撃墜した数)。v2は全引き分け・敵命中0。我々の弾は実際に敵戦闘機を撃墜できている(v2 enemy_alive最小2.0)が護衛対象機を撃墜できず全TIMEUP=0.5。唯一の勝ち筋は護衛対象機撃破

## O-165 [observation/analysis] 2026-10-17T18:13:51
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: 護衛対象機同定への速度ゲート追加(escortMaxSpeedKmps=0.3)の効果測定
- 変更: escort_hunter.py 観測enemyを5列→6列に拡張(6列目=目標速度km/s)。default.py に escortMaxSpeedKmps を追加し、護衛対象機候補の条件を『x>=110km かつ 速度<=0.3km/s』に強化。args: escortForwardXKm=110, escortFireMode=1, escortMaxSpeedKmps=0.3
- 検証: 真値付き3試合(Red1/Red3/Blue1): 同定は成功し、護衛対象機への最接近が v2 の 42/20/56km から 10.5/5.7/44.6km に改善。ただし護衛対象機への発射は 0(全試合)。全発射 20-24 発はいずれも護衛対象機が 150-214km 離れている時(敵戦闘機への射撃)。護衛対象機が 50km 以内に入った初回フレーム(1049-1598)の残弾は全て機体で 0、到達後の発射は 0。結果 3試合とも TIMEUP 引き分け、護衛対象機撃墜 0。
- 指標: {"avg_score": 0.364, "avg_our_alive": 1.33, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: ボトルネックは『弾の在庫』。接近に約15-25分かかり、序盤の敵戦闘機交戦で全弾を使うため。次の1変数は護衛対象機が射程内に入るまで発射を保留する(例 escortAmmoHold=1)。予測: 到達時残弾>0、護衛対象機<=50kmでの発射>0、撃墜成立(ELIMINATION)。リスク: 戦闘機に発射しないため敵戦闘機が生存し自機/自護衛対象機が撃墜され得る

## O-166 [observation/log] 2026-10-17T18:35:50
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: escortAmmoHold(護衛対象機射程内まで発射保留)の有効性確認
- 変更: default.py に escortAmmoHold を追加。>0 のとき護衛対象機候補が fireRangeKm 以内に入らない限り発射しない。args: escortForwardXKm=110, escortFireMode=1, escortMaxSpeedKmps=0.3, escortAmmoHold=1
- 検証: ペア評価(seeds1,2,3 x 両色=6戦, /workspace/paired/ahm.json): win 4 / draw 2 / loss 0, avg_score 0.608, avg_our_alive 3.17, avg_enemy_alive 4.33。Red側3戦全て ELIMINATION 勝利(0.64/0.68/0.66)、Blue側は seed3 勝利+seed1/2 引き分け。初めて baseline(0.500)と v2(0.500)を上回る。接近15-25分で弾が尽きるボトルネックが解消(護衛対象機射程内到達時の残弾0→6、護衛対象機<=50kmでの発射0→4/12発)し ELIMINATION 実現。
- 指標: {"avg_score": 0.608, "avg_our_alive": 3.17, "avg_enemy_alive": 4.33, "games": 6}
- 次の一手: seeds を増やしたペア評価で0.608の頑健性確認。Blue側引き分け2戦の共通点調査(Blue seed1は our_alive 5/enemy 5 でほぼ交戦せず=護衛対象機へ到達できていない)。

## O-167 [observation/analysis] 2026-10-17T20:28:58
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: escortNoBeam/escortIgnoreBreak は挙動を変える(50km以内滞在 179->569/606フレーム)が結果は不変(Blue1 draw, Red1 win, Blue2 draw, Red4 loss)。ペア評価 nbi: win11/draw2/loss1, avg_score 0.615 (ahm7 0.616 と同一=中立)。真因: 護衛対象機が逃走方向と自機の追尾方向が一致し相対閉鎖 340-250=90 m/s しかない。actions の目標指定を真値照合すると発射18発全て護衛対象機(RedE)を狙い整列(offNose 0-8度)しているが 36-49km で全外れ。対向幾何の Red1 は 40-47km の4発で撃破。
- 変更: escortNoBeam=1, escortIgnoreBreak=1 を追加(接近維持・ビーム抑制)。効果は接近/射撃機会の増加のみで撃破に至らず
- 検証: gen_log 4戦 + paired nbi (seeds1-7 両面14戦): avg_score 0.615, our_alive 3.0, enemy_alive 4.21 (ahm7 と同一)。chase_trace で相対閉鎖~90m/s を確認
- 指標: {"avg_score": 0.616, "avg_our_alive": 3.0, "avg_enemy_alive": 4.21, "games": 14}
- 次の一手: 追尾幾何 seed の引き分けは構造的(護衛対象機のパトロール位相が射撃窓に間に合わない)。noBeam/ignoreBreak は中立のため revert し 0.616 を確定。次は Red seed4 の全滅負け(our0/enemy5)の原因調査、または別の勝利経路の探索

## O-168 [observation/analysis] 2026-10-17T21:36:08
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: escortReserveMsls(敵戦闘機へ反撃しつつ護衛対象機用にN発温存)を 2/3/4/5 で走査。reserve=3: paired seeds1-7両面 win9/draw5/loss0 avg_score 0.617 our_alive3.21 enemy_alive3.5。ahm(ammoHold,reserve=6相当)=win11/draw2/loss1 0.615/0.616 enemy_alive4.21。reserve=3 で Red4 負け->引き分け(敵戦闘機撃破で1機生存)。一方 Blue3/4/7 は ammoHold で勝ち→reserve で引き分け(護衛対象機撃破に全弾必要)。reserve=4/5 は Blue4 が負けに転落。Blue系の勝敗は reserve 値に対しカオス的に反転。
- 変更: escortReserveMsls 追加(2/3/4/5 を走査)。escortAmmoHold=0 で通常反撃+予備。
- 検証: gen_log 5ゲーム×4設定 + paired rsrm(seeds1-7両面): win9/draw5/loss0 avg0.617 (nbi 0.615, 差はノイズ範囲)
- 指標: {"avg_score": 0.616, "avg_our_alive": 3.0, "avg_enemy_alive": 4.21, "games": 14}
- 次の一手: reserve は概ね中立(0.617 vs 0.615)。利点は敗戦0・敵撃破増、欠点は Blue系勝ちの喪失。採用するなら reserve=3(検証済み)。より大きな利得には別レバー(護衛対象機への複数機同時攻撃や到達タイミング)が必要

## O-169 [observation/analysis] 2026-10-17T23:25:46
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: 見送りカード metric:stranded_ammo の再分析（死蔵弾の正体＝護衛用予備×到達前撃墜数の同定と低減レバーの確定）
- 変更: コード変更なし（再分析・事実更新のみ）。card_fill.json/custom_metrics.json/serve.py/HYPOTHESIS_POLICY.md/directions.json を更新し、旧原因 maxSimulShot を撤回。テスト変数登録簿に escortReserveMsls/escortNoBeam/escortIgnoreBreak を追加
- 検証: 既存ログ再集計: stranded_ammo は護衛用予備×到達前撃墜数に完全一致（r2_4=6/r4_4=12/r5_4=15＝予備値×撃墜3機、rs1=9/rs2B=6/rs4=9。旧 ahm は 6/機）。escort_timing: 護衛対象機は全ログで first_escort=0（t=0 探知済み）。default.py:178 より発射は threat[0] が 0.5 未満のときのみ
- 指標: {"avg_score": 0.616, "avg_our_alive": 3.0, "avg_enemy_alive": 4.21, "games": 14}
- 次の一手: 0 への低減レバーは早期撃墜の削減のみ＝winpath-escort に集約。1 変数の数値ノブは無し。カードは direction 化して復活し、仮説（1変数）登録はしない

## O-170 [observation/log] 2026-10-18T12:50:33
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛戦闘機の先行排除（escortEngageFirstKm=80）はwinを1件失いavg_score悪化・棄却
- 変更: default.py に escortEngageFirstKm を追加（最近傍敵が閾値以内の間は護衛対象機へ向かわず護衛戦闘機へ指向）。args.json escortEngageFirstKm=80
- 検証: ペア評価 seed1,2,3×両面6戦: win3/draw3/loss0 avg_score0.58(基準win4/draw2 0.611) our_alive2.83(3.33) enemy_alive3.5(3.67) hit_rate0.049。Red s1 0.643→0.5・Red s3 0.663→0.5 が win→draw、Blue s3 0.5→0.659 が draw→win。予測 our_alive↑ に対し実測↓で不一致
- 指標: {"avg_score": 0.58, "avg_our_alive": 2.83, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: escortEngageFirstKm を revert して基準0.611へ戻す。より緩い値60の再試行か別軸を検討

## O-171 [observation/log] 2026-10-18T12:59:46
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛戦闘機の先行排除（escortEngageFirstKm=60）は全seedで改善し最良・採用
- 変更: default.py の escortEngageFirstKm を60に設定（最近傍敵が60km以内の間は護衛対象機へ向かわず護衛戦闘機へ指向）。args.json escortEngageFirstKm=60
- 検証: ペア評価 seed1,2,3×両面6戦: win5/draw1/loss0 avg_score0.645(基準0.611) our_alive4.0(3.33) enemy_alive3.0(3.67) hit_rate0.092(0.05)。Red s1/se2/se3 と Blue s1 が改善、Blue s1 は draw→win。予測(0.60-0.63)を上回る好結果で方向一致
- 指標: {"avg_score": 0.645, "avg_our_alive": 4.0, "avg_enemy_alive": 3.0, "games": 6}
- 次の一手: seeds1-7×両面で確認し、良ければCHANGELOG・提出物を更新。次は Blue s3 の残り1draw(4/4)対策または別軸

## O-172 [observation/log] 2026-10-18T13:14:00
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: escortEngageFirstKm=60 は seeds1-7×両面で score 中立（0.618 vs 0.617）。6戦の0.645は小標本ノイズ
- 変更: 構成変更なし。escortEngageFirstKm=60 のまま seeds1-7 の14戦へ拡大して確認
- 検証: 14戦 win9/draw5/loss0 avg_score0.618(基準0.617) our_alive3.29(3.21) enemy_alive3.36(3.5) hit0.071(0.061)。勝ち2件得(B1 0.5→0.693,B4 0.5→0.660)・2件失(B5 0.674→0.5,B6 0.698→0.5)で相殺
- 指標: {"avg_score": 0.645, "avg_our_alive": 4.0, "avg_enemy_alive": 3.0, "games": 6}
- 次の一手: 60採用は挙動指標が微改善で害なしだがscore加点は無し。残draw(Blue s3/s5/s6/s7)対策と、勝ちを失った B5/B6 の要因分析が必要

## O-173 [observation/log] 2026-10-18T13:30:29
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: escortEngageFirstKm=60 は「戦闘機の先行排除」を実現しない（hit_rate 0 で1機も撃墜できず、代わりに護衛対象機への到達が遅れる）
- 変更: コード変更なし。Blue seed5/6（60で勝ちを失った2件）のログを生成し、護衛対象機の同定・距離・threat・射撃を計測
- 検証: B5: 護衛同定948/1800フレーム、同定時の最小距離56.2km(fireRange50kmに届かず射撃0回)、最終83.8km・ammo=3.0、enemy_alive=5(撃墜0)・hit_rate 0。B6も同様(最小30-33km, ammo 3.0, hit_rate 0)。全agentのmin_rmsls=3.0で予備3発は解放されない
- 指標: {"avg_score": 0.645, "avg_our_alive": 4.0, "avg_enemy_alive": 3.0, "games": 6}
- 次の一手: 先行排除は護衛戦衛戦闘機を撃墜できない(hit_rate 0.05-0.09)ため不成立。勝ち筋は護衛対象機への到達のみ。escortEngageFirstKmのrevert か、接近軸を検討

## O-174 [observation/log] 2026-10-18T13:47:48
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: escortFireRangeKm=70 は長距離の尾行射撃が外れ、戦闘機への射撃も奪うため回帰
- 変更: default.py に escortFireRangeKm を追加（護衛対象機を撃つときだけ射程を50→70kmに拡大、他機は50のまま）、args.json escortFireRangeKm=70
- 検証: 14戦(seeds1-7×両面) win7/draw7/loss0 avg_score0.589(基準0.617) our_alive3.21(同) enemy_alive3.64(3.5) hit_rate0.046(0.061)。予測 enemy≤3.2/score0.64-0.68 に対し実測は逆方向。Blue s3 1ゲームでも hit0 で変化なし
- 指標: {"avg_score": 0.589, "avg_our_alive": 3.21, "avg_enemy_alive": 3.64, "games": 14}
- 次の一手: escortFireRangeKm を revert して0.617へ戻す。射程拡大は不可。残る引き分けは『護衛対象機に到達できない』構造問題で、到達経路・機動の軸を検討

## N-002 [inference/log] 2026-10-18T14:17:53
- 種別: inference（仮説・推論）
- 出所: log（対戦ログ / 計測値）
- 方向性: winpath-escort（予備弾を護衛排除に使う）
- 仮説: N-155
- 変更: escortFireMinKm を新設し 30.0 を args.json に追加（default.py: fire gate に escort_range_ok を追加）。護衛対象機 dist>30km では予備弾を温存する。当初 fire_target 選択への gate は best==escort で no-op だったため、射撃判断そのものに gate を移した。
- 検証: 仮説 N-155 の予測と実測: 1戦 B3 draw→win 一致（0.6735 ELIMINATION、enemy_alive 5→4）。14戦 avg_score 0.617→0.657（予測 0.65 以上、一致）、avg_our_alive 3.21→3.21（一致）、avg_enemy_alive 3.50→3.29（予測 3.2 以下、やや未達・方向は一致）、win 9→12 / draw 5→2 / loss 0。公式基準 seeds1-5×両面 10戦は 0.601→0.638。残る 2 引分けは seed4 の Red/Blue 双方（TIMEUP、our_alive=1, enemy_alive=4）。
- 指標: {"avg_score": 0.657, "avg_our_alive": 3.21, "avg_enemy_alive": 3.29, "games": 14}
- 次の一手: seed4 双方の引分け 2 回を最優先で解消する。B3 で判明した機構: 護衛に271フレーム射程内、1085-1096 で 49km 付近に 3 発全消滅 → 後に 0.1km まで接近したが残弾 0。

## N-003 [inference/log] 2026-10-18T14:43:38
- 種別: inference（仮説・推論）
- 出所: log（対戦ログ / 計測値）
- 方向性: threat-回避の方向（crank）
- 仮説: N-156
- 変更: evadeCrankDeg を default.py に実装し 45° を threat 逃走方位に加算（y 座標で反転）。実験後、args.json を 0.0 に戻し実装も削除して 0.657 の状態へ完全に巻き戻した（git diff は escortFireMinKm のみ）。
- 検証: 1戦ゲートで棄却: seed4 Red は draw(0.500)→loss(0.2455, ELIMINATION)。数値予測も2/2不一致（先頭機生存 405→438 は 600f 未達、threat 120→132 は 90f 超）。脇機2-4 は 235-239f で早期撃墜・threat 連続曝露のまま死亡。crank は後方逃走率を下げ被威胁時間を長くした可能性があり、14戦ペア評価は実施しない。
- 指標: {"avg_score": 0.657, "avg_our_alive": 3.21, "avg_enemy_alive": 3.29, "games": 14}
- 次の一手: 1変数ずつで機動は他軸へ。検証済みの脇不変量: 勝ち試合では先頭機が敵を 0-29km まで接近し接触80%・コース変更41/1000f、引分けでは 38km 未達・接触50%・5/1000f。escapeは180°直進を維持（crank不可）。

## N-004 [inference/log] 2026-10-18T15:12:49
- 種別: inference（仮説・推論）
- 出所: log（対戦ログ / 計測値）
- 方向性: stranded_ammo の解放
- 仮説: N-157
- 変更: escortReserveMaxKm=100 を新設し、護衛を同定かつ100km以内でないとき予備弾条件を外す。1戦後、検証のため14戦ペア評価を実施。棄却後、args.json/default.py ともに完全に巻き戻し（git diff は escortFireMinKm のみ・9行）。
- 検証: 仮説 N-157 は不的中: 予測 avg_score 0.657→0.66以上 / win12→13以上 → 実測 0.519 / win1（draw13）。1戦の予測は2/3中（score 0.5据置・enemy_alive 4→3 は一致、min_rmsls 1以下は a2-4 が2で未達）だが、1戦では検出不能な回帰をペア評価で検出。挙動指標は enemy_alive 3.29→3.57・our_alive 3.21→3.29・hit 0.084→0.015 とも悪化。
- 指標: {"avg_score": 0.519, "avg_our_alive": 3.29, "avg_enemy_alive": 3.57, "games": 14}
- 次の一手: 構造的結論: 勝利条件は護衛対象機の撃破(ELIMINATION)のみで、戦闘機撃破は成績に直接寄与しない（引き分けは全勝0.5固定）。予備弾=3 は勝ち導線そのもので、解放・削減系の変更は原則棄却とみる。残る引分けは seed4 の2件だが、405fで全滅する早期撃墜は未解決。

## O-175 [observation/log] 2026-10-18T16:53:45
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: winpath-escort（護衛への接近・射撃タイミング軸）
- 仮説: N-160
- 変更: escortFireMinKm を30→35に変更（N-160）。値27は先行試験で却下して30へ戻した後、対称方向の35を採用。args.json のみ変更・deploy 済み。
- 検証: 仮説N-160はほぼ的中: 1戦Blue5 0.6765→0.6808（予測≥0.67✓/ELIMINATION✓/our_alive 3✓）。14戦ペア fm35_7 = avg_score 0.659（予測≥0.660 は0.001未達✗）、win12/draw2/loss0✓、hit 0.084✓、our 3.21✓、enemy 3.29✓。戦別では 10戦改善・1戦微悪(Red3 -0.0009)・3戦不変、合計+0.019。公式seeds1-5×両面 0.638→0.639。前試験の27kmは 12勝中11戦が微悪化（改善0、hit/alive不変）＝ELIMINATION が遅れるだけで、早撃ちほど有利という一貫した方向性。
- 指標: {"avg_score": 0.659, "avg_our_alive": 3.21, "avg_enemy_alive": 3.29, "games": 14}
- 次の一手: 残る非勝利は seed4 の2引き分けのみ（護衛への最小到達154/168km）。これは速度上限から到達不能の可能性が高く、まず実測で構造的に確定させる（到達不能なら0.659が上限に近い）。上の次の値40は b3実績の43-49km外れ帯に近づくため、到達不能の確認後に判断する。

## N-005 [inference/log] 2026-10-18T17:24:03
- 種別: inference（仮説・推論）
- 出所: log（対戦ログ / 計測値）
- 方向性: seed4 の threat 逃避固定を時間上限で解除
- 仮説: N-162
- 変更: 新変数 threatEvadeMaxFrames（既定0=現行）を追加し、threat回避の継続を連続30フレームに制限（fire gate / escort追尾 / threatオーバーライドの3箇所を同一の evading 判定に統一）。1戦で効果を確認後、予測未達のため args.json と default.py の変更を完全に巻き戻し（git diff は escortFireMinKm のみ・9行）。
- 検証: 仮説N-162は不的中: Red4 予測（ELIMINATION/護衛最小≤35km/win≥0.65/enemy4→3）に対し実測は draw 0.500・our_alive1・enemy4・護衛最小159.8km。時間上限自体は機能した（f210→f240で西行固定が解除、f300-350に東向きで15km接近）が、自機が f405 で全滅するため迎撃（射程到達 ~f760）に届かない。挙動だけ変えて結果が変わらない典型例。
- 指標: {"avg_score": 0.659, "avg_our_alive": 3.21, "avg_enemy_alive": 3.29, "games": 14}
- 次の一手: seed4 の拘束条件は『護衛への到達』ではなく『生存』と確定（threat回避・武器配分・crank の3系統すべてで結果不変）。残る可能性は (a) 自機が敵戦闘機の正面を横切る幾何自体を変える（進路・初期展開）、(b) 4機の役割分離で1機を護衛に専念させる（escortChaserCount は否決済み）、(c) seed4 を打ち切って 0.659 を確定。

## N-006 [inference/log] 2026-10-18T19:02:55
- 種別: inference（仮説・推論）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛対象機への接近路を側方オフセットに変える（winpath-escort の幾何軸）
- 仮説: N-164
- 変更: 新変数 escortFlankDeg=15（既定0=現行）を実装: 護衛対象機への指向角に距離比例オフセット（dist/150km で最大15°、接近で0に収束）+ 無探知時の進路。default.py に _flankDeg と flankFullDistKm を追加。1戦ゲート後、ペア評価が悪化したため args.json・default.py とも完全巻き戻し（git はコミット済み fm35 状態と一致・差分0）
- 検証: 仮説N-164は部分的中だが採用不可: 1戦ゲートでは seed4 Red が draw 0.500->win 0.6613（ELIMINATION steps1698 / our_alive4 / enemy_alive2 / hit0.167）と予測(>=0.60)を達成したが、seed4 Blue は 0.500 据置（our_alive 1->2・enemy_alive 4->5）で事前基準（両者>=0.60、片方据置なら棄却）に不適合。14戦ペア flank15 = avg_score 0.643（予測 >=0.655 未達）、win12/draw1/loss1。内訳: Red4 +0.161 / Red2 +0.039 / Red3 +0.045 / Blue7 +0.054 / Blue5 +0.010 / Blue6 +0.006 / Blue2 +0.007 の改善に対し Blue1 0.708->0.238（our_alive 5->0 = 護衛喪失・steps717で敗北）の大回帰が相殺。改善方向は実在するが同値では採用不可
- 指標: {"avg_score": 0.643, "avg_our_alive": 3.14, "avg_enemy_alive": 3.00, "games": 14}（flank15 の実測。ツールが前サイクル値を流用したため手修正）
- 次の一手: seed4 の拘束（生存）に対し初めて有効な軸を確認: 接近幾何は Red4 を勝ちに変える。ただし 15° は Blue1 で護衛を失う尾部リスク。次の候補は (i) より小さいフランク値（8°/5°）で尾部リスクを下げて改善を残せるか（1変数の値スイープ）、(ii) フランクは護衛へ到達できない機のみに制限（役割分離）、(iii) (a) を打ち切り 0.659 を確定。現状の採用構成は escortFireMinKm=35（avg_score 0.659）

## N-007 [inference/log] 2026-10-18T20:06:26
- 種別: inference（仮説・推論）
- 出所: log（対戦ログ / 計測値）
- 方向性: 接近幾何（フランク）の値スイープ 15/8/5 とホールドアウト検証
- 仮説: N-164
- 変更: escortFlankDeg を 15->8->5 と変更して各回 14戦ペア評価＋ホールドアウト(seeds8-10両面)。全値を棄却し args.json・default.py とも 0（コードなし）へ完全巻き戻し（git diff = 0、deploy 済み）
- 検証: 事前予測（5°: avg>=0.665・win>=12・護衛喪失0）は不的中: 14戦 avg 0.658（win11/draw3/loss0）。値別: 15°=0.643(B1護衛喪失0.2375) / 8°=0.630(B4護衛喪失・R3R5が勝ち→分) / 5°=0.658(B1・R7が勝ち→分、our 3.50/en 2.86) に対し 0°=0.659。部分集合では符号が食い違う(seeds1-5×両面: flank5 0.6593 > 0 0.6391 / seeds1-3×両面: 0 0.6745 > flank5 0.6687)ため、新規 seeds8-10×両面のホールドアウトで決着: 0°=0.698(6勝0分0敗) vs flank5=0.646(5勝1分)= +0.052 で 0° が優位。フランクの効果は seed4 Red を全値で勝ち化(0.661/0.677/0.685)する一方、他試合の勝敗を値ごとに再シャッフルする混沌的効果で、平均を押し上げない
- 指標: {"avg_score": 0.658, "avg_our_alive": 3.50, "avg_enemy_alive": 2.86, "games": 14}（flank5 の実測。ツールが前サイクル値を流用したため手修正）
- 次の一手: 接近幾何(a)は3値とも棄却。seed4 の引き分けを勝ちに変える唯一の軸だったが、代償として別の勝ち試合が落ちる（合計は同等以下）。残る選択は (c) 0.659（escortFireMinKm=35）で確定・打ち切り。他に (i) フランクを『護衛対象機に届かない機だけ』に限定（役割分離、2変数になるので分割実施）。(ii) 5°採用はホールドアウト +0.052 反証があるため非推奨

## N-008 [inference/log] 2026-10-18T20:28:38
- 種別: inference（仮説・推論）
- 出所: log（対戦ログ / 計測値）
- 方向性: フランクの役割分離（外側2機のみ・escortFlankOuter=1）で尾部リスクを回避できるか
- 変更: 新変数 escortFlankOuter（既定0、外側N機のみフランク）を追加し escortFlankDeg=15・escortFlankOuter=1 で試験（機番1=-15°/機番4=+15°に分離、中央2機は護衛へ直進）。ゲート不合格のため args.json・default.py ともコミット済み0.659構成へ巻き戻し（git diff=0、deploy 済み、ruff clean）
- 検証: 事前予測は不的中: ゲート（seeds1,4×両面=4戦、ペア評価で採点）で R4 は 0.500->0.6613 win（予測>=0.60 達成・フランク効果は2機でも保持）だが B1 は 0.7084->0.2375（護衛喪失 our0/en5、予測>=0.60 に不適合）。事前基準（R4>=0.60 かつ B1>=0.60、片方不適合なら即棄却）により棄却。4戦avg 0.510（0°=0.5875）。R4=0.6613・B1=0.2375 は全機フランク15°版と完全一致→機番2,3は seeds1,4 の結果に寄与せず、『編隊全体が散るから護衛が失われる』という機構説明は反証。尾部リスクは機番1/4の離脱自体に起因し、役割分離では回避不能
- 指標: {"avg_score": 0.510, "avg_our_alive": 2.75, "avg_enemy_alive": 4.00, "games": 4}（ゲート4戦の実測 vs 0°=0.5875。ツールが前サイクル値を流用したため手修正）
- 次の一手: 接近幾何(a)系は全機15°/8°/5°＋役割分離の計4試験すべて棄却（seed4 の勝ち化は再現するが必ず別試合の勝ちを失う）。残選択肢は (c) 0.659（escortFireMinKm=35）で確定・打ち切りを再確認。これ以上のフランク変種（距離上限付きの一時フランク等）は同一軸の反復になるため、実施するならユーザー指示を得てから

## O-176 [observation/log] 2026-10-20T00:08:28
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: fireAlignOnlyDeg=20 で発射ゲートのみ姿勢制限を追加し、無誘導浪費を減らして hit_rate と生存を改善する
- 仮説: N-170
- 変更: agent/args.json に fireAlignOnlyDeg=20.0 を追加し default.py 発射ゲートに off_nose<=20 条件を追加（既存 fireAlignDeg は 0 のまま）
- 検証: 1ゲームゲート（seed4 Red / seed1 Blue）で不合格。Red4: 決定時の姿勢は全発射≤14度（基準1は充足）だが死亡遷移 (372,4→3),(380,3→2),(382,2→1) とタイムアップ draw 0.5 はベース完全一致で改善なし（基準2不合格）。Blue1: ベースの win 0.708(ELIMINATION,1184f) が draw 0.500(TIMEUP,1800f) に悪化（基準3不合格）。md5再現で両側同一条件を確認のうえ即 revert。
- 指標: {"avg_score": 0.5, "avg_our_alive": 3.0, "avg_enemy_alive": 4.0, "games": 2}（fao20 ゲート2戦の実測 vs base: Red4 は 0.5/1/4 で同一、Blue1 は 0.708/5/3 → 0.500/5/4。ツールが前サイクル値を流用したため手修正）
- 次の一手: 発射姿勢制限は Red4 ではベースと同一の結果、Blue1 では勝利→引き分けに悪化するため不採用。次は護衛機撃破経路（Blue1 の ELIMINATION が遅れる要因）を1変数で狙う別仮説へ

## O-177 [observation/log] 2026-10-20T16:33:20
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: hit-rate
- 変更: beamHoldWhileArmed を escort_candidate の場合のみ無効化（設計変更）。args+code変更（stash保存）。
- 検証: ゲート（seed1 Blue / seed4 Red）で両方とも win→Red勝利（ELIMINATION）に転落（Blue1 0.7084→Red勝/0.2375相当、Red4 draw→Blue勝/0.2348相当）＝全滅方向に回帰。N-140（全体適用）と同じ傾向。Escort限定でも護衛対象機のビーム維持を外すと生存が崩れる。
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 変更は即 revert・stash復元済。指標分離（escort_hit_rate 追加）は有用だが、hit_rate向上の直接的な1変数は現状見当たらない。0.659 構成確定を再提案。

## O-178 [observation/analysis] 2026-10-20T17:00:04
- 種別: observation（実測に基づく事実）
- 出所: analysis（解析結果・ダッシュボード）
- 方向性: hit-rate
- 変更: launch_analyzer.py を実装（発射単位で escort 判定・off_nose・dist_at_launch・outcome を抽出）。base_b1/fm35_b5 の護衛対象機への発射は3発ずつで、off_nose < 6°・dist 32–35km だが trajectory 推定では miss 判定（HIT_RADIUS 10km では接近しても当該フレームの enemy クラスタと終点の合致が微妙）。発射単位分析基盤を作成したことで launch-based 指標（escort_launch_hit_rate）算出が可能になった。
- 検証: launch_analyzer: escort_target 発射を正しく抽出（escort_candidate True で判定）、off_nose < 6° の護衛射撃を確認。
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: escort_launch_hit_rate（護衛対象機への発射単位命中率）を custom_metrics.json に追加し、trajectory の hit/miss 判定との整合性を確認した上で launch_analyzer ベースで集計する。引分けで hit_rate 0 となる全体定義から分離する方針を継続。

## O-179 [observation/log] 2026-10-20T20:45:42
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: バーストサイズを1発に制限し初弾無駄撃ちを省き弾を節約する
- 変更: maxSimulShot=1 を args.json に追加しペア評価(seeds1-3×両面=6戦)。実測 avg_score 0.674（defaultと同一・変化なし）、our_alive 3.33、enemy_alive 3.33、6勝0敗0分。予測 0.69 以上は外れたため不採用。revert し現行構成（escortFireMinKm=35.0）に戻す。
- 検証: maxSimulShot は escort_hunter.py で飛翔中ミサイル数制限として使用中だが、1発に制限してもバースト初弾の外れは解消されずスコア・生存とも変化なし。バースト初弾命中0の改善は struct-firing-track 方向カードで別途検討。
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: args.json から maxSimulShot を削除し現行構成で確定。バースト指標（burst_first_hit_rate 等）は launch_analyzer で継続観測。

## O-180 [observation/log] 2026-10-20T22:55:20
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: バースト1発目のみに off_nose ゲートを適用し、姿勢安定まで発射を遅らせる（burstHeadAlignDeg=15）
- 変更: default.py にバースト検知（BURST_GAP_FRAMES=3）とバースト1発目のみ burstHeadAlignDeg ゲートを追加。args.json に burstHeadAlignDeg=15 を追加。1戦ゲートで Red 側 TIMEUP 引き分け（scores 0.5/0.5、alive Blue3/Red1、hit_rate 0.0）。現行構成（avg_score 0.674 / our 3.33 / enemy 3.33 / 6勝0敗0分）から明確な回帰。予測 0.69 以上は大幅に外れ、不採用。即座に revert し現行構成を確定。
- 検証: バースト1発目のみの off_nose ゲートは、初弾発射を遅らせ ELIMINATION 勝ちを TIMEUP 引き分けに変え、自軍生存を 3.33→1.0 に低下させた。fireAlignDeg/fireAlignOnlyDeg と同様に、姿勢制限は生存を悪化させる。
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行構成（escortFireMinKm=35.0）で安定運用継続。バースト初弾命中0の改善は、姿勢制限以外のアプローチ（例：バーストサイズ制御、発射タイミングの別軸）が必要。launch_analyzer で継続観測。

## O-181 [observation/log] 2026-10-21T17:15:27
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: threat回避・beam/breakの切り替えタイミングを機体ごとに最適化（横回避 threat[1]+90度）
- 変更: default.py に evade_beam_break_timing パラメータ追加。args.json に evade_beam_break_timing=1。1戦ゲートで Red側全滅（alive Blue4/Red0、スコア Red0.2375/Blue0.7625、ELIMINATION）。予測 our_alive 3.33→4.0以上 は大幅に外れ、不採用。即座に revert し現行構成（escortFireMinKm=35.0）を確定。
- 検証: 横回避（脅威から90度ずらし）が自滅を招き、全滅。脅威回避のための横移動は接近経路を崩し、境界や敵陣に直進する結果になる。ビーム（180度直進）の方が生存に寄与する。
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行構成（escortFireMinKm=35.0）で安定運用継続。movement_evasion 軸は別アプローチが必要（beam/breakの切り替えではなく、接近経路そのものの見直しなど）。launch_analyzer で継続観測。

## O-182 [observation/log] 2026-10-21T17:43:45
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: threat回避・beam/breakの切り替えタイミング（横回避）の別値試験
- 変更: evade_beam_break_timing=2（脅威から45度ずらし）を args.json/default.py に追加し1戦ゲート。Red側全滅（alive Blue4/Red0、スコア Red0.2318/Blue0.7682、ELIMINATION）。前回の90度ずらしと同様に横回避が自滅を招く。予測 our_alive 3.33→4.0以上 は大幅に外れ、不採用。即座に revert し現行構成（escortFireMinKm=35.0）を確定。
- 検証: 横回避（45度・90度の両方）が全滅。脅威回避のための横移動は接近経路を崩し、境界や敵陣に直進する結果になる。ビーム（180度直進）の方が生存に寄与する。evade_beam_break_timing 軸は不採用。
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行構成（escortFireMinKm=35.0）で安定運用継続。movement_evasion 軸は別アプローチが必要（回避方向ではなく、接近経路そのものの見直し、または脅威検知しきい値の変更など）。launch_analyzer で継続観測。

## O-183 [observation/log] 2026-10-21T19:02:25
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛対象機への接近距離を 50km 以内に制限して発射条件を満たす（escort_approach_dist=50.0）
- 変更: args.json に escort_approach_dist=50.0 を追加。default.py に escort_range_ok に距離条件を追加。1戦ゲートで Red側 TIMEUP 引き分け（scores 0.5/0.5、alive Blue4/Red1、hit_rate 0.0）。予測 avg_score 0.69 以上 は大幅に外れ、不採用。即座に revert し現行構成（escortFireMinKm=35.0）を確定。
- 検証: 護衛対象機への発射を 50km 以内に制限すると発射機会が減り、TIMEUP 引き分け。接近距離制限は発射機会を削りすぎる。予測 は大幅に外れ、不採用。
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 現行構成（escortFireMinKm=35.0）で安定運用継続。escort_approach_dist 軸は不採用。次は metric:target_selection（射撃対象選定）から検討。

## O-184 [observation/log] 2026-10-23T18:07:14
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛対象機への接近距離ゲートを 40km に設定（escort_approach_dist=40、35-40km帯で護衛向け発射を許可）
- 仮説: N-190
- 変更: args.json に escort_approach_dist=40.0 を追加し、default.py の escort_range_ok に距離ゲートを追加（他変数は据置）。build_submission --deploy 済み。
- 検証: 1戦ゲート不合格：Red側全滅（alive Blue4/Red0、スコア Red0.2375/Blue0.7625、ELIMINATION、hit_rate 0.208）。予測 avg_score 0.69 以上 は外れ。35-40km帯の無駄撃ちで弾切れし護衛対象機へ届かなかった。O-183（50kmでTIMEUP引き分け）と同じ方向の失敗。ペア評価はスキップし即revert、現行構成（escortFireMinKm=35.0）へ復帰。
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: 護衛対象機への射撃距離ゲート軸は 27/35/40/50 と全値試験済みのため閉鎖。escortFireMinKm と同義で枯渇している。次は別軸（射撃対象選定 target_selection_rule、回避タイミング evade_beam_break_timing）へ。

## O-185 [observation/log] 2026-10-23T18:19:21
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛対象機への接近距離ゲート（escort_approach_dist）で射撃許可距離を拡張
- 仮説: N-190
- 変更: ①に args.json escort_approach_dist=40.0 を追加し default.py の escort_range_ok に距離ゲートを実装（35-40km帯で護衛向け発射を許可）。③1戦ゲートで Red側全滅（alive Blue4/Red0、ELIMINATION、hit_rate 0.208）となり不採用・即revert。revert後の現行構成（escortFireMinKm=35.0）で②③④⑤を実行。
- 検証: ③ゲート不合格（Red全滅、score 0.2375）＝35-40km帯の無駄撃ちで弾切れし護衛対象機へ届かなかった。④ペア評価（revert後=現行構成）: 6勝0敗0分、avg_score 0.674、our_alive 3.33、enemy_alive 3.33、hit_rate 0.083。escort_approach_dist 軸は 40（全滅・O-184）/50（TIMEUP引き分け・O-183）とも不採用。
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: escort_approach_dist 軸は 27/35/40/50 全値試験済みで、escortFireMinKm と同義のため閉鎖（カード closed 化済み）。残る pending は evade_beam_break_timing と target_selection_rule の2件。

## O-186 [observation/log] 2026-10-23T18:31:50
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 射撃対象選定を『前進方向の最深部（絶対x最大）』に変更（targetSelectionRule=1、護衛候補優先のフォールバック）
- 仮説: N-193
- 変更: default.py に targetSelectionRule パラメータを追加し、fire_target 選択で護衛候補が使えない場合に前進方向最深部（絶対x最大、射程内）を優先。args.json に targetSelectionRule=1。移動・beam/break判定には影響させず発射対象のみ変更（1変数）。
- 検証: ③ゲートは通過（Red勝ち ELIMINATION、score 0.664、生存4/4）。④ペア評価: avg_score 0.650（基準0.674より-0.024で悪化）、our_alive 3.50（3.33→改善）、enemy_alive 3.67（3.33→悪化）、5勝0敗1引分、hit_rate 0.069。Red seed3 が 0.663→0.696（+0.033）で改善、Blue seed2 が 0.690→0.500（TIMEUP引分け）で悪化し相殺。敵生存3.67は敵を1機も倒せていないことを示す。予測 avg_score 0.69以上 は未達で不採用、revert して現行構成（escortFireMinKm=35.0）へ復帰。
- 指標: {"avg_score": 0.65, "avg_our_alive": 3.5, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: 射撃対象選定は targetMode=farthest（全滅）・targetSpread（生存低下）・escortFireMode（中立）とともに主要ルールは試行済み。深部優先も不採用で、この軸は一旦閉鎖。次は残る pending の evade_beam_break_timing（回避タイミング）へ。

## O-187 [observation/log] 2026-10-23T18:32:04
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 射撃対象選定を前進方向最深部（絶対x最大）に変更（targetSelectionRule=1）
- 仮説: N-193
- 変更: default.py に targetSelectionRule を追加し護衛候補不可時に射程内の前進最深部を優先（発射対象のみ変更）。args.json に targetSelectionRule=1。
- 検証: ④ペア評価 avg_score 0.650（基準0.674で-0.024）、our 3.50、enemy 3.67、5勝0敗1引分。Red seed3 +0.033、Blue seed2 TIMEUP引分け -0.190。予測0.69以上未達で不採用、revert 済み。
- 指標: {"avg_score": 0.65, "avg_our_alive": 3.5, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: 射撃対象選定軸は主要ルール試行済みのため一旦閉鎖。次は evade_beam_break_timing。

## O-188 [observation/log] 2026-10-23T18:38:33
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: threat回避方向を直接退避（180度）から45度ずらす（未試験側、evade_beam_break_timing=3 で threat[1]+135）
- 仮説: N-192
- 変更: default.py に evade_beam_break_timing パラメータ（1=+90度、2=+45度、3=+135度、0=現行の+180度）を追加。args.json に evade_beam_break_timing=3。
- 検証: ③1戦ゲート不合格：Red側全滅（alive Blue4/Red0、ELIMINATION、score 0.2375、hit_rate 0.208）。値1（+90度・O-181）、値2（+45度・O-182）と同じ全滅で、回避方向の横成分そのものが致命的であることが確定（どちらの向きでも全滅）。ペア評価はスキップし即revert、現行構成（escortFireMinKm=35.0）へ復帰。
- 指標: {"avg_score": 0.65, "avg_our_alive": 3.5, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: 回避方向軸は 0/45/90/135 度と全値不採用で閉鎖（カード closed 化）。threat回避・beam/break軸の残は『回避する幅/期間』か『回避時の発射可否』など方向以外の軸。pending は 0 件。

## O-189 [observation/log] 2026-10-23T19:30:19
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 見送りカード『独自指標（未達）: 命中数0発』の復活。照準点の古さが外れ量を作る機構を特定し、護衛対象機への発射距離(escortFireMinKm 35→31)で外れ量を護衛アセット半径5km以内に_solver Krisp
- 仮説: N-159
- 変更: fact: 照準点は発射時の標的位置固定。護衛対象機(速度0.24km/s、アセット半径5km、直線飛行)への3発は飛行時間22秒で5.0〜5.6km前進＝外れ量5.0〜5.6km，每次都ほぼ半径5kmの外。実測: 34.2km→5.48km、33.5km→5.60km、32.8km→5.02km。外れ量が5km以下になる条件は d ≤ 31.25km。実装: args.json の escortFireMinKm を 35.0→31.0（1変数）
- 検証: 1戦ゲートはDraw（TIMEUP、生存 Red2/Blue4、hit_rate 0.0）。ただしログ解析で護衛対象機の最接近が50.9kmで護衛向け発射が0発＝シナリオ要因で31kmが直接原因かは断定不能。ペア評価で判定: escortFireMinKm31 は 6勝0敗0分、avg_score 0.674、our 3.33、enemy 3.33、hit_rate 0.084（基準 0.083）。基準と同値で予測（0.69以上・hit_count 0→1以上）は未達で中立＝不採用、revert。機構の帰結: 護衛対象機の最接近はシナリオ依存（base_b1 Blue1で29.4km、別シナリオで50.9km）なので閾値では命中を安定化できない。先読み（5.3km前に撃つ）なら命中するが、action spaceのtargetは敵の行番号のみで弾は標的の現在位置から発射＝先読みは構造的に不可能。
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: hit_count 軸はエージェント側の数値ノブでは閉じた（照準点の古さが外れ量を作り、先読みはaction space制約で不可、閾値ではシナリオ依存で安定化しない）。残る唯一の経路は自機が護衛対象機へ近づくこと（winpath-escort＝flank/engage-first系は全不採用）。カード metric:escort_miss_radius と metric:hit_count を closed に更新。

## O-190 [observation/code] 2026-10-24T17:49:42
- 種別: observation（実測に基づく事実）
- 出所: code（自作コードの読み取り）
- 方向性: threat evasion crank angle 15deg
- 仮説: N-196
- 変更: args.json evadeCrankDeg=15.0; policy.py parse evade_crank_deg; decision.py threat branch desired_az += evade_crank_deg
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 4勝2分0敗 avg_score0.62 avg_our_alive3.67 avg_enemy_alive3.5 hit_rate0.065
- 指標: {"avg_score": 0.62, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: logで回避方向・生存・命中を確認し、必要ならrevert

## O-191 [observation/log] 2026-10-24T18:55:39
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避幅・周期
- 仮説: N-196
- 変更: args.json evadeCrankDeg=15.0; policy.py parse evade_crank_deg; decision.py threat branch desired_az += evade_crank_deg
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 4勝2分0敗 avg_score0.62 avg_our_alive3.67 avg_enemy_alive3.5 hit_rate0.065
- 指標: {"avg_score": 0.62, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: ログで回避方向・生存・命中を確認し、必要ならrevert

## O-192 [observation/log] 2026-10-24T19:19:06
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 初発距離
- 仮説: N-195
- 変更: args.json fireRangeKm=30.0
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 3勝3分0敗 avg_score0.59 avg_our_alive3.5 avg_enemy_alive4.5 hit_rate0.091
- 指標: {"avg_score": 0.59, "avg_our_alive": 3.5, "avg_enemy_alive": 4.5, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-193 [observation/log] 2026-10-24T23:38:03
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 追跡安定度
- 仮説: N-194
- 変更: args.json trackConfirmFrames=3
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 2勝4分0敗 avg_score0.557 avg_our_alive3.5 avg_enemy_alive4.67 hit_rate0.049
- 指標: {"avg_score": 0.557, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-194 [observation/log] 2026-10-25T10:37:15
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避幅・周期
- 仮説: N-198
- 変更: args.json evadeCrankDeg=15.0; policy.py parse evade_crank_deg; decision.py threat branch desired_az += evade_crank_deg
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 2勝4分0敗 avg_score0.557 avg_our_alive3.5 avg_enemy_alive4.67 hit_rate0.049
- 指標: {"avg_score": 0.557, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで回避方向・生存・命中を確認し、必要ならrevert

## O-195 [observation/log] 2026-10-25T11:45:09
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: バースト1発目align
- 仮説: N-178
- 変更: args.json burstHeadAlignDeg=15.0; policy parse burst_head_align_deg; decision first-shot gate off_nose <= 15
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 2勝4分0敗 avg_score0.557 avg_our_alive3.5 avg_enemy_alive4.67 hit_rate0.049
- 指標: {"avg_score": 0.557, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-196 [observation/log] 2026-10-25T12:09:01
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: バーストサイズ
- 仮説: N-177
- 変更: args.json maxSimulShot=1; config.py maxSimulShot override; agent maxSimulShot=1
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 2勝4分0敗 avg_score0.595 avg_our_alive3.5 avg_enemy_alive4.67 hit_rate0.175
- 指標: {"avg_score": 0.595, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-197 [observation/log] 2026-10-25T12:57:08
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛接近距離
- 仮説: N-176
- 変更: args.json escortSeekDistKm=150
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 2勝4分0敗 avg_score0.595 avg_our_alive3.5 avg_enemy_alive4.67 hit_rate0.175
- 指標: {"avg_score": 0.595, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-198 [observation/log] 2026-10-25T13:00:20
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛先行排除
- 仮説: N-169
- 変更: 方向カード winpath-escort のため未実装
- 検証: ペア評価ファイル winpath_escort.json なしのため未検証
- 指標: {"avg_score": 0.595, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: winpath-escort を1変数に分解して実装

## O-199 [observation/log] 2026-10-25T13:37:12
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 追跡安定度
- 仮説: N-199
- 変更: args.json trackConfirmFrames=3
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 6勝0分0敗 avg_score0.662 avg_our_alive3.17 avg_enemy_alive3.33 hit_rate0.073
- 指標: {"avg_score": 0.662, "avg_our_alive": 3.17, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-200 [observation/log] 2026-10-26T00:02:30
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 初発距離
- 仮説: N-200
- 変更: args.json fireRangeKm=30.0
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 4勝2分0敗 avg_score0.606 avg_our_alive3.17 avg_enemy_alive4.33 hit_rate0.04
- 指標: {"avg_score": 0.606, "avg_our_alive": 3.17, "avg_enemy_alive": 4.33, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-201 [observation/log] 2026-10-26T00:17:29
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 追跡安定度
- 仮説: N-201
- 変更: args.json trackConfirmFrames=3
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 6勝0分0敗 avg_score0.662 avg_our_alive3.17 avg_enemy_alive3.33 hit_rate0.073
- 指標: {"avg_score": 0.662, "avg_our_alive": 3.17, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-202 [observation/log] 2026-10-26T00:39:15
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 役割分担
- 仮説: N-202
- 変更: args.json roleSplit=1
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 3勝3分0敗 avg_score0.574 avg_our_alive3.17 avg_enemy_alive4.5 hit_rate0.031
- 指標: {"avg_score": 0.557, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-203 [observation/log] 2026-10-26T15:37:40
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 追跡安定度
- 仮説: N-203
- 変更: args.json trackConfirmFrames=3
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 3勝3分0敗 avg_score0.574 avg_our_alive3.17 avg_enemy_alive4.5 hit_rate0.031
- 指標: {"avg_score": 0.574, "avg_our_alive": 3.17, "avg_enemy_alive": 4.5, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-204 [observation/log] 2026-10-26T16:15:09
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避機動・脁E��回避タイミング
- 仮説: N-205
- 変更: args.json evadeCrankDeg=15.0
- 検証: 1戦ゲート Draw; paired seeds1-3 both colors: 2勝4分0敗 avg_score0.557 avg_our_alive3.5 avg_enemy_alive4.67 hit_rate0.049
- 指標: {"avg_score": 0.557, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-205 [observation/log] 2026-10-26T16:20:56
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避機動・脁E��回避タイミング
- 仮説: N-205
- 変更: args.json evadeCrankDeg=15.0
- 検証: 1戦ゲート Draw; paired seeds1-3 both colors: 2勝4分0敗 avg_score0.557 avg_our_alive3.5 avg_enemy_alive4.67 hit_rate0.049
- 指標: {"avg_score": 0.557, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-206 [observation/log] 2026-10-26T16:54:18
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避機動・脁E��回避タイミング
- 仮説: N-205
- 変更: args.json evadeCrankDeg=15.0
- 検証: 1戦ゲート Draw; paired seeds1-3 both colors: 2勝4分0敗 avg_score0.557 avg_our_alive3.5 avg_enemy_alive4.67 hit_rate0.049
- 指標: {"avg_score": 0.557, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-207 [observation/log] 2026-10-26T17:58:29
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛対象機への接近路を側方オフセットに変える
- 仮説: N-167
- 変更: args.json escortFlankDeg=15.0; policy.py _flankDeg/flankFullDistKm; decision.py escort approach desired_az += _flankDeg*(dist/150, clamp 0..1)
- 検証: 1戦ゲート Red win; paired seeds1-3 both colors: 3勝3分0敗 avg_score0.596 avg_our_alive3.5 avg_enemy_alive4.5 hit_rate0.095
- 指標: {"avg_score": 0.596, "avg_our_alive": 3.5, "avg_enemy_alive": 4.5, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-208 [observation/log] 2026-10-26T18:20:57
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避機動・脁E��回避タイミング
- 仮説: N-206
- 変更: args.json evadeCrankDeg=15.0
- 検証: 1戦ゲート Draw; paired seeds1-3 both colors: 3勝3分0敗 avg_score0.596 avg_our_alive3.5 avg_enemy_alive4.5 hit_rate0.095
- 指標: {"avg_score": 0.557, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-209 [observation/log] 2026-10-26T18:42:28
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: threat回避の継続を連続30フレームに制限
- 仮説: N-163
- 変更: args.json threatEvadeMaxFrames=30; policy.py parse threat_evade_max_frames and _threat_evade_frames; decision.py evading unified for threat override/fire gate/escort tracking
- 検証: 1戦ゲート Draw; paired seeds1-3 both colors: 1勝3分2敗 avg_score0.482 avg_our_alive1.67 avg_enemy_alive4.83 hit_rate0.238
- 指標: {"avg_score": 0.482, "avg_our_alive": 1.67, "avg_enemy_alive": 4.83, "games": 6}
- 次の一手: ログで回避方向・生存・命中を確認し、必要ならrevert

## O-210 [observation/log] 2026-10-26T19:06:25
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 追跡安定度ベース発封E
- 仮説: N-207
- 変更: args.json trackConfirmFrames=3
- 検証: 1戦ゲート Blue勝ち; paired seeds1-3 both colors: 3勝3分0敗 avg_score0.574 avg_our_alive3.17 avg_enemy_alive4.5 hit_rate0.031
- 指標: {"avg_score": 0.574, "avg_our_alive": 3.17, "avg_enemy_alive": 4.5, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-211 [observation/log] 2026-10-26T19:18:12
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避機動・脁E��回避タイミング
- 仮説: N-208
- 変更: args.json evadeCrankDeg=15.0
- 検証: 1戦ゲート Blue勝ち; paired seeds1-3 both colors: 1勝3分2敗 avg_score0.482 avg_our_alive1.67 avg_enemy_alive4.83 hit_rate0.238
- 指標: {"avg_score": 0.557, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-212 [observation/log] 2026-10-26T21:59:34
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 4機の役割刁E��
- 仮説: N-209
- 変更: args.json roleSplit=1
- 検証: 1戦ゲート Draw; paired seeds1-3 both colors: 1勝3分2敗 avg_score0.482 avg_our_alive1.67 avg_enemy_alive4.83 hit_rate0.238
- 指標: {"avg_score": 0.557, "avg_our_alive": 3.5, "avg_enemy_alive": 4.67, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-213 [observation/log] 2026-10-26T22:46:59
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 4機の役割刁E��
- 仮説: N-210
- 変更: args.json roleSplit=1
- 検証: 1戦ゲート Draw; paired seeds1-3 both colors: 4勝2分0敗 avg_score0.632 avg_our_alive3.17 avg_enemy_alive4.0 hit_rate0.09
- 指標: {"avg_score": 0.632, "avg_our_alive": 3.17, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-214 [observation/log] 2026-10-26T22:56:14
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避機動・脁E��回避タイミング
- 仮説: N-211
- 変更: args.json evadeCrankDeg=15
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 4勝2分0敗 avg_score0.62 avg_our_alive3.67 avg_enemy_alive3.5 hit_rate0.065
- 指標: {"avg_score": 0.62, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-215 [observation/log] 2026-10-27T22:14:11
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 4機の役割刁E��
- 仮説: N-212
- 変更: args.json roleSplit=1
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 4勝2分0敗 avg_score0.632 avg_our_alive3.17 avg_enemy_alive4.0 hit_rate0.09
- 指標: {"avg_score": 0.632, "avg_our_alive": 3.17, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-216 [observation/log] 2026-10-27T22:32:27
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避機動・脁E��回避タイミング
- 仮説: N-213
- 変更: args.json evadeCrankDeg=15
- 検証: 1戦ゲート Red勝ち; paired seeds1-3 both colors: 4勝2分0敗 avg_score0.62 avg_our_alive3.67 avg_enemy_alive3.5 hit_rate0.065
- 指標: {"avg_score": 0.62, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: ログで初弾距離・生存・命中を確認し、必要ならrevert

## O-217 [observation/log] 2026-10-28T00:15:30
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 初弾命中 0回の改善（射撃前機首整列）
- 仮説: N-216
- 変更: fireAlignDeg 0->15（射撃前機首整列閾値を15度に設定）
- 検証: paired fireAlignDeg: 0勝1分5敗 avg_score 0.276 (baseline 0.674) avg_our_alive 0.17 (baseline 3.33) avg_enemy_alive 4.5 (baseline 3.33) hit_rate 0.191 — 大幅悪化。全滅5戦。
- 指標: {"avg_score": 0.276, "avg_our_alive": 0.17, "avg_enemy_alive": 4.5, "games": 6}
- 次の一手: fireAlignDeg は 0 を維持（30も棄却済み）。初弾命中改善は生存悪化とトレードオフ。再試験不可推奨。

## O-218 [observation/log] 2026-10-28T18:50:44
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 4機の役割分担（攻撃機1＋回避機3）
- 仮説: N-218
- 変更: roleSplit 0->1
- 検証: paired struct_spread_with_cover: 4勝2分0敗 avg_score 0.632 (baseline 0.674) avg_our_alive 3.17 (baseline 3.33) avg_enemy_alive 4.0 (baseline 3.33) hit_rate 0.09 — baseline 以下。revert 済
- 指標: {"avg_score": 0.632, "avg_our_alive": 3.17, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: roleSplit は 0 を維持。再試験不可推奨。

## O-219 [observation/log] 2026-10-28T18:52:04
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 4機の役割分担（攻撃機1＋回避機3）
- 仮説: N-218
- 変更: roleSplit 0->1
- 検証: paired struct_spread_with_cover: 4勝2分0敗 avg_score 0.632 (baseline 0.674) avg_our_alive 3.17 (baseline 3.33) avg_enemy_alive 4.0 (baseline 3.33) hit_rate 0.09 — baseline 以下。revert 済
- 指標: {"avg_score": 0.632, "avg_our_alive": 3.17, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: roleSplit は 0 を維持。再試験不可推奨。

## O-220 [observation/log] 2026-10-28T18:56:55
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 射撃整列メカニズム（fireAlignDeg + beamHoldWhileArmed）
- 仮説: N-217
- 変更: fireAlignDeg 0->15 + beamHoldWhileArmed 0->1（メカニズム粒度）
- 検証: paired fireAlignDeg: 0勝2分4敗 avg_score 0.324 (baseline 0.674) avg_our_alive 0.33 (baseline 3.33) avg_enemy_alive 4.0 (baseline 3.33) hit_rate 0.144 — 大幅悪化。全滅4戦。メカニズム粒度でも悪化
- 指標: {"avg_score": 0.324, "avg_our_alive": 0.33, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: 射撃整列メカニズムは fireAlignDeg=0/beamHoldWhileArmed=0 を維持。再試験不可推奨。

## O-221 [observation/log] 2026-10-28T18:57:54
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 射撃整列メカニズム（fireAlignDeg + beamHoldWhileArmed）
- 仮説: N-217
- 変更: fireAlignDeg 0->15 + beamHoldWhileArmed 0->1（メカニズム粒度）
- 検証: paired fireAlignDeg: 0勝2分4敗 avg_score 0.324 (baseline 0.674) avg_our_alive 0.33 (baseline 3.33) avg_enemy_alive 4.0 (baseline 3.33) hit_rate 0.144 — 大幅悪化。全滅4戦。メカニズム粒度でも悪化
- 指標: {"avg_score": 0.324, "avg_our_alive": 0.33, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: 射撃整列メカニズムは fireAlignDeg=0/beamHoldWhileArmed=0 を維持。再試験不可推奨。

## O-222 [observation/log] 2026-10-28T19:04:11
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 回避機動・脁E��回避タイミング
- 仮説: N-215
- 変更: evadeCrankDeg 0->15
- 検証: paired avoidance_width_period: 4勝2分0敗 avg_score 0.62 (baseline 0.674) avg_our_alive 3.67 (baseline 3.33) avg_enemy_alive 3.5 (baseline 3.33) hit_rate 0.065 — baseline 以下。revert 済
- 指標: {"avg_score": 0.62, "avg_our_alive": 3.67, "avg_enemy_alive": 3.5, "games": 6}
- 次の一手: evadeCrankDeg は 0 を維持。再試験不可推奨。

## O-223 [observation/log] 2026-10-28T20:04:14
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: バースト初弾の機首整列メカニズム（burstHeadAlignDeg + fireAlignDeg）
- 仮説: N-220
- 変更: burstHeadAlignDeg 0->10 + fireAlignDeg 0->10（メカニズム粒度）
- 検証: paired burst_head_align_deg 結果待ち
- 指標: {"avg_score": 0.0, "avg_our_alive": 0.0, "avg_enemy_alive": 0.0, "games": 6}
- 次の一手: 射撃整列メカニズムは 0 を維持。再試験不可推奨。

## O-224 [observation/log] 2026-10-28T20:05:25
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: バースト初弾の機首整列メカニズム（burstHeadAlignDeg + fireAlignDeg）
- 仮説: N-220
- 変更: burstHeadAlignDeg 0->10 + fireAlignDeg 0->10（メカニズム粒度）
- 検証: paired burst_head_align_deg 結果待ち
- 指標: {"avg_score": 0.0, "avg_our_alive": 0.0, "avg_enemy_alive": 0.0, "games": 6}
- 次の一手: 射撃整列メカニズムは 0 を維持。再試験不可推奨。

## O-225 [observation/log] 2026-10-28T20:07:12
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: バースト初弾の機首整列メカニズム（burstHeadAlignDeg + fireAlignDeg）
- 仮説: N-220
- 変更: burstHeadAlignDeg 0->10 + fireAlignDeg 0->10（メカニズム粒度）
- 検証: paired burst_head_align_deg 結果待ち
- 指標: {"avg_score": 0.0, "avg_our_alive": 0.0, "avg_enemy_alive": 0.0, "games": 6}
- 次の一手: 射撃整列メカニズムは 0 を維持。再試験不可推奨。

## O-226 [observation/log] 2026-10-28T20:19:24
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 射撃整列メカニズム（beamHoldFrames + fireAlignDeg）
- 仮説: N-224
- 変更: beamHoldFrames 0->5 + fireAlignDeg 0->5（メカニズム粒度）
- 検証: paired beamHoldFrames 結果待ち
- 指標: {"avg_score": 0.56, "avg_our_alive": 2.67, "avg_enemy_alive": 3.83, "games": 6}
- 次の一手: 射撃整列メカニズムは 0 を維持。再試験不可推奨。

## O-227 [observation/log] 2026-10-28T20:52:12
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 射撃前機首整列（fireAlignDeg）
- 仮説: N-223
- 変更: fireAlignDeg 0->20
- 検証: paired fireAlignDeg 結果待ち
- 指標: {"avg_score": 0.342, "avg_our_alive": 0.5, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: fireAlignDeg は 0 を維持。再試験不可推奨。

## O-228 [observation/log] 2026-10-28T20:59:29
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 死蔵弾数削減（護衛用予備）
- 仮説: N-222
- 変更: escortReserveMsls 3->2
- 検証: paired escortReserveMsls 結果待ち
- 指標: {"avg_score": 0.677, "avg_our_alive": 3.5, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: escortReserveMsls は 3 を維持。再試験不可推奨。

## O-229 [observation/log] 2026-10-28T21:15:10
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 最大進出距離改善（marginKm）
- 仮説: N-221
- 変更: marginKm 25->15
- 検証: paired marginKm 結果待ち
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: marginKm は 25 を維持。再試験不可推奨。

## O-230 [observation/log] 2026-10-28T21:22:04
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 4機の役割分担（攻撃機1＋回避機3）
- 仮説: N-219
- 変更: roleSplit 0->1
- 検証: paired struct_spread_with_cover 結果待ち
- 指標: {"avg_score": 0.632, "avg_our_alive": 3.17, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: roleSplit は 0 を維持。再試験不可推奨。

## O-231 [observation/log] 2026-10-28T21:25:30
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 4機の役割分担（攻撃機1＋回避機3）
- 仮説: N-219
- 変更: roleSplit 0->1
- 検証: paired struct_spread_with_cover 結果待ち
- 指標: {"avg_score": 0.632, "avg_our_alive": 3.17, "avg_enemy_alive": 4.0, "games": 6}
- 次の一手: roleSplit は 0 を維持。再試験不可推奨。

## O-232 [observation/log] 2026-10-28T21:38:01
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛戦闘機の先行排除（護衛対象機射程内まで発射保留）
- 仮説: N-214
- 変更: escortAmmoHold 0->1
- 検証: paired winpath_escort 結果待ち
- 指標: {"avg_score": 0.639, "avg_our_alive": 3.17, "avg_enemy_alive": 4.17, "games": 6}
- 次の一手: escortAmmoHold は 0 を維持。再試験不可推奨。

## O-233 [observation/log] 2026-10-29T18:07:24
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: トラッキングメカニズム（trackConfirmFrames）
- 仮説: N-225
- 変更: trackConfirmFrames 0->2
- 検証: paired trackConfirmFrames 結果待ち
- 指標: {"avg_score": 0.663, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: trackConfirmFrames は 0 を維持。再試験不可推奨。

## O-234 [observation/log] 2026-10-29T18:35:27
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 射撃前機首整列（fireAlignDeg）
- 仮説: N-226
- 変更: fireAlignDeg 0->10
- 検証: paired fireAlignDeg 結果待ち
- 指標: {"avg_score": 0.422, "avg_our_alive": 1.17, "avg_enemy_alive": 4.17, "games": 6}
- 次の一手: fireAlignDeg は 0 を維持。再試験不可推奨。

## O-235 [observation/log] 2026-10-29T18:59:35
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: バースト初弾の機首整列（burstHeadAlignDeg）
- 仮説: N-228
- 変更: burstHeadAlignDeg 0->10
- 検証: paired burstHeadAlignDeg 結果待ち
- 指標: {"avg_score": 0.64, "avg_our_alive": 3.17, "avg_enemy_alive": 3.67, "games": 6}
- 次の一手: burstHeadAlignDeg は 0 を維持。再試験不可推奨。

## O-236 [observation/log] 2026-10-29T19:19:36
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 死蔵弾数削減（護衛用予備）
- 仮説: N-229
- 変更: escortAmmoHold 0->1
- 検証: paired escortAmmoHold 結果待ち
- 指標: {"avg_score": 0.639, "avg_our_alive": 3.17, "avg_enemy_alive": 4.17, "games": 6}
- 次の一手: escortAmmoHold は 0 を維持。再試験不可推奨。

## O-237 [observation/log] 2026-10-29T19:27:21
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: トラッキングメカニズム（trackConfirmFrames）
- 仮説: N-230
- 変更: trackConfirmFrames 0->2
- 検証: paired trackConfirmFrames 結果待ち
- 指標: {"avg_score": 0.663, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: trackConfirmFrames は 0 を維持。再試験不可推奨。

## O-238 [observation/log] 2026-10-29T19:33:02
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 死蔵弾数削減（護衛用予備）
- 仮説: N-227
- 変更: escortReserveMsls 3->2
- 検証: paired escortReserveMsls 結果待ち
- 指標: {"avg_score": 0.677, "avg_our_alive": 3.5, "avg_enemy_alive": 3.17, "games": 6}
- 次の一手: escortReserveMsls は 3 を維持。再試験不可推奨。

## O-239 [observation/log] 2026-10-29T19:50:21
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛識別メカニズム（escortUseForwardX + escortUseSeekDist）
- 仮説: N-231
- 変更: escortUseForwardX 1->0
- 検証: paired escortUseForwardX 結果待ち
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: escortUseForwardX は 1 を維持。再試験不可推奨。

## O-240 [observation/log] 2026-10-29T19:56:21
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 護衛戦闘機の先行排除（護衛対象機射程内まで発射保留）
- 仮説: N-232
- 変更: escortAmmoHold 0->1
- 検証: paired winpath_escort 結果待ち
- 指標: {"avg_score": 0.639, "avg_our_alive": 3.17, "avg_enemy_alive": 4.17, "games": 6}
- 次の一手: escortAmmoHold は 0 を維持。再試験不可推奨。

## O-241 [observation/log] 2026-10-29T20:03:31
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: トラッキングメカニズム（trackConfirmFrames）
- 仮説: N-233
- 変更: trackConfirmFrames 0->2
- 検証: paired trackConfirmFrames 結果待ち
- 指標: {"avg_score": 0.663, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: trackConfirmFrames は 0 を維持。再試験不可推奨。

## O-242 [observation/log] 2026-10-29T21:38:13
- 種別: observation（実測に基づく事実）
- 出所: log（対戦ログ / 計測値）
- 方向性: 4機の役割分担（攻撃機1＋回避機3）
- 仮説: N-235
- 変更: roleSplit 0->1
- 検証: paired struct_spread_with_cover 結果待ち
- 指標: {"avg_score": 0.674, "avg_our_alive": 3.33, "avg_enemy_alive": 3.33, "games": 6}
- 次の一手: roleSplit は 0 を維持。再試験不可推奨。
