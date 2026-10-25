function renderObservationHtml(obs) {
  const o = obs || {};
  const own = o.own || {};
  const t = o.threat || {};
  let h = '<div><div class="k">観測: 自機</div><div class="v">';
  h += `x ${esc(String(own.x))} / y ${esc(String(own.y))} / 高度 ${esc(String(own.alt))} km<br>`;
  h += `速度 ${esc(String(own.speed))} m/s / 姿勢 ${esc(String(own.heading))}°<br>`;
  h += `残弾 ${esc(String(own.ammo))} / 燃料 ${esc(String(own.fuel))}<br>`;
  h += `マージン side ${esc(String(own.marginSide))} / front ${esc(String(own.marginFront))}`
     + ` / back ${esc(String(own.marginBack))}</div></div>`;
  h += '<div><div class="k">観測: 脅威</div><div class="v">'
     + (t.flag ? `あり（方位 ${esc(String(t.bearing))}°）` : 'なし') + '</div></div>';
  h += '<div><div class="k">観測: 敵</div><div class="v">'
     + (o.enemies || []).map(e =>
         `#${e.row} ${e.det ? `${esc(String(e.dist))}km/${esc(String(e.bearing))}°/速${esc(String(e.speed))}` : '未探知'}`
         + `${e.escort ? ' [護衛]' : ''}`).join('<br>') + '</div></div>';
  return h;
}

function renderDecisionHtml(dec) {
  const d = dec || {};
  const target = d.target;
  let h = '<div><div class="k">判断: 標的</div><div class="v">'
     + (target ? `#${target.row}（${esc(String(target.dist))}km）` : 'なし') + '</div></div>';
  h += '<div><div class="k">判断: 照準</div><div class="v">'
     + (d.aim ? `x ${esc(String(d.aim.x))} / y ${esc(String(d.aim.y))}` : 'なし')
     + (d.off_nose !== null && d.off_nose !== undefined
         ? `<br>機首とのずれ ${esc(String(d.off_nose))}°` : '') + '</div></div>';
  h += '<div><div class="k">判断: 撃てるか</div><div class="v">'
     + (d.can_fire ? '発射可' : '発射不可')
     + `<br>残弾 ${esc(String(d.ammo))} / 脅威 ${esc(String(d.threat))}`
     + (d.fire_range_km !== undefined && d.fire_range_km !== null
         ? `<br>射程 ${esc(String(d.fire_range_km))}km` : '')
     + (d.break_zone ? `<br>break 域内（${esc(String(d.break_range_km))}km）` : '') + '</div></div>';
  return h;
}

function renderActionHtml(act) {
  const a = act || {};
  const turn = a.turn || {};
  const speed = a.speed || {};
  const target = a.target || {};
  let h = '<div><div class="k">行動: 機首</div><div class="v">'
     + `turn ${esc(String(turn.index))}`
     + (turn.value !== null && turn.value !== undefined ? ` = ${esc(String(turn.value))}${esc(String(turn.unit || ""))}` : '')
     + '</div></div>';
  h += '<div><div class="k">行動: 速度</div><div class="v">'
     + `speed ${esc(String(speed.index))}`
     + (speed.value !== null && speed.value !== undefined ? ` = ${esc(String(speed.value))} ${esc(String(speed.unit || ""))}` : '')
     + '</div></div>';
  h += '<div><div class="k">行動: 標的</div><div class="v">'
     + `target ${esc(String(target.index || 0))} 行</div></div>`;
  return h;
}

function renderAircraft(ac) {
  let h = '<div class="fact">';
  h += `<div class="fact-head"><span class="title">機体 ${esc(ac.slot)}</span>`
     + '<span class="badge">観測 / 判断 / 行動</span></div>';
  h += '<div class="fact-grid">';
  h += renderObservationHtml(ac.observation);
  h += renderDecisionHtml(ac.decision);
  h += renderActionHtml(ac.action);
  h += '</div></div>';
  return h;
}

function renderDecision(d) {
  const box = document.getElementById("decision");
  const st = state.decision || (state.decision = { log: "", frame: 0, data: null, logs: null, busy: false });

  if (!st.logs) {
    fetch("/api/replays").then(r => r.json()).then(j => {
      st.logs = (j.entries || []).map(e => e.log);
      if (!st.log && st.logs.length) st.log = st.logs[0];
      renderDecision(d);
    }).catch(() => { box.innerHTML = '<div class="empty">ログ一覧を取得できません。</div>'; });
    if (!st.data) box.innerHTML = '<div class="empty">ログを読み込んでいます…</div>';
    return;
  }
  if (!st.logs.length) {
    box.innerHTML = '<div class="empty">再生できるログがありません。</div>';
    return;
  }

  const loadFrame = () => {
    if (!st.log) return;
    st.busy = true;
    const q = "?log=" + encodeURIComponent(st.log) + "&frame=" + st.frame;
    fetch("/api/decision" + q).then(r => r.json()).then(j => {
      st.data = j;
      st.busy = false;
      renderDecision(d);
    }).catch(() => { st.busy = false; box.innerHTML = '<div class="empty">フレームを取得できません。</div>'; });
  };
  if (!st.data) { loadFrame(); box.innerHTML = '<div class="empty">フレームを読み込んでいます…</div>'; return; }

  const data = st.data;
  const total = data.frames || 0;
  let h = '<div class="verify-pick"><label for="dec-log">ログ</label><select id="dec-log">' +
    st.logs.map(l => `<option value="${attr(l)}"${l === st.log ? " selected" : ""}>${esc(l)}</option>`).join("") +
    '</select></div>';
  h += '<div class="verify-pick"><label for="dec-frame">フレーム</label>' +
    `<input type="number" id="dec-frame" min="0" max="${Math.max(0, total - 1)}" value="${data.frame}" style="width:8em">` +
    ` <span class="meta">/ ${Math.max(0, total - 1)}（ptime ${esc(String(data.ptime))}）</span>` +
    ' <button class="copy" data-cmd="__dec_prev__">◀ 1つ前</button>' +
    ' <button class="copy" data-cmd="__dec_next__">1つ次 ▶</button></div>';
  h += '<p class="meta">観測＝ログが持つ値／判断＝観測と行動から導出した標的の選び方と撃てたか／行動＝turn・speed・target（config.json の表で値に翻訳）。</p>';

  (data.aircraft || []).forEach(ac => { h += renderAircraft(ac); });

  box.innerHTML = h;
  const logSel = document.getElementById("dec-log");
  if (logSel) logSel.addEventListener("change", () => { st.log = logSel.value; st.data = null; renderDecision(d); });
  const fr = document.getElementById("dec-frame");
  if (fr) fr.addEventListener("change", () => { st.frame = parseInt(fr.value, 10) || 0; st.data = null; renderDecision(d); });
  box.querySelectorAll("[data-cmd]").forEach(b => {
    const c = b.dataset.cmd;
    if (c === "__dec_prev__") b.addEventListener("click", () => { st.frame = Math.max(0, st.frame - 1); st.data = null; renderDecision(d); });
    else if (c === "__dec_next__") b.addEventListener("click", () => { st.frame = st.frame + 1; st.data = null; renderDecision(d); });
  });
  bindCopy(box);
}
