const battle = { data: null, log: null, t: 0, playing: false, timer: null, sub: 0, speed: 1,
                 trail: true, shots: true, threat: true, toasts: [] };

function buildBattleShell() {
  const opts = traj.entries.map(e =>
    `<option value="${esc(e.log)}">${esc(e.log + "  " + e.mtime + "  " + e.frames + "ステップ"
      + (e.has_ammo ? "" : "（残弾列なし）"))}</option>`).join("");
  document.getElementById("battle").innerHTML = `
    <div class="traj-controls">
      <select id="battle-sel">${opts}</select>
      <button id="battle-reload">再読み込み</button>
      <span class="meta">再生可能なログ ${traj.entries.length} 本</span>
    </div>
    <div class="traj-wrap">
      <div class="traj-stage">
        <canvas id="battle-canvas"></canvas>
        <div class="traj-controls">
          <button id="battle-play">▶ 再生</button>
          <input type="range" id="battle-seek" min="0" max="0" value="0">
          <span class="meta" id="battle-time">0 / 0</span>
          <select id="battle-speed">
            <option value="0.5">0.5×（スロー）</option><option value="1" selected>1×</option>
            <option value="2">2×</option><option value="4">4×</option><option value="8">8×</option>
          </select>
          <label><input type="checkbox" id="battle-trail" checked>軌跡</label>
          <label><input type="checkbox" id="battle-shots" checked>誘導弾</label>
          <label><input type="checkbox" id="battle-threat" checked>警報</label>
        </div>
        <div class="traj-legend" id="battle-legend"></div>
      </div>
      <div class="traj-side">
        <div id="battle-info"></div>
        <h2>イベント（クリックでジャンプ）</h2>
        <div class="traj-events" id="battle-events"></div>
      </div>
    </div>
    <p class="traj-note">両陣営を固定マップ（全域 ±150 km）に描いたシミュレーションイメージ。
      青 ▲ = 自軍 4 機（座標はログの<b>実測</b>）、赤 ◆ = 敵軍（全機の探知点を融合して復元した
      <b>推定位置・推定方位</b>）。敵の個体IDはログに無いため、近くの点を束ねて
      「見失って 8 フレーム以上、または 25 km 離れたら別の敵」という規則で軌跡を繋いでいます。
      弾は自軍が撃った誘導弾（発射点→標点の直線補間）のみで、敵弾はログに入っていません。
      照準中の狙い線（矢印＋「ロック n km」）と機体下の「残弾 n」（0 は赤・発射不能）も表示します。
      見失っている間の敵の動き（点線）は描かれません。</p>`;

  document.getElementById("battle-sel").addEventListener("change", e => openBattle(e.target.value));
  document.getElementById("battle-reload").addEventListener("click", () => loadTrajEntries(true));
  document.getElementById("battle-play").addEventListener("click", toggleBattle);
  document.getElementById("battle-seek").addEventListener("input", e => {
    battle.t = Number(e.target.value); drawBattle();
  });
  document.getElementById("battle-speed").addEventListener("change", e => {
    battle.speed = Number(e.target.value);
  });
  document.getElementById("battle-trail").addEventListener("change", e => { battle.trail = e.target.checked; drawBattle(); });
  document.getElementById("battle-shots").addEventListener("change", e => { battle.shots = e.target.checked; drawBattle(); });
  document.getElementById("battle-threat").addEventListener("change", e => { battle.threat = e.target.checked; drawBattle(); });
}

async function openBattle(log) {
  const btn = document.getElementById("battle-play");
  if (btn) { battle.playing = false; clearInterval(battle.timer); battle.timer = null; btn.textContent = "▶ 再生"; }
  const info = document.getElementById("battle-info");
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
  battle.data = payload;
  battle.log = log;
  battle.t = 0;
  const seek = document.getElementById("battle-seek");
  if (seek) { seek.max = Math.max(0, payload.frame_count - 1); seek.value = 0; }
  renderBattleLegend();
  drawBattle();
}

