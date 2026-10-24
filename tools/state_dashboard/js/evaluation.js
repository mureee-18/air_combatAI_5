function renderEval(d) {
  const p = d.paired;
  if (!p.files.length) {
    document.getElementById("eval").innerHTML =
      '<div class="empty">workspace/paired/*.json がありません。<br>docker exec atla5-cpu bash -lc "cd /workspace && python /repo/local_test/run_eval_paired.py --seeds 1,2,3 --colors both --label baseline --out /workspace/paired/baseline.json"</div>';
    return;
  }
  const bestScore = Math.max(1, ...p.files.map(f => (f.metrics || {}).avg_score || 0));
  const pickLabel = lbl => p.files.find(f => (f.metrics || {}).label === lbl) || null;
  const focusNames = [];
  [(pickLabel("default") || {}).name, p.best, (pickLabel("baseline") || {}).name]
    .forEach(n => { if (n && !focusNames.includes(n)) focusNames.push(n); });
  const focus = focusNames.map(n => p.files.find(f => f.name === n)).filter(Boolean);
  const roleTags = f => {
    const m = f.metrics || {};
    const t = [];
    if (f.name === p.best) t.push("★最良");
    if (m.label === "default") t.push("現行");
    if (m.label === "baseline") t.push("基準");
    return t.join(" / ");
  };
  const scoreCell = f => {
    const m = f.metrics || {};
    const w = Math.round(((m.avg_score || 0) / bestScore) * 140);
    return `<span style="display:inline-flex;align-items:center;gap:6px">` +
      `<span class="bar ${f.name === p.best ? "" : "alt"}" style="width:${w}px;height:12px"></span>` +
      `<span>${num(m.avg_score, 3)}</span></span>`;
  };
  const evalHeaders = [
    {label:"label / 役割", num:false}, {label:"ファイル", num:false}, {label:"対戦数", num:true},
    {label:"win/draw/loss", num:false}, {label:"avg_score", num:false},
    {label:"avg_our_alive", num:true}, {label:"avg_enemy_alive", num:true}, {label:"更新", num:false},
  ];
  const evalRow = f => {
    const m = f.metrics || {};
    const role = roleTags(f);
    return [
      esc((m.label || f.name) + (role ? ` (${role})` : "")), esc(f.name),
      m.games ?? "—", `${m.win ?? "—"}/${m.draw ?? "—"}/${m.loss ?? "—"}`,
      scoreCell(f), num(m.avg_our_alive, 2), num(m.avg_enemy_alive, 2), esc(f.mtime),
    ];
  };
  const gm = (d.custom_metrics && d.custom_metrics.rows) || [];
  const goalTotal = gm.filter(m => m.target !== null && m.target !== undefined).length;
  const goalDone = gm.filter(m => m.status === "reached").length;
  let h = cards([
    { k: "評価ファイル", v: p.files.length },
    { k: "最良", v: p.best || "—" },
    { k: "目標", v: goalTotal ? `${goalDone}/${goalTotal} 達成` : "—",
      cls: goalTotal && goalDone === goalTotal ? "ok" : "" },
  ]);
  h += "<h2>注目（現行 default／★最良／基準 baseline）</h2>";
  h += table(evalHeaders, focus.map(evalRow));

  if (p.history && p.history.length) {
    h += "<h2>強化推移（時系列・古い順）</h2>";
    h += '<div class="section" style="margin-top:8px">';
    h += '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:8px">';
    h += '<span class="muted">指標：</span>';
    h += '<button class="btn small active" data-hist-metric="avg_score">avg_score</button>';
    h += '<button class="btn small" data-hist-metric="win_rate">勝率(%)</button>';
    h += '<button class="btn small" data-hist-metric="avg_our_alive">avg_our_alive</button>';
    h += '<button class="btn small" data-hist-metric="avg_enemy_alive">avg_enemy_alive</button>';
    const histLabels = [...new Set(p.history.map(hf => (hf.metrics || {}).label || hf.name))];
    h += '<span class="muted" style="margin-left:8px">系列：</span>';
    h += '<select id="hist-series" class="btn small">';
    h += '<option value="__all__">すべて（時系列順）</option>';
    h += histLabels.map(l => `<option value="${attr(l)}">${esc(l)}</option>`).join("");
    h += '</select>';
    h += '</div>';
    h += '<div style="overflow-x:auto;border:1px solid var(--border);border-radius:6px;padding:8px;background:var(--bg-soft)">';
    h += '<svg id="hist-chart" width="960" height="240" viewBox="0 0 960 240" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;max-height:320px"></svg>';
    h += '</div>';
    h += '<div id="hist-legend" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px"></div>';
    h += '</div>';
    // 時系列の全件表は「過去の実験」に集約（重複表示を避ける）
    // defer chart render
    setTimeout(() => renderHistoryChart(p.history), 0);
  }

  const rest = p.files.filter(f => !focusNames.includes(f.name));
  h += `<details style="margin-top:10px">` +
    `<summary style="cursor:pointer;color:var(--muted);font-size:13px">過去の実験 ${rest.length} 件（クリックで展開）</summary>`;
  h += table(evalHeaders, rest.map(evalRow));
  h += "</details>";

  h += "<h2>目標（独自指標）</h2>";
  h += renderGoals(d);
  document.getElementById("eval").innerHTML = h;
  bindCopy(document.getElementById("eval"));
}

