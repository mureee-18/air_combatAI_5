# 対戦ログフォーマット（第5回空戦AIチャレンジ / ユース部門）

ローカルで `validate.py` を実行したときに得られるログの構造と、解析時に毎回調べ直さないための
既知事項をまとめる。改善セッション開始時に必ず読むこと。

## 1. 実行と出力場所

```
docker exec atla5-cpu bash -lc "cd /workspace && python validate.py --youth 1 --num-validation 3 --result-dir /workspace/results --visualize 0"
```

- ホスト（Windows）側からは `workspace/results/{agent_id}/` に見える（コンテナの `/workspace` は
  リポジトリの `workspace/` をバインドマウントしている）。
- 出力物
  - `validation_results.json` … 勝敗・スコア集計
  - `log_{fight_n}.json` … 各戦のステップごとの観測/行動/情報

ラッパー:
- `python scripts/run_eval.py --games 3` … 3戦実行して集計を表示
- `python scripts/run_eval.py --games 3 --sweep fireRangeKm=25,35,50` … `args.json` の値を書き換えて走査
- `python tools/battle_analyzer/battle_stats.py workspace/results/0/log_0.json` … 挙動指標の集計
- `python tools/battle_analyzer/trajectory.py workspace/results_tel/0/log_0.json` … 軌跡の復元（要約）
  （ダッシュボードの「自機視点」タブが同じデータを使う。HTTP は `/api/replays` と `/api/replay?log=<repo相対パス>`）

## 2. validation_results.json

```json
{
  "own": "Red",
  "details": {
    "0": {
      "finishedTime": 21.1,
      "step_count": 1035,
      "numAlives": {"Blue": 2.0, "Red": 3.0},
      "endReason": "ELIMINATION",
      "scores": {"Blue": 0.28, "Red": 0.72},
      "hit_rate": 0.2,
      "time_bonus": 0.1,
      "error": false,
      "red_error_message": "",
      "blue_error_message": "",
      "config": { ... }
    }
  },
  "win": 1, "loss": 0, "draw": 0,
  "status": "success",
  "message": "ok"
}
```

- `win` / `loss` / `draw` は合計が必ずしも対戦数にならない（TIMEUP が draw に数えられないことがある）。
  判定には `details[].scores[own]` の平均を使うほうが安全。
- 勝者のスコアは `0.6 + 0.3 * hit_rate + time_bonus`、敗者は `1 - 勝者のスコア`、TIMEUP は双方 0.5。
- `numAlives` は陣営ごと戦闘機4機 + 護衛対象機1機の計5が初期値。
- 終了理由: `ELIMINATION`（どちらかの護衛対象機が撃墜）/ `TIMEUP`（1800 tick = 1800 s）。
- `details[].hit_rate` は `1 - wastedMissiles[winner]/launchedMissiles[winner]` だが、引き分け（`winner='Draw'`）
  では `winner` が陣営名でないため**必ず 0.0 が記録される**（実際の命中率ではない。`fight.py:473`）。
  引き分け戦の hit_rate 比較は無効。命中率は勝敗が付いた戦 or ログ側の発射・命中数から数えること。

## 3. log_{n}.json

```json
{
  "observations": [{"ptime": 0.0, "data": {"1": {...}, "2": {...}}}],
  "actions":     [{"ptime": 0.0, "data": {"1": {"turn": 12, "speed": 1, "target": 0}}}],
  "infos":       [{"ptime": 0.0, "data": {"1": null}}]
}
```

- `data` のキーは**死亡機を除いた生存機の詰め直し番号（`"1"`〜`"N"`）で、死亡のたびに付け替えられる**
  （`fight.py` の `get_data` が生存する `Fighter` だけを順に `1,2,...` で振り直す）。
  したがってキー番号は固定の機体番号ではない。死亡を境に別の機体が同じキーを引き継ぐため、
  **キー単位でフレーム間の機体を追跡してはいけない**（死亡時はキー数が減る事実のみ使える。
  例: `{1..4}→{1..3}` の遷移フレームが機体の死亡時刻）。
  `observations` と `actions` は同じ `get_data` による振り直しを受けるため、**同一フレーム内では両者のキーは一致**
  （obs/act の機体取り違えは発生しない。`key_align.py` で確認済み）。
