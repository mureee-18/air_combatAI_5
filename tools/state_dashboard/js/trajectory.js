const TRAJ_SLOT_COLORS = ["#58a6ff", "#3fb950", "#d29922", "#a371f7"];

const TRAJ_RING_COLORS = { radar: "rgba(88,166,255,0.20)", irst: "rgba(163,113,247,0.18)", mws: "rgba(248,81,73,0.35)" };

const TRAJ_SENSOR_COLORS = { radar: "#58a6ff", irst: "#a371f7", rcs: "#ffd33d", far: "#8b949e" };

const TRAJ_EVENT_COLORS = { lost: "#f85149", lose: "#f85149", warning: "#f85149", launch: "#ff7b72",
                            lock: "#58a6ff", detect: "#3fb950", hit: "#3fb950", miss: "#8b949e" };

const traj = { entries: [], data: null, log: null, t: 0, playing: false, timer: null, sub: 0,
               speed: 1, span: 150, rings: true, trail: true, shots: true, aim: true, toasts: [] };

// キャンバス内の重要イベントの一時表示（発射・命中/空振り・被弾警報・初発見など）。
// 図の中央（自機と敵機の間）を隠さないよう、キャンバス左上の固定バナーに重ねて出す。
// フレーム到達時に pushFrameToasts で追加し、EVENT_TOAST_FRAMES フレーム(1×時)かけてフェードアウトする。

const EVENT_TOAST_FRAMES = 50;

const EVENT_TOAST_TAGS = { launch: "発射", hit: "命中", miss: "空振り", warning: "被弾警報",
                           lost: "撃墜?", lock: "射撃指示", first: "初発見" };

function pushFrameToasts(state, frame) {
  const now = state.t;
  if (state._lastT !== undefined && now < state._lastT) state._toastSeen = new Set();
  state._lastT = now;
  if (!frame) return;
  (frame.events || []).forEach(ev => {
    if (ev.t !== now) return;
    const kind = ev.first === true ? "first" : ev.kind;
    if (!EVENT_TOAST_TAGS[kind]) return;
    const key = now + ":" + kind + ":" + ev.slot;
    if ((state._toastSeen || new Set()).has(key)) return;
    (state._toastSeen = state._toastSeen || new Set()).add(key);
    const toasts = (state.toasts = state.toasts || []);
    while (toasts.length && now - toasts[0].t0 > EVENT_TOAST_FRAMES) toasts.shift();
    toasts.push({ text: ev.text, t0: now, kind, slot: ev.slot });
  });
}

function drawEventToasts(ctx, state) {
  const visible = (state.toasts || []).filter(ev => ev.t0 <= state.t && state.t - ev.t0 <= EVENT_TOAST_FRAMES);
  visible.slice(-4).forEach((ev, i) => {
    const age = state.t - ev.t0;
    const label = (EVENT_TOAST_TAGS[ev.kind] || ev.kind) + " " + ev.text;
    const x = 10, y = 16 * (i + 1);
    ctx.globalAlpha = Math.max(0, 1 - age / EVENT_TOAST_FRAMES);
    ctx.font = "bold 11px Consolas, monospace";
    ctx.lineWidth = 3;
    ctx.strokeStyle = "rgba(11,15,20,0.9)";
    ctx.strokeText(label, x + 1, y);
    ctx.fillStyle = TRAJ_EVENT_COLORS[ev.kind] || "#e6edf3";
    ctx.fillText(label, x, y - 1);
    ctx.globalAlpha = 1;
  });
}

function trajColor(slot) {
  const i = traj.data ? traj.data.slots.indexOf(slot) : -1;
  return TRAJ_SLOT_COLORS[(i < 0 ? 0 : i) % TRAJ_SLOT_COLORS.length];
}