function goalPct(m) {
  const v = m.value, t = m.target;
  if (v === null || v === undefined || t === null || t === undefined || t === 0) return null;
  if (m.direction === "lower") {
    if (v <= t) return 100;
    return Math.max(0, Math.min(100, Math.round((t / v) * 100)));
  }
  return Math.max(0, Math.min(100, Math.round((v / t) * 100)));
}

function goalStatus(m) {
  if (m.status === "reached") return '<span class="ok">達成</span>';
  if (m.status === "open") return '<span class="warn">未達</span>';
  if (m.target === null || m.target === undefined) return '<span class="muted">参考</span>';
  return '<span class="muted">値なし</span>';
}

// 目標ボード: custom_metrics.json の定義と値・目標・進捗を評価タブに出す（読み取り専用）

function renderGoals(d) {
  const cm = d.custom_metrics || {};
  const rows = cm.rows || [];
  if (!rows.length) {
    return '<div class="empty">独自指標が未定義です。</div>' +
      cmdRow(cm.add_command || "python tools/state_dashboard/add_metric.py --list", "定義を追加する");
  }
  const fmt = (v, digits) =>
    v === null || v === undefined ? "—" : num(v, digits === undefined ? 2 : digits);
  let h = table(
    [{label:"状態"}, {label:"指標"}, {label:"現在値", num:true},
     {label:"目標", num:true}, {label:"進捗"}, {label:"出所"}],
    rows.map(m => {
      const pct = goalPct(m);
      const bar = pct === null
        ? '<span class="muted">—</span>'
        : `<span style="display:inline-flex;align-items:center;gap:6px">` +
          `<span class="bar ${pct >= 100 ? "" : "alt"}" style="width:${Math.round(pct * 1.2)}px;height:10px"></span>` +
          `<span class="muted">${pct}%</span></span>`;
      const target = m.target === null || m.target === undefined
        ? "—"
        : `${fmt(m.target, m.digits)}${m.direction === "lower" ? " 以下" : " 以上"}`;
      const labelCell =
        `<b>${esc(m.label)}</b><br><span class="muted" style="font-size:11px">${esc(m.id)}</span>` +
        (m.note ? `<br><span class="muted" style="font-size:11px">${esc(m.note)}</span>` : "");
      return [
        goalStatus(m), labelCell,
        `${fmt(m.value, m.digits)}${m.unit ? ` <span class="muted">${esc(m.unit)}</span>` : ""}`,
        target, bar, `<span class="pill" title="${attr(m.where || "")}">${esc(m.tab || "—")}</span>`,
      ];
    })
  );
  h += `<p class="meta">${esc(cm.note || "定義は tools/state_dashboard/custom_metrics.json。")}</p>`;
  h += "<h2>目標の編集</h2>";
  h += cmdRow(cm.add_command || "python tools/state_dashboard/add_metric.py --label \"<指標名>\" --from paired --direction higher --target <目標値>", "指標を追加する");
  h += cmdRow(cm.list_command || "python tools/state_dashboard/add_metric.py --list", "定義一覧を表示");
  h += '<details style="margin-top:4px"><summary style="cursor:pointer;color:var(--muted);font-size:13px">指標ごとの目標を変更</summary>';
  rows.forEach(m => {
    h += cmdRow(
      `python tools/state_dashboard/add_metric.py --id ${m.id} --target <新しい目標値>`,
      `「${m.label}」の目標を更新`);
  });
  h += "</details>";
  return h;
}