- 死亡した機体は以降のエントリから消える（観測が無い）。エントリ数 = その機体が生きていたステップ数（キー振り直しのため機体別エントリ数は不可）。
- `infos` は現状ほぼ `null`。観測と行動の組で挙動を追う。
- **baseline（`BasicAACRuleBasedAgent01`）を相手にしたログは observation の payload がスカラー（int）で、
  `actions` の payload が `null` になる。** 3.1/3.2 の dict 構造が現れるのは自作 Agent のログだけ。
  `data` に含まれるのは自分の陣営の機体のみで、相手陣営の機体は載らない。
  → ログ解析ツールは dict payload が存在しないログをBenchMark 用と判定して除外すること。
- 自作 Agent のログでも、Agent の世代差で `own` の長さが変わっている（`float32[8]` の世代と
  現在の `float32[10]`）。`enemy`（5×5）と `threat`（2）は安定している。

### 3.1 自作 Agent（EscortHunterAgent）の Observation

- `own` … float32[10]
  - 0: 陣営座標系 x（敵陣方向が正）[km]
  - 1: 同 y（横方向）[km]
  - 2: 高度 [km]
  - 3: 速さ [m/s]
  - 4: 進行方位 [deg]
  - 5: 場外ラインまでの横方向の余裕 [km]
  - 6: 前方（敵陣側）の余裕 [km]
  - 7: 後方（自陣側）の余裕 [km]
  - 8: 残弾数 `remMsls`
  - 9: 残燃料 `fuelRemaining`
- `enemy` … float32[5, 5]。距離が近い順。
  - 0: 探知フラグ, 1: 方位 [deg], 2: 水平距離 [km], 3: 高度 [km], 4: 護衛対象機フラグ
- `threat` … float32[2]。0: 被弾警報フラグ, 1: 誘導弾の方位 [deg]

### 3.2 Action

`{"turn": int, "speed": int, "target": int}`
- `turn` … turnTable（24分割、15°刻み、-180〜165）の index
- `speed` … speedTable `[220, 280, 340]` の index
- `target` … 0=撃たない、1..5=観測の何行目を撃つか

### 3.3 enemies_direct（敵の絶対座標記録・ローカル対戦専用）

ローカル対戦（`workspace/gen_log.py` / 友軍内検証）でのみ、`src/fight.py` が `record_enemies`
ON のときにログへ追記する。**提出物（`agent/`）のログ出力は一切増えない**。

```json
"enemies_direct": [
  [
    {"id": "BlueF1", "x": 102.203, "y": 3.319, "heading": 328.2, "alive": true},
    {"id": "BlueE",  "x": 115.0,   "y": -21.892, "heading": 90.0, "alive": true}
  ],
  ...
]
```

- `observations` と同じ長さ・同じ順序（観測が記録されたフレームに限る）。各要素がその
  フレームの敵側5機（F1..F4 + E＝護衛対象機）の一覧。
- 座標は**予測ではなくシミュレータ管理オブジェクトの絶対座標の変換値**（自陣フレーム [km]、x=+ が敵方向）:
  - Red 陣営: 変換 `(y_w, -x_w)/1000` ／ Blue 陣営: `(-y_w, x_w)/1000`
  - `heading` は機首方位の記録が無いため `pos` と `pos_prev` の差から求めた**進路方位**（2点の実測による微分・推定ではない）。
- `alive: false` は撃墜済み（dashboard の戦場俯瞰では描画しない）。撃墜後の残像は出さない。
- 実装: `local_test/battle_recorder.py`（`collect_enemy`）。`workspace/src/fight.py` が
  `match_config["record_enemies"]` を契機に読み込む。

## 4. 既知の制約（毎回調べ直さない）

- **`/sensor/track` の航跡に `spec` は含まれない**（pos / vel / time / truth / crs のみ）。
  そのため「spec.sensor.radar が無い = 護衛対象機」という判定は**機能しない**。
  護衛対象機を航跡から識別する手段は現状なし（自作 Agent の `isEscorted` フラグは常に 0）。