async function loadTrajEntries(force) {
  const box = document.getElementById("traj");
  if (!box) return;
  if (!force && traj.entries.length) return;
  box.innerHTML = '<div class="empty">軌跡データを読み込み中…</div>';
  let payload;
  try {
    const res = await fetch("/api/replays", { cache: "no-store" });
    payload = await res.json();
  } catch (err) {
    box.innerHTML = '<div class="empty">読み込み失敗: ' + esc(err) + '</div>';
    return;
  }
  traj.entries = payload.entries || [];
  if (payload.error) {
    box.innerHTML = '<div class="empty">' + esc(payload.error) + '</div>';
    return;
  }
  if (!traj.entries.length) {
    box.innerHTML = '<div class="empty">再生可能なログがありません。<br>'
      + '軌跡の復元は自作エージェント（EscortHunterAgent）のログのみ対象です。'
      + 'BenchMark 同士のログは observation がスカラー構造で位置情報を持たないため再生できません。</div>';
    return;
  }
  buildTrajShell();
  const keep = traj.entries.some(e => e.log === traj.log);
  const target = keep ? traj.log : traj.entries[0].log;
  document.getElementById("traj-sel").value = target;
  await openTraj(target);
  if (document.getElementById("battle")) {
    buildBattleShell();
    document.getElementById("battle-sel").value = target;
    await openBattle(target);
  }
}

function buildTrajShell() {
  const opts = traj.entries.map(e =>
    `<option value="${esc(e.log)}">${esc(e.log + "  " + e.mtime + "  " + e.frames + "ステップ"
      + (e.has_ammo ? "" : "（残弾列なし）"))}</option>`).join("");
  document.getElementById("traj").innerHTML = `
    <div class="traj-controls">
      <select id="traj-sel">${opts}</select>
      <button id="traj-reload">再読み込み</button>
      <span class="meta">再生可能なログ ${traj.entries.length} 本</span>
    </div>
    <div class="traj-wrap">
      <div class="traj-stage">
        <canvas id="traj-canvas"></canvas>
        <div class="traj-controls">
          <button id="traj-play">▶ 再生</button>
          <input type="range" id="traj-seek" min="0" max="0" value="0">
          <span class="meta" id="traj-time">0 / 0</span>
          <select id="traj-speed">
            <option value="0.5">0.5×（スロー）</option><option value="1" selected>1×</option>
            <option value="2">2×</option><option value="4">4×</option><option value="8">8×</option>
          </select>
          <select id="traj-span">
            <option value="80">80 km</option>
            <option value="150" selected>150 km（戦域全域）</option>
            <option value="300">300 km（広域）</option>
          </select>
          <label><input type="checkbox" id="traj-rings" checked>センサリング</label>
          <label><input type="checkbox" id="traj-trail" checked>軌跡</label>
          <label><input type="checkbox" id="traj-shots" checked>誘導弾</label>
          <label><input type="checkbox" id="traj-aim" checked>射撃指示</label>
        </div>
        <div class="traj-legend" id="traj-legend"></div>
      </div>
      <div class="traj-side">
        <div id="traj-info"></div>
        <h2>イベント（クリックでジャンプ）</h2>
        <div class="traj-events" id="traj-events"></div>
      </div>
    </div>
    <p class="traj-note">陣営座標系（km）。x=+ は敵陣方向、y=+ は反時計回り側。プロットは自機編隊の中心に追従。
      敵の点は <code>own + dist·(cos bearing, sin bearing)</code> で復元した推定位置で、
      <b>そのフレームで当該機が探知していた敵だけ</b>を表示します（ undetected の敵は出ません）。
      ▲ は自機の位置と進行方位、リングはレーダ 80 km / IRST 120 km / MWS 10 km、
      赤線は被弾警報の方位です。高度はユース部門で固定のため平面表示です。<br>
      <b>誘導弾</b>は残弾数の減少から発射を検出し、破線が発射点→照準点、実線＋●が推定位置です
      （弾の座標はログに無いため <span id="traj-missile-note">速度 1.5 km/s で直線補間、最大 60 s</span>の推定表示）。
      弾の後ろに**軌跡**（直線補間の過去位置）を引き、ラベルは「1号→E4 3s/31s」のように「誰が誰に撃った弾か」を表示します
      （E4 は発射時の融合敵。敵は移動するため、着弾時には照準点から離れて「届かない」ように見える弾があります。これは命中/空振りがログから確定できないための表示です）。
      発射直後はリング＋「発射!」で強調し、機体の下に「残弾 n」を表示します（0 は弾切れ・発射不能を赤く表示）。<br>
      <b>ロック中（射撃指示）</b>は <code>action.target</code> が非 0 の間の狙い線で、
      矢印が照準先（=そのフレームの観測行の敵位置）、線の途中に「ロック n km」の距離、
      照準先に ○（護衛対象機なら金色二重丸）を表示します。弾が飛んでいる間もロックが続いている様子が見えます。
      破線の四角は戦域境界 150 km（越境で PENALTY）です。
       <b>探知イベント</b>は敵の個体IDがログに無いため位置の近傍一致で疑似追跡し、
       「探知/再探知」「8フレーム以上連続で観測が切れたら目標ロスト」を検出します。「命中/空振り」は弾着時の敵位置から**推定**です。
        「発射」「命中/空振り」「被弾警報」「初発見」はキャンバス上に一時的に文字表示され、時間経過で消えます。
       敵点の色は距離による<b>探知センサの推定</b>（レーダ ≤80 km / IRST ≤120 km / 護衛対象機の RCS 拡大 ≤150 km / それ以上は遠距離）です。</p>`;

  document.getElementById("traj-sel").addEventListener("change", e => openTraj(e.target.value));
  document.getElementById("traj-reload").addEventListener("click", () => loadTrajEntries(true));
  document.getElementById("traj-play").addEventListener("click", toggleTraj);
  document.getElementById("traj-seek").addEventListener("input", e => {
    traj.t = Number(e.target.value); drawTraj();
  });
  document.getElementById("traj-speed").addEventListener("change", e => { traj.speed = Number(e.target.value); });
  document.getElementById("traj-span").addEventListener("change", e => { traj.span = Number(e.target.value); drawTraj(); });
  document.getElementById("traj-rings").addEventListener("change", e => { traj.rings = e.target.checked; drawTraj(); });
  document.getElementById("traj-trail").addEventListener("change", e => { traj.trail = e.target.checked; drawTraj(); });
  document.getElementById("traj-shots").addEventListener("change", e => { traj.shots = e.target.checked; drawTraj(); });
  document.getElementById("traj-aim").addEventListener("change", e => { traj.aim = e.target.checked; drawTraj(); });
}