function toggleBattle() {
  const btn = document.getElementById("battle-play");
  battle.playing = !battle.playing;
  btn.textContent = battle.playing ? "❚❚ 一時停止" : "▶ 再生";
  clearInterval(battle.timer);
  battle.timer = null;
  if (!battle.playing) return;
  battle.timer = setInterval(() => {
    if (!battle.data) return;
    const last = battle.data.frame_count - 1;
    if (battle.speed < 1) {
      battle.sub = (battle.sub || 0) + battle.speed;
      if (battle.sub < 1) return;
      battle.sub -= 1;
    }
    const inc = Math.round(battle.speed >= 1 ? battle.speed : 1);
    battle.t = battle.t >= last ? 0 : Math.min(last, battle.t + inc);
    document.getElementById("battle-seek").value = battle.t;
    drawBattle();
  }, 50);
}

function renderBattleLegend() {
  document.getElementById("battle-legend").innerHTML =
    `<span><span class="sw" style="background:#58a6ff"></span>自軍（4機・座標実測）</span>`
    + `<span><span class="sw" style="background:#f85149"></span>敵軍（探知融合・推定）</span>`
    + `<span><span class="sw" style="background:#ff7b72"></span>自軍の誘導弾（推定）</span>`
    + `<span><span class="sw" style="background:transparent;border:1px solid #8b949e"></span>ロック中（射撃指示）</span>`
    + `<span><span class="sw" style="background:#f85149"></span>被弾警報</span>`
    + `<span><span class="sw" style="background:#3fb950"></span>命中（推定）</span>`
    + `<span><span class="sw" style="background:#8b949e"></span>空振り（推定）</span>`
    + `<span><span class="sw" style="background:transparent;border:1px dashed #d29922"></span>戦域境界 150 km</span>`;
}

function renderBattleEvents() {
  const box = document.getElementById("battle-events");
  const events = battle.data ? (battle.data.events || []) : [];
  if (!events.length) {
    box.innerHTML = '<div class="empty">イベントなし</div>';
    return;
  }
  box.innerHTML = events.map((e, i) =>
    `<div data-i="${i}" data-t="${e.t}">t=${String(e.t).padStart(4)} ${esc(e.kind)} ${esc(e.text)}</div>`).join("");
  box.querySelectorAll("div[data-t]").forEach(el => {
    el.addEventListener("click", () => {
      battle.t = Number(el.dataset.t);
      document.getElementById("battle-seek").value = battle.t;
      drawBattle();
    });
  });
}

/* 射撃レイヤー（自機視点 / 戦場俯瞰 共通）。
   aim は action.target が非0の間の「ロック中」表示: 照準線＋矢印＋距離、
   先端にブラケット。escort（護衛対象機）は金色リングを重ねる。
   srcAt = (slot) => その機のこのフレームの座標（なければ null）。
*/

function drawAimLayer(ctx, frame, X, Y, srcAt) {
  (frame.aim || []).forEach(a => {
    const src = srcAt(a.slot);
    const sx = (src && src.x !== null && src.x !== undefined) ? X(src.x) : null;
    const sy = (src && src.y !== null && src.y !== undefined) ? Y(src.y) : null;
    const tx = X(a.x), ty = Y(a.y);
    const col = trajColor(a.slot);
    if (sx !== null && sy !== null) {
      const dx = tx - sx, dy = ty - sy;
      const l = Math.hypot(dx, dy);
      if (l > 0.1) {
        const ux = dx / l, uy = dy / l;
        // ロック線は各機のスロット色の破線（実線の編隊軌跡と破線なら区別でき、同色同士で埋もれない）
        ctx.save();
        ctx.setLineDash([5, 3]);
        ctx.strokeStyle = col + "cc";
        ctx.lineWidth = 1.8;
        ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(tx, ty); ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.moveTo(tx, ty);
        ctx.lineTo(tx - ux * 8 + uy * 4, ty - uy * 8 - ux * 4);
        ctx.lineTo(tx - ux * 8 - uy * 4, ty - uy * 8 + ux * 4);
        ctx.closePath(); ctx.fill();
        ctx.fillStyle = col;
        ctx.font = "10px Consolas, monospace";
        ctx.fillText(`ロック ${num(a.dist, 0)} km`, (sx + tx) / 2 - uy * 15 + 2, (sy + ty) / 2 + ux * 15);
      }
    }
    ctx.strokeStyle = col;
    ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.arc(tx, ty, 5, 0, Math.PI * 2); ctx.stroke();
    if (a.escort) {
      ctx.strokeStyle = "#ffd33d";
      ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.arc(tx, ty, 8, 0, Math.PI * 2); ctx.stroke();
    }
  });
}