- 護衛対象機は `rcsScale=16` で探知距離が約2倍（~150 km）になるため、遠方の航跡として現れる。
  戦闘機のレーダ `Lref` は 80 km、IRST は 120 km。
- **MWS（被弾警報）の探知距離は短い**（`Lref` が 10 km 程度）。警報が出てからの回避はほぼ間に合わない。
- **ユース部門では燃料は消費されない**（`fuelRemaining` は一定）。燃料枯渇は敗因ではない。
- ユース部門は高度 10,000 m 固定・水平面上の戦闘（`PlanarFighter`）。上下機動は意味を持たない。
- 初期配置は自陣営側 x ≈ -100 km、敵護衛対象機は x ≈ +120 km の周回軌道上。
  戦域は `dOut` = `dLine` = 150 km。
- 初期誘導弾数は 6。同時発射は `maxSimulShot`（自作 Agent）/ `nMslSimul`（初期行動判断モデル）で制限。
  飛翔中の誘導弾は最大 150 s（`tMax`）残るため、同時発射数の上限を上げると長時間新しい射撃ができなくなる。
- シミュレータ側の `isLaunchableAt()` が False の場合は action で target を指定しても発射されない。
  したがって「fire_orders」の数と実際の発射数は一致しない（残弾数の推移で確認する）。

## 5. 軌跡の復元（trajectory.py / ダッシュボード「自機視点」タブ）

- 敵の座標は 3.1 の `own` と `enemy` から次の式で復元する（**実測で検証済み**:
  4機が独立に探知した同一敵の推定位置が平均 0.07 km で一致した）。

  ```
  enemy_x = own_x + dist * cos(bearing)
  enemy_y = own_y + dist * sin(bearing)
  ```

  bearing は陣営座標系で `0 = 敵陣方向(+x)`、反時計回りが正。水平面のみ扱う（高度は固定）。
- 復元できるログは**自作 Agent のログだけ**（dict payload が無い baseline / BenchMark は除外）。
- 表示されるのは「そのフレームで当該機が探知していた敵」だけ。未探知の敵は出ない。
- イベント:
  - `launch` … `own[8]`（残弾）が前フレームより減ったとき（`isLaunchableAt()` の都合で
    `target` 指定回数と発射数は一致しない）。`row`（`action.target` の観測行）と
    `dist`（その行の水平距離）が付き、未探知なら `dist: null` /「標的未探知」。
  - `lock` … `actions[].data[].target` が 0 → 非 0 に変化
  - `warning` … `threat[0]` が 0 → 1（`threat[1]` が警報方位）
  - `lost` … あるスロットの観測が以降のフレームから消えた（=`previous_ammo` にあり `own` にない）
  - `detect` / `lose` … **敵の個体IDはログに無い**ので、位置の近傍一致（`DETECT_MATCH_KM: 8.0` km）
    で疑似追跡し、初見を `detect`（消えた track に同一位置で再マッチした場合は「再探知」）、
    **8 フレーム以上連続（`DETECT_MISS_FRAMES`）で観測が切れた場合に `lose`（ロスト）** を出す。
    実ログで多数を占める 1〜3 フレームの欠落（観測行の並び替えや探知のブレ）をロストと誤認しないためのしきい値。
    イベントには `row` / `dist` / `sensor` が付く。感度調整は「話しすぎ」なら `DETECT_MISS_FRAMES`、
    「別目標とくっつく」なら `DETECT_MATCH_KM` を増やす。
  - 全ての `detect` のうち各敵行で最初の 1 件には `first: true` が付き、テキストが
    「敵を最初に発見」になる（個体 ID が無いため行単位の近似）。ダッシュボードではタグ「初発見」で表示。
  - `hit` / `miss` … 誘導弾の**命中推定**（未検証）。弾が照準点に到達したフレームで、
    融合済みの敵（`teams` 内の `side: "enemy"`）と照準点の距離が `HIT_RADIUS_KM = 10.0` km 以内なら
    `hit`（テキストに該当敵 ID と距離）、それ以外は `miss`。ダッシュボードでは「命中/空振り」タグで表示。