async function openTraj(log) {
  const btn = document.getElementById("traj-play");
  if (btn) { traj.playing = false; clearInterval(traj.timer); traj.timer = null; btn.textContent = "▶ 再生"; }
  const info = document.getElementById("traj-info");
  if (info) info.innerHTML = '<div class="empty">読み込み中…</div>';
  let payload;
  try {
    const res = await fetch("/api/replay?log=" + encodeURIComponent(log), { cache: "no-store" });
    payload = await res.json();
  } catch (err) {
    if (info) info.innerHTML = '<div class="empty">読み込み失敗: ' + esc(err) + '</div>';
    return;
  }
  if (payload.error) {
    if (info) info.innerHTML = '<div class="empty">' + esc(payload.error) + '</div>';
    return;
  }
  traj.data = payload;
  traj.log = log;
  traj.t = 0;
  const mnote = document.getElementById("traj-missile-note");
  if (mnote) {
    const mm = payload.missile_model || {};
    mnote.textContent = `速度 ${mm.speed_kms ?? 1.5} km/s で直線補間、発射から最長 ${mm.max_sec ?? 60} s`;
  }
  const seek = document.getElementById("traj-seek");
  seek.max = Math.max(0, payload.frame_count - 1);
  seek.value = 0;
  renderTrajLegend();
  renderTrajEvents();
  drawTraj();
}