/* 飛翔中の誘導弾レイヤー（自機視点 / 戦場俯瞰 共通）。
   弾の座標はログに無いので発射点→照準点を直線補間して復元。
   - 弾の後ろに**過去の位置（軌跡）**を薄く描いて進行方向を見せる
   - 発射時点で照準点に最も近い融合敵を「撃った相手」とし、ラベルに `→ E4` と表示
     （敵は移動するので、弾が届く頃には照準点から離れていて「空振り」に見えることがある、という意味も込めている）
*/

const shotTargetCache = {};

function drawShotsLayer(ctx, d, frame, X, Y, scale) {
  (frame.shots || []).forEach(s => {
    const col = trajColor(s.slot);
    const sfx = s.fx, sfy = s.fy;
    const stx = s.tx, sty = s.ty;
    if (stx !== null && stx !== undefined && sty !== null && sty !== undefined) {
      ctx.save();
      ctx.setLineDash([3, 5]);
      ctx.strokeStyle = col + "40";
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(X(sfx), Y(sfy)); ctx.lineTo(X(stx), Y(sty)); ctx.stroke();
      ctx.restore();
      // 軌跡（直線補間の過去位置を段階的に再現）
      const steps = Math.min(14, Math.floor(s.age) + 1);
      for (let k = steps; k >= 1; k--) {
        const a1 = Math.max(0, s.age - k), a2 = Math.max(0, s.age - k + 1);
        const p1 = s.flight > 0 ? a1 / s.flight : 0;
        const p2 = s.flight > 0 ? a2 / s.flight : 0;
        ctx.strokeStyle = col + (Math.round(102 * (1 - (k - 1) / steps)).toString(16).padStart(2, "0"));
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        ctx.moveTo(X(sfx + (stx - sfx) * p1), Y(sfy + (sty - sfy) * p1));
        ctx.lineTo(X(sfx + (stx - sfx) * p2), Y(sfy + (sty - sfy) * p2));
        ctx.stroke();
      }
      ctx.strokeStyle = col + "e6";
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(X(sfx), Y(sfy)); ctx.lineTo(X(s.x), Y(s.y)); ctx.stroke();
      // 弾の実線（発射点→現在）: 目標ロストリングと同じ太さ（1.5px）に細い白縁取り
      ctx.lineCap = "round";
      ctx.strokeStyle = "rgba(255,255,255,0.35)";
      ctx.lineWidth = 3.5;
      ctx.beginPath(); ctx.moveTo(X(sfx), Y(sfy)); ctx.lineTo(X(s.x), Y(s.y)); ctx.stroke();
      ctx.strokeStyle = col;
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(X(sfx), Y(sfy)); ctx.lineTo(X(s.x), Y(s.y)); ctx.stroke();
      ctx.lineCap = "butt";
      // 照準点: 白リング＋スロット色
      ctx.strokeStyle = "rgba(255,255,255,0.9)";
      ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.arc(X(stx), Y(sty), 5.4, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(X(stx), Y(sty), 3, 0, Math.PI * 2); ctx.fill();
    }
    if (s.age <= 2) {
      ctx.strokeStyle = col + "cc";
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(X(sfx), Y(sfy), 9 + s.age * 3, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = col;
      ctx.font = "10px Consolas, monospace";
      ctx.fillText("発射!", X(sfx) + 13, Y(sfy) - 13);
    }
    const sx = X(s.x), sy = Y(s.y);
    ctx.strokeStyle = "rgba(255,255,255,0.9)";
    ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(sx, sy, 5.6, 0, Math.PI * 2); ctx.stroke();
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.arc(sx, sy, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "rgba(11,15,20,0.9)";
    ctx.font = "8px Consolas, monospace";
    ctx.fillText("弾", sx - 4, sy + 4);
    const key = s.slot + "@" + s.t0;
    if (!(key in shotTargetCache)) {
      let target = null;
      if (stx !== null && stx !== undefined) {
        const tf = d.frames[Math.min(s.t0, d.frames.length - 1)];
        let best = null, bestD = 5;
        (tf.teams || []).forEach(t => {
          if (t.side !== "enemy") return;
          const dd = Math.hypot(t.x - stx, t.y - sty);
          if (dd < bestD) { best = t.id; bestD = dd; }
        });
        target = best;
      }
      shotTargetCache[key] = target;
    }
    ctx.fillStyle = col;
    ctx.font = "10px Consolas, monospace";
    const tgt = shotTargetCache[key];
    ctx.fillText(`${s.slot}号${tgt ? "→" + tgt : ""} ${num(s.age, 0)}s/${num(s.flight, 0)}s`, sx + 7, sy - 6);
  });
}

function drawBattleIcon(ctx, x, y, heading, color, kind) {
  ctx.save();
  ctx.translate(x, y);
  if (heading !== null && heading !== undefined) ctx.rotate(-heading * Math.PI / 180);
  ctx.fillStyle = color;
  ctx.beginPath();
  if (kind === "own") {
    ctx.moveTo(9, 0); ctx.lineTo(-5, 5); ctx.lineTo(-2, 0); ctx.lineTo(-5, -5);
  } else {
    ctx.moveTo(7, 0); ctx.lineTo(0, 7); ctx.lineTo(-7, 0); ctx.lineTo(0, -7);
  }
  ctx.closePath(); ctx.fill();
  ctx.restore();
}

function drawBattle() {
  const canvas = document.getElementById("battle-canvas");
  const d = battle.data;
  const span = 150;
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

  const scale = Math.min(cssW, cssH) / span;
  const X = x => cssW / 2 + x * scale;
  const Y = y => cssH / 2 - y * scale;

  ctx.strokeStyle = "rgba(147,161,176,0.16)";
  ctx.lineWidth = 1;
  ctx.font = "10px Consolas, monospace";
  ctx.fillStyle = "rgba(147,161,176,0.55)";
  for (let g = -300; g <= 300; g += 50) {
    const sx = X(g), sy = Y(g);
    ctx.beginPath(); ctx.moveTo(sx, 0); ctx.lineTo(sx, cssH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, sy); ctx.lineTo(cssW, sy); ctx.stroke();
    if (sx > 12 && sx < cssW - 30) ctx.fillText(String(g), sx + 3, cssH - 6);
    if (sy > 12 && sy < cssH - 6) ctx.fillText(String(g), 6, sy - 3);
  }

  const bounds = d.bounds || { x: 150, y: 150 };
  {
    const bx0 = X(-bounds.x), bx1 = X(bounds.x);
    const by0 = Y(bounds.y), by1 = Y(-bounds.y);
    ctx.save();
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = "rgba(210,153,34,0.6)";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(Math.min(bx0, bx1), Math.min(by0, by1), Math.abs(bx1 - bx0), Math.abs(by1 - by0));
    ctx.restore();
  }

  const frame = d.frames[Math.min(battle.t, d.frames.length - 1)];
  pushFrameToasts(battle, frame);
  const drawTrail = (side, color, width) => {
    if (!battle.trail) return;
    const byId = {};
    for (let i = 0; i <= battle.t; i++) {
      (d.frames[i].teams || []).forEach(t => {
        if (t.side !== side || t.x === null || t.x === undefined) return;
        (byId[t.id] = byId[t.id] || []).push([t.x, t.y]);
      });
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    Object.values(byId).forEach(pts => {
      ctx.beginPath();
      let started = false;
      pts.forEach(p => {
        const sx = X(p[0]), sy = Y(p[1]);
        if (!started) { ctx.moveTo(sx, sy); started = true; } else { ctx.lineTo(sx, sy); }
      });
      ctx.stroke();
    });
  };
  drawTrail("own", "rgba(88,166,255,0.30)", 1.4);
  drawTrail("enemy", "rgba(248,81,73,0.32)", 1.4);

  drawAimLayer(ctx, frame, X, Y, slot => (frame.own || {})[slot] || null);

  if (battle.threat) {
    (frame.threat || []).forEach(th => {
      const src = (frame.own || {})[th.slot];
      if (!src || src.x === null) return;
      const rad = (th.bearing || 0) * Math.PI / 180;
      const len = (d.sensor_ranges.mws || 10) * scale;
      const ax = X(src.x), ay = Y(src.y);
      ctx.strokeStyle = "#f85149";
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(ax + Math.cos(rad) * len, ay - Math.sin(rad) * len); ctx.stroke();
    });
  }

  if (battle.shots) {
    drawShotsLayer(ctx, d, frame, X, Y, scale);
  }

  (frame.events || []).forEach(ev => {
    const p = (frame.own || {})[ev.slot];
    if (!p || p.x === null) return;
    ctx.strokeStyle = TRAJ_EVENT_COLORS[ev.kind] || "#58a6ff";
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(X(p.x), Y(p.y), 16, 0, Math.PI * 2); ctx.stroke();
  });

  drawEventToasts(ctx, battle);

  let nOwn = 0, nEnemy = 0;
  (frame.teams || []).forEach(t => {
    const sx = X(t.x), sy = Y(t.y);
    if (t.side === "own") {
      drawBattleIcon(ctx, sx, sy, t.heading, "#58a6ff", "own");
      nOwn += 1;
      ctx.fillStyle = "#58a6ff";
      ctx.font = "11px Consolas, monospace";
      ctx.fillText(t.id + "号", sx + 9, sy - 6);
      const am = (frame.own || {})[t.id];
      if (am && am.ammo !== undefined && am.ammo !== null) {
        ctx.fillStyle = am.ammo > 0 ? "rgba(147,161,176,0.85)" : "rgba(248,81,73,0.75)";
        ctx.font = "9px Consolas, monospace";
        ctx.fillText(`残弾${num(am.ammo, 0)}`, sx + 9, sy + 10);
      }
    } else {
      drawBattleIcon(ctx, sx, sy, t.heading, "#f85149", "enemy");
      nEnemy += 1;
      ctx.fillStyle = "rgba(248,81,73,0.9)";
      ctx.font = "11px Consolas, monospace";
      ctx.fillText(t.source === "direct" ? t.id : String(t.seen_by || 1) + "機検知 " + t.id, sx + 9, sy + 12);
    }
  });

  document.getElementById("battle-seek").value = battle.t;
  document.getElementById("battle-time").textContent = `${battle.t + 1} / ${d.frame_count}  （ptime ${frame.ptime}s）`;
  const r = d.result || {};
  document.getElementById("battle-info").innerHTML = cards([
    { k: "ログ", v: (d.log || "").split("/").slice(-2).join("/") },
    { k: "自軍生存", v: nOwn + " / " + d.slots.length, cls: nOwn < d.slots.length ? "warn" : "ok" },
    { k: "敵軍表示中", v: nEnemy + " 機", cls: nEnemy ? "ok" : "warn" },
    { k: "終了理由", v: r.endReason || "—" },
    { k: "自陣スコア", v: r.own ? num(r.scores ? r.scores[r.own] : null, 3) : "—" },
    { k: "命中率", v: r.hit_rate === null || r.hit_rate === undefined ? "—" : num(r.hit_rate, 3) },
    { k: "命中数", v: r.hit_count === null || r.hit_count === undefined ? "—" : num(r.hit_count, 0) },
    { k: "初弾命中", v: r.first_shot_hit === null || r.first_shot_hit === undefined ? "—" : (r.first_shot_hit ? "命中" : "不命中") },
    { k: "初発距離", v: r.first_shot_distance === null || r.first_shot_distance === undefined ? "—" : num(r.first_shot_distance, 1) + " km" },
    { k: "生存（自/敵）", v: r.numAlives ? `${r.numAlives.Red ?? "—"} / ${r.numAlives.Blue ?? "—"}` : "—" },
  ]);
  const rows = (frame.teams || []).map(t => [
    `<span style="color:${t.side === "own" ? "#58a6ff" : "#f85149"}">${esc(t.id)}${t.side === "own" ? "号" : ""}</span>`,
    t.side === "own" ? "自軍" : "敵軍",
    t.side === "own" ? "ログ実測" : (t.source === "direct" ? "ログ実測（絶対座標）" : (t.seen_by ? `${t.seen_by} 機の探知を融合` : "—")),
    t.x === null || t.x === undefined ? "—" : `${num(t.x, 0)}, ${num(t.y, 0)}`,
    t.heading === null || t.heading === undefined ? "—" : `${num(t.heading, 0)}°`,
  ]);
  document.getElementById("battle-info").innerHTML += "<h2>機体一覧</h2>" + table([
    { label: "機体" },
    { label: "陣営" },
    { label: "座標の出所" },
    { label: "座標 [km]" },
    { label: "方位" },
  ], rows);
  renderBattleEvents();
}