- `own` が旧 8 列世代のログは残弾・燃料の列が無いため `launch` イベントは出ない。
- フレームごとの追加フィールド（ダッシュボード「自機視点」タブの表示用）:
  - `aim` … `action.target` が非 0 の間の狙い線。`{slot, row, x, y, dist, escort}`。
    そのフレームの `enemy[row-1]` を座標復元したもの。未探知行なら入らない。
  - `shots` … 飛翔中の誘導弾（**推定**）。`{slot, t0, age, x, y, fx, fy, tx, ty, dist, flight}`。
    **弾の座標はログに入っていない**ので、発射点 `(fx,fy)` → 標的 `(tx,ty)` を直線補間する。
    速度 `MISSILE_SPEED_KMS = 1.5` km/s、飛翔時間は `dist / 1.5` を 5〜60 秒に丸めた値。
    発射点は実測（残弾減のフレームの自機位置）、標的は実測（`action.target` 行の復元位置）。
  - 敵点の `sensor` … `classify_sensor(dist, escort)` による**探知センサの推定**。実ログ実測では
    escort フラグは常に 0 のため、実際は奇数回 `radar`（レーダ ≤80 km）/`irst`（IRST ≤120 km）/
    `far`（>120 km）の 3 種だけ。`rcs` は護衛対象機フラグが立つ場合の「RCS 拡大 ≤150 km」で、合成ログのテスト用。
  - `missile_model` … 上の推定パラメータ（`speed_kms` / `min_sec` / `max_sec`）。
  - `bounds` … 戦域境界 ±150 km。`own[5..7]`（各方向の余裕）と `own.x/y` から
    `x=±150, y=±150` の矩形に一致することを実測確認済み（越境で PENALTY）。
  - `teams` … 両陣営の俯瞰マップ「戦場俯瞰」タブ用の `{side, id, x, y, heading}` 一覧。
    - `own` … ログの **実測**座標（`side: "own"`、`id` はスロット番号）。
    - `enemy` … 3.3 の `enemies_direct` があるログでは**その絶対座標をそのまま使う**
      （`side: "enemy"`、`source: "direct"`、`alive: false` は除外）。無いログ
      （旧ログ・他所のログ）は全機の探知点を近傍クラスタで融合して復元した**推定**位置・方位
      （`id` は `E1..`、`heading` は前フレームとの移動方向、`seen_by` は同時探知機数）。
      最大 `FUSE_MAX_CRAFT = 5` 機。フレーム間は `DETECT_MATCH_KM` の近傍マッチで同 ID を繋ぎ、
      8 フレーム以上見失った track は死骸にし、`FUSE_RETURN_KM = 25` km 以内の再出現なら
      同じ敵として復活させる（実ログ: 一意 ID は 45 個に乱立していたのが 9 個に収束、同時最大 4 機）。
      融合時・記録なしの敵の個体 ID・軌跡は「見失っている間の動きは描けない」ことに注意。
- **`infos` の `score` / `penalty` は全フレーム 0 のまま変化しない**（実測: 1800 フレームで
  値の変化はゼロ）。スコアの時間推移はログから復元できない。
- **武装は誘導弾のみ**（`numMsls` / `remMsls`）。レーザー・ビーム兵器はシミュレータに存在しない
  （`workspace/` 全体を grep して該当 0 件。`beamRangeKm` は自作 Policy の機動パラメータで兵器ではない）。

## 6. ベンチマーク（BenchMark = BasicAACRuleBasedAgent01）

- 状態（ADVANCE / APPROACH_TARGET / KEEP_SENSING / RTB / WITHDRAW / EVADE）を遷移するルールベース。
- BenchMark 同士の対戦は引き分け寄り（TIMEUP が多い）。
- 自作の単純な突撃ロジックは BenchMark に対して全滅しやすい（実測: 平均スコア 0.32 前後）。
  まず BenchMark と同等以上になることが改善の出発点。