function toggleTraj() {
  const btn = document.getElementById("traj-play");
  traj.playing = !traj.playing;
  btn.textContent = traj.playing ? "❚❚ 一時停止" : "▶ 再生";
  clearInterval(traj.timer);
  traj.timer = null;
  if (!traj.playing) return;
  traj.timer = setInterval(() => {
    if (!traj.data) return;
    const last = traj.data.frame_count - 1;
    if (traj.speed < 1) {
      traj.sub = (traj.sub || 0) + traj.speed;
      if (traj.sub < 1) return;
      traj.sub -= 1;
    }
    const inc = Math.round(traj.speed >= 1 ? traj.speed : 1);
    traj.t = traj.t >= last ? 0 : Math.min(last, traj.t + inc);
    document.getElementById("traj-seek").value = traj.t;
    drawTraj();
  }, 50);
}

/* 戦場俯瞰タブ: 両陣営（自軍4機＋敵軍）を固定マップに描くシミュレーション表示。
   own はログの実測座標。enemy はログに敵の絶対座標記録（enemies_direct）があればそれを
   そのまま使い（source:"direct"）、無いログでは全機の探知点をクラスタ融合した推定位置（frame.teams）。
*/

function renderTrajLegend() {
  const d = traj.data;
  const items = d.slots.map(s =>
    `<span><span class="sw" style="background:${trajColor(s)}"></span>${esc(s)}号</span>`).join("");
  const rings = Object.keys(d.sensor_ranges || {}).map(k =>
    `<span><span class="sw" style="background:${TRAJ_RING_COLORS[k]}"></span>${esc(k)} ${d.sensor_ranges[k]} km</span>`).join("");
  document.getElementById("traj-legend").innerHTML =
    `<span><span class="sw" style="background:#f85149"></span>被弾警報</span>`
    + `<span><span class="sw" style="background:${TRAJ_SENSOR_COLORS.radar}"></span>レーダ ≤80 km</span>`
    + `<span><span class="sw" style="background:${TRAJ_SENSOR_COLORS.irst}"></span>IRST ≤120 km</span>`
    + `<span><span class="sw" style="background:${TRAJ_SENSOR_COLORS.rcs}"></span>護衛対象機（RCS拡大）</span>`
    + `<span><span class="sw" style="background:${TRAJ_SENSOR_COLORS.far}"></span>遠距離 &gt;120 km</span>`
    + `<span><span class="sw" style="background:#ff7b72"></span>誘導弾（発射点→標的・推定）</span>`
    + `<span><span class="sw" style="background:transparent;border:1px solid #8b949e"></span>ロック中（射撃指示）</span>`
    + `<span><span class="sw" style="background:transparent;border:1px dashed #d29922"></span>戦域境界 150 km</span>`
    + `<span><span class="sw" style="background:#3fb950"></span>命中（推定）/探知</span>`
    + `<span><span class="sw" style="background:#8b949e"></span>空振り（推定）</span>`
    + `<span><span class="sw" style="background:#f85149"></span>目標ロスト</span>`
    + items + rings;
}

function renderTrajEvents() {
  const box = document.getElementById("traj-events");
  const events = traj.data.events || [];
  if (!events.length) {
    box.innerHTML = '<div class="empty">イベントなし</div>';
    return;
  }
  box.innerHTML = events.map((e, i) =>
    `<div data-i="${i}" data-t="${e.t}">t=${String(e.t).padStart(4)} ${esc(e.kind)} ${esc(e.text)}</div>`).join("");
  box.querySelectorAll("div[data-t]").forEach(el => {
    el.addEventListener("click", () => {
      traj.t = Number(el.dataset.t);
      document.getElementById("traj-seek").value = traj.t;
      drawTraj();
    });
  });
}

function trajFoeCount(frame) {
  const seen = {};
  (frame.enemy || []).forEach(e => {
    const key = Math.round(e.x) + ":" + Math.round(e.y);
    seen[key] = true;
  });
  return Object.keys(seen).length;
}

