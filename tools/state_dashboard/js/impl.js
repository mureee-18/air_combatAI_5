function renderImpl(d) {
  const a = d.agents || {};
  const args = a.args || {};
  const baseline = {
    "fireRangeKm": 50.0, "breakRangeKm": 35.0, "evadeCrankDeg": 0.0, "marginKm": 25.0,
    "trackConfirmFrames": 0, "targetSpread": 0, "escortSeekDistKm": 150, "escortForwardXKm": 110,
    "escortFireMode": 1, "escortMaxSpeedKmps": 0.3, "escortAmmoHold": 0, "escortNoBeam": 1,
    "escortIgnoreBreak": 1, "escortReserveMsls": 3, "escortFireMinKm": 35.0, "beamHoldWhileArmed": 0,
    "beamHoldFrames": 0, "fireAlignDeg": 0, "launchIntervalFrames": 0, "roleSplit": 0,
    "escortFlankDeg": 0.0, "threatEvadeMaxFrames": 0, "burstHeadAlignDeg": 0.0,
  };
  const desc = {
    "fireRangeKm": "射撃開始距離(km)。遠いほど早く撃てるが弾浪費リスク",
    "breakRangeKm": "ブレイク(離脱)開始距離(km)。近いほど交戦持続",
    "evadeCrankDeg": "回避時の機首ずらし角度(度)。0=真後ろ退避",
    "marginKm": "境界回避マージン(km)。小さいほど深く進出",
    "trackConfirmFrames": "射撃前に必要な連続トラックフレーム数。高いほど安定射撃",
    "targetSpread": "目標分散(0=集中射撃)。味方の射撃先を分散する",
    "escortSeekDistKm": "護衛対象機探索距離(km)。遠い護衛を優先",
    "escortForwardXKm": "護衛対象機の前方x閾値(km)。この距離以上で護衛候補",
    "escortFireMode": "護衛射撃モード(0=最近傍, 1=護衛優先)",
    "escortMaxSpeedKmps": "護衛対象機の最大速度(km/s)。これ以下を護衛候補",
    "escortAmmoHold": "護衛対象機射程内まで発射保留(0=即射, 1=保留)",
    "escortNoBeam": "護衛対象機射撃時にビーム抑制(0=通常, 1=抑制)",
    "escortIgnoreBreak": "護衛対象機射撃時にブレイク無視(0=通常, 1=無視)",
    "escortReserveMsls": "護衛用予備ミサイル数。護衛対象機用に温存",
    "escortFireMinKm": "護衛射撃の最小距離(km)。これ以内で発射",
    "beamHoldWhileArmed": "武装中ビーム保持(0=通常, 1=保持)",
    "beamHoldFrames": "ビーム保持フレーム数。射撃前の整列待ち",
    "fireAlignDeg": "射撃前機首整列角度(度)。この角度以内で発射可",
    "launchIntervalFrames": "発射間隔フレーム数。0=同時発射",
    "roleSplit": "役割分担(0=全機攻撃, 1=攻撃機1+回避機3)",
    "escortFlankDeg": "護衛接近の側方オフセット角度(度)",
    "threatEvadeMaxFrames": "脅威回避の最大フレーム数。0=無制限",
    "burstHeadAlignDeg": "バースト初弾の機首整列角度(度)",
  };
  const keys = Object.keys(args).filter(k => k !== "type" && k !== "specialist").sort();
  let h = '<h2>実装状態（agent/args.json）</h2>';
  h += '<p class="meta">現在の変数値と目的。変数の追加・削除・仕様変更は agent/args.json と policy.py を編集する。</p>';
  h += table([{label:"変数"},{label:"現在値"},{label:"ベースライン"},{label:"目的"}],
    keys.map(k => {
      const cur = args[k];
      const base = baseline[k];
      const changed = (cur !== base && base !== undefined);
      return [
        esc(k),
        esc(String(cur)),
        esc(base !== undefined ? String(base) : "—"),
        esc(desc[k] || "—"),
      ];
    }));
  const changed = keys.filter(k => args[k] !== baseline[k] && baseline[k] !== undefined);
  if (changed.length) {
    h += `<p class="meta warn">ベースラインと異なる変数: ${esc(changed.join(", "))}（${changed.length} 個）</p>`;
  } else {
    h += '<p class="meta ok">全変数がベースラインと一致しています。</p>';
  }
  h += '<h2>変数の追加・削除・仕様変更</h2>';
  h += '<p class="meta">変数を追加するには: (1) agent/args.json にキーを追加、(2) policy.py に self.xxx = args.get("xxx", default) を追加、(3) judgment.py で使用。削除は逆順。仕様変更は policy.py の型変換や judgment.py のロジックを編集。</p>';
  h += cmdRow(
    '実装変更を依頼します。agent/args.json / policy.py / judgment.py を編集して変数を追加・削除・仕様変更してください。具体的な変更内容は私が指定します。',
    "実装変更の指示（OpenCode に貼り付け）", INTENT_IMPL);
  document.getElementById("impl").innerHTML = h;
  bindCopy(document.getElementById("impl"));
}