function drawTraj() {
  const canvas = document.getElementById("traj-canvas");
  const d = traj.data;
  if (!canvas || !d || !d.frames.length) return;
  if (!canvas.clientWidth) return;
  const cssW = canvas.clientWidth;
  const cssH = Math.max(360, Math.round(cssW * 0.62));
  const dpr = window.devicePixelRatio || 1;
  if (canvas.width !== Math.round(cssW * dpr) || canvas.height !== Math.round(cssH * dpr)) {
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
    canvas.style.height = cssH + "px";
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "#0b0f14";
  ctx.fillRect(0, 0, cssW, cssH);

  const frame = d.frames[Math.min(traj.t, d.frames.length - 1)];
  pushFrameToasts(traj, frame);
  const ownAt = (slot, t) => {
    for (let i = t; i >= 0; i--) {
      const p = d.frames[i].own[slot];
      if (p && p.x !== null && p.y !== null) return p;
    }
    return null;
  };
  const own = Object.values(frame.own || {}).filter(p => p.x !== null && p.y !== null);
  let cx = 0, cy = 0;
  if (own.length) {
    cx = own.reduce((a, p) => a + p.x, 0) / own.length;
    cy = own.reduce((a, p) => a + p.y, 0) / own.length;
  }
  const scale = Math.min(cssW, cssH) / traj.span;
  const X = x => cssW / 2 + (x - cx) * scale;
  const Y = y => cssH / 2 - (y - cy) * scale;

  ctx.strokeStyle = "rgba(147,161,176,0.16)";
  ctx.lineWidth = 1;
  ctx.font = "10px Consolas, monospace";
  ctx.fillStyle = "rgba(147,161,176,0.55)";
  const step = traj.span > 200 ? 50 : 25;
  for (let g = -300; g <= 300; g += step) {
    const sx = X(g), sy = Y(g);
    ctx.beginPath(); ctx.moveTo(sx, 0); ctx.lineTo(sx, cssH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, sy); ctx.lineTo(cssW, sy); ctx.stroke();
    if (sx > 12 && sx < cssW - 30) ctx.fillText(String(g), sx + 3, cssH - 6);
    if (sy > 12 && sy < cssH - 6) ctx.fillText(String(g), 6, sy - 3);
  }
  ctx.fillStyle = "rgba(147,161,176,0.8)";
  ctx.fillText("x=+ 敵陣側 →", cssW - 96, 14);
  ctx.fillText("← x=- 自陣側", 8, cssH - 20);

  const bounds = d.bounds || { x: 150, y: 150 };
  {
    const bx0 = X(-bounds.x), bx1 = X(bounds.x);
    const by0 = Y(bounds.y), by1 = Y(-bounds.y);
    const left = Math.min(bx0, bx1), top = Math.min(by0, by1);
    ctx.save();
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = "rgba(210,153,34,0.6)";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(left, top, Math.abs(bx1 - bx0), Math.abs(by1 - by0));
    ctx.restore();
    if (left > -40 && left < cssW - 200 && top > 0 && top < cssH - 12) {
      ctx.fillStyle = "rgba(210,153,34,0.9)";
      ctx.fillText("戦域境界 150 km（越境=PENALTY）", left + 5, top + 13);
    }
  }

  if (traj.rings) {
    Object.entries(d.sensor_ranges || {}).forEach(([k, km]) => {
      ctx.strokeStyle = TRAJ_RING_COLORS[k] || "rgba(147,161,176,0.2)";
      own.forEach(p => {
        ctx.beginPath();
        ctx.arc(X(p.x), Y(p.y), km * scale, 0, Math.PI * 2);
        ctx.stroke();
      });
    });
  }

  if (traj.trail) {
    d.slots.forEach(slot => {
      ctx.strokeStyle = trajColor(slot) + "4d";
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      let started = false;
      for (let i = 0; i <= traj.t && i < d.frames.length; i++) {
        const p = d.frames[i].own[slot];
        if (!p || p.x === null || p.y === null) { started = false; continue; }
        const sx = X(p.x), sy = Y(p.y);
        if (!started) { ctx.moveTo(sx, sy); started = true; } else { ctx.lineTo(sx, sy); }
      }
      ctx.stroke();
    });
  }

  (frame.enemy || []).forEach(e => {
    const sx = X(e.x), sy = Y(e.y);
    ctx.fillStyle = TRAJ_SENSOR_COLORS[e.sensor] || "#e6edf3";
    ctx.beginPath(); ctx.arc(sx, sy, 3.2, 0, Math.PI * 2); ctx.fill();
    if (e.escort) {
      ctx.strokeStyle = "#ffd33d";
      ctx.lineWidth = 1.1;
      ctx.beginPath(); ctx.arc(sx, sy, 5.4, 0, Math.PI * 2); ctx.stroke();
    }
  });

  (frame.threat || []).forEach(th => {
    const src = frame.own[th.slot];
    if (!src || src.x === null) return;
    const rad = (th.bearing || 0) * Math.PI / 180;
    const len = (d.sensor_ranges.mws || 10) * scale;
    const ax = X(src.x), ay = Y(src.y);
    const bx = ax + Math.cos(rad) * len, by = ay - Math.sin(rad) * len;
    ctx.strokeStyle = "#f85149";
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
    ctx.fillStyle = "#f85149";
    ctx.beginPath(); ctx.arc(bx, by, 3, 0, Math.PI * 2); ctx.fill();
  });

  if (traj.aim) {
    drawAimLayer(ctx, frame, X, Y, slot => ownAt(slot, traj.t));
  }

  Object.entries(frame.own || {}).forEach(([slot, p]) => {
    if (p.x === null || p.y === null) return;
    const sx = X(p.x), sy = Y(p.y), col = trajColor(slot);
    ctx.save();
    ctx.translate(sx, sy);
    ctx.rotate(-(p.heading || 0) * Math.PI / 180);
    ctx.fillStyle = col;
    ctx.beginPath();
    ctx.moveTo(8, 0); ctx.lineTo(-5, 5); ctx.lineTo(-2, 0); ctx.lineTo(-5, -5);
    ctx.closePath(); ctx.fill();
    ctx.restore();
    ctx.fillStyle = col;
    ctx.font = "11px Consolas, monospace";
    ctx.fillText(slot + "号", sx + 9, sy - 6);
    if (p.ammo !== undefined && p.ammo !== null) {
      ctx.fillStyle = p.ammo > 0 ? "rgba(147,161,176,0.85)" : "rgba(248,81,73,0.75)";
      ctx.font = "9px Consolas, monospace";
      ctx.fillText(`残弾${num(p.ammo, 0)}`, sx + 9, sy + 10);
    }
  });

  if (traj.shots) {
    drawShotsLayer(ctx, d, frame, X, Y, scale);
  }

  (frame.events || []).forEach(ev => {
    const p = frame.own[ev.slot];
    if (!p || p.x === null) return;
    ctx.strokeStyle = TRAJ_EVENT_COLORS[ev.kind] || "#58a6ff";
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(X(p.x), Y(p.y), 16, 0, Math.PI * 2); ctx.stroke();
  });

  drawEventToasts(ctx, traj);

  document.getElementById("traj-seek").value = traj.t;
  document.getElementById("traj-time").textContent = `${traj.t + 1} / ${d.frame_count}  （ptime ${frame.ptime}s）`;
  const r = d.result || {};
  const alive = Object.keys(frame.own || {}).length;
  document.getElementById("traj-info").innerHTML = cards([
    { k: "ログ", v: (d.log || "").split("/").slice(-2).join("/") },
    { k: "自機応答", v: alive + " / " + d.slots.length, cls: alive < d.slots.length ? "warn" : "ok" },
    { k: "推定敵位置", v: trajFoeCount(frame) },
    { k: "このフレームのイベント", v: (frame.events || []).length },
    { k: "終了理由", v: r.endReason || "—" },
    { k: "自陣スコア", v: r.own ? num(r.scores ? r.scores[r.own] : null, 3) : "—" },
    { k: "命中率", v: r.hit_rate === null || r.hit_rate === undefined ? "—" : num(r.hit_rate, 3) },
    { k: "生存（自/敵）", v: r.numAlives ? `${r.numAlives.Red ?? "—"} / ${r.numAlives.Blue ?? "—"}` : "—" },
  ]);
  const slotRows = d.slots.map(s => {
    const p = (frame.own || {})[s] || {};
    const aims = (frame.aim || []).filter(a => a.slot === s);
    let nearest = null;
    (frame.enemy || []).forEach(e => {
      if (e.slot !== s) return;
      if (nearest === null || e.dist < nearest) nearest = e.dist;
    });
    const flying = (frame.shots || []).filter(sh => sh.slot === s).length;
    return [
      `<span style="color:${trajColor(s)}">${esc(s)}号</span>`,
      p.ammo === null || p.ammo === undefined ? "—" : num(p.ammo, 0),
      aims.length ? `行${aims[0].row} ${num(aims[0].dist, 1)} km` : "—",
      nearest === null ? "—" : num(nearest, 1),
      flying ? `${flying} 発` : "—",
    ];
  });
  document.getElementById("traj-info").innerHTML += "<h2>機体状況</h2>" + table([
    { label: "機体" },
    { label: "残弾", num: true },
    { label: "射撃指示" },
    { label: "最近敵 km", num: true },
    { label: "飛翔中の弾" },
  ], slotRows);

  const box = document.getElementById("traj-events");
  if (box) {
    box.querySelectorAll("div[data-t]").forEach(el => {
      el.classList.toggle("cur", Number(el.dataset.t) === traj.t);
    });
  }
}

function renderHistoryChart(history) {
  const svg = document.getElementById("hist-chart");
  const legend = document.getElementById("hist-legend");
  if (!svg || !history.length) return;
  const metricBtns = document.querySelectorAll("[data-hist-metric]");
  let metric = "avg_score";
  metricBtns.forEach(b => { if (b.classList.contains("active")) metric = b.dataset.histMetric; });
  metricBtns.forEach(b => {
    b.onclick = () => {
      metricBtns.forEach(x => x.classList.toggle("active", x === b));
      renderHistoryChart(history);
    };
  });

  // one point per history entry, in time order (single series)
  const ACCENT = "#58a6ff";
  const valueOf = (hf) => {
    const m = hf.metrics || {};
    if (metric === "avg_score") return (m.avg_score === null || m.avg_score === undefined) ? null : Number(m.avg_score);
    if (metric === "win_rate") { const g = Number(m.games||0); const w = Number(m.win||0); return g > 0 ? (w/g)*100 : null; }
    if (metric === "avg_our_alive") return (m.avg_our_alive === null || m.avg_our_alive === undefined) ? null : Number(m.avg_our_alive);
    if (metric === "avg_enemy_alive") return (m.avg_enemy_alive === null || m.avg_enemy_alive === undefined) ? null : Number(m.avg_enemy_alive);
    return null;
  };
  const sel = document.getElementById("hist-series");
  const chosen = sel ? sel.value : "__all__";
  const entries = [...history]
    .sort((a,b) => (a.mtime||"").localeCompare(b.mtime||""))
    .filter(hf => chosen === "__all__" || ((hf.metrics || {}).label || hf.name) === chosen);
  const points = entries.map((hf, i) => {
    const m = hf.metrics || {};
    const label = m.label || hf.name || "default";
    return { i, label, v: valueOf(hf), mtime: hf.mtime, name: hf.name, games: m.games, wdl: `${m.win||0}/${m.draw||0}/${m.loss||0}` };
  });
  const valid = points.filter(p => p.v !== null);
  if (sel) sel.onchange = () => renderHistoryChart(history);

  const W = 960, H = 240, M = { l: 40, r: 20, t: 20, b: 40 };
  const w = W - M.l - M.r, h = H - M.t - M.b;
  const vals = valid.map(p => p.v);
  let vmin = vals.length ? Math.min(...vals) : 0;
  let vmax = vals.length ? Math.max(...vals) : 1;
  if (vmax === vmin) { vmax = vmin + 0.01; }
  const pad = (vmax - vmin) * 0.1 || 0.05;
  vmin -= pad; vmax += pad;
  const x = (i) => M.l + (points.length <= 1 ? w/2 : i * (w / (points.length - 1)));
  const y = (v) => M.t + h - ((v - vmin) / (vmax - vmin)) * h;

  let svgStr = `
<defs>
  <style>.axis{stroke:var(--muted);stroke-width:1;opacity:.5}.tick{font-size:10px;fill:var(--muted);font-family:Consolas,monospace}.line{fill:none;stroke-width:2;vector-effect:non-scaling-stroke}.pt{stroke-width:1.5;fill:var(--bg)}</style>
</defs>
<line x1="${M.l}" y1="${M.t}" x2="${M.l}" y2="${M.t+h}" class="axis"/>
<line x1="${M.l}" y1="${M.t+h}" x2="${M.l+w}" y2="${M.t+h}" class="axis"/>`;

  // ticks y
  const yticks = 4;
  for (let i = 0; i <= yticks; i++) {
    const tv = vmin + (vmax - vmin) * (i / yticks);
    const yy = y(tv);
    svgStr += `<line x1="${M.l-3}" y1="${yy}" x2="${M.l}" y2="${yy}" class="axis"/>`;
    const fmt = (metric === "win_rate") ? Math.round(tv*10)/10 : (tv >= 10 ? Math.round(tv) : Math.round(tv*100)/100);
    svgStr += `<text x="${M.l-6}" y="${yy+3}" text-anchor="end" class="tick">${fmt}</text>`;
  }
  // ticks x (max 6)
  const xt = Math.min(points.length, 6);
  for (let i = 0; i < xt; i++) {
    const idx = Math.floor(i * (points.length - 1) / Math.max(1, xt-1));
    const xx = x(idx);
    const hf = points[idx];
    svgStr += `<line x1="${xx}" y1="${M.t+h}" x2="${xx}" y2="${M.t+h+3}" class="axis"/>`;
    const mtimeStr = hf.mtime || "";
    const t = mtimeStr.includes("T") ? mtimeStr.slice(5,16).replace("T"," ") : mtimeStr.slice(5,16);
    svgStr += `<text x="${xx}" y="${M.t+h+14}" text-anchor="middle" class="tick">${t}</text>`;
  }

  // single trend line through all points in time order
  let trend = "";
  points.forEach(p => {
    if (p.v === null) return;
    const cmd = trend === "" ? "M" : "L";
    trend += cmd + x(p.i) + "," + y(p.v) + " ";
  });
  svgStr += `<path d="${trend.trim()}" class="line" stroke="${ACCENT}"/>`;

  // points (single color)
  points.forEach(p => {
    if (p.v === null) return;
    svgStr += `<circle cx="${x(p.i)}" cy="${y(p.v)}" r="3" class="pt" stroke="${ACCENT}" fill="${ACCENT}"><title>${esc(p.label)} [${esc(p.name)}] ${p.mtime}: ${p.v.toFixed(3)} (${p.wdl}, ${p.games||0}戦)</title></circle>`;
  });

  svg.innerHTML = svgStr;
  if (legend) {
    const labelText = chosen === "__all__" ? "すべて（時系列順）" : chosen;
    const note = valid.length < 2 ? " ※同一系列の履歴が1件のみ（点1つ）" : "";
    legend.innerHTML = `<span class="muted">系列: ${esc(labelText)} / ${valid.length}件${note}</span>`;
  }
}
