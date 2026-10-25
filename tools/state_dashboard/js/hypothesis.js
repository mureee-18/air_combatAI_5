const STEP_STATE_LABEL = { done: "済", current: "次", todo: "未" };

// 登録系コピーは、貼った時点でAIが意図を判別できるよう先頭に種別行を付ける

function recordedPhrases() { try { const r = (typeof state !== "undefined" && state.data && state.data.session && state.data.session.recorded_materials) || []; return Array.isArray(r) ? r : []; } catch (e) { return []; } }

function isHandled(c) {
  const phrase = c.phrase || "";
  if (!phrase) return false;
  for (const r of recordedPhrases()) {
    if (r.phrase === phrase) return true;
  }
  return false;
}

function sortByHandled(list) { const un = [], hd = []; list.forEach(c => { (isHandled(c) ? hd : un).push(c); }); return un.concat(hd); }

function bindFactToggle(root) {
  root.querySelectorAll("button[data-fact-toggle]").forEach(btn => {
    btn.addEventListener("click", () => {
      const box = btn.closest(".fact-grid, .fact-list");
      if (!box) return;
      const open = box.classList.toggle("open");
      btn.textContent = open ? btn.dataset.less : btn.dataset.more;
    });
  });
}

function renderSteps(steps) {
  if (!steps || !steps.length) return '<div class="empty">対象 specialist が未設定です。</div>';
  let h = '<div class="steps">';
  steps.forEach((s, i) => {
    h += `<div class="step ${s.state}">` +
         `<span class="n">${STEP_STATE_LABEL[s.state] || "?"}</span>` +
         `<span class="t">${i + 1}. ${esc(s.label)}</span>` +
         `<div class="d">${esc(s.detail || "")}</div>` +
         `<div class="h">${esc(s.hint || "")}</div>`;
    h += "</div>";
  });
  return h + "</div>";
}

const PARKED_PATTERNS = ["新規仮説はない", "変数はない", "閉鎖", "棄却済み"];

function isParked(c) {
  const t = c.hypothesis || "";
  return PARKED_PATTERNS.some(p => t.indexOf(p) >= 0);
}

function renderFactGroups(list) {
  const un = [], pk = [], hd = [];
  list.forEach(c => {
    if (isHandled(c)) hd.push(c);
    else if (isParked(c)) pk.push(c);
    else un.push(c);
  });
  const anySub = pk.length + hd.length > 0;
  let h = "";
  if (un.length && (pk.length || hd.length)) h += `<div class="fact-group-title">未処理（${un.length}件）</div>`;
  h += un.map(c => renderFact(c, (pk.length || hd.length) ? "fresh" : "")).join("");
  if (pk.length) {
    h += `<div class="fact-group-title">見送り（対応不要・${pk.length}件）</div>`;
    h += pk.map(c => renderFact(c, "parked")).join("");
  }
  if (hd.length) {
    h += `<div class="fact-group-title">処理済み（${hd.length}件）</div>`;
    h += hd.map(c => renderFact(c, "handled")).join("");
  }
  return h;
}

function renderFact(card, extraCls) {
  const badgeKind = { observation: "観測", assumption: "前提", rule: "公式ルール" };
  const badgeSrc = { log: "ログ", code: "コード", official: "公式" };
  const handledTag = "";
  const deepened = !!card.deepened;
  const needDeepen = !!(card.phrase && !deepened && card.kind !== "assumption" && card.kind !== "rule");
  let h = `<div class="fact ${card.kind}">`;
  h += '<div class="fact-head">' +
       `<span class="title">${esc(card.title)}</span>` +
       `<span class="badge">${esc(badgeKind[card.kind] || card.kind)}</span>` +
       `<span class="badge${card.source === "official" ? " official" : ""}">` +
       `${esc(badgeSrc[card.source] || card.source)}</span>` +
       (needDeepen ? '<span class="badge deep-pending">深掘り未了</span>' : '') +
       (deepened ? '<span class="badge deep-done">深掘り済</span>' : '') +
       `${handledTag}</div>`;
  if (card.summary) h += `<div class="summary clamp2">${esc(card.summary)}</div>`;

  if (card.evidence && card.evidence.length) {
    const LIMIT = 8;
    const hasExtra = card.evidence.length > LIMIT;
    h += '<div class="fact-grid">';
    card.evidence.forEach((e, idx) => {
      const digits = e.digits !== undefined ? e.digits : (Number.isInteger(e.value) ? 0 : 2);
      const v = e.num ? num(e.value, digits) : esc(e.value);
      const diffClass = e._diff === "changed" ? "changed" : (e._diff === "new" ? "new" : "");
      const diffIcon = e._diff === "changed" ? '<span class="diff-icon">🔄</span>' : (e._diff === "new" ? '<span class="diff-icon new">NEW</span>' : "");
      const prevDisplay = e._diff === "changed" && e._prevValue !== undefined ? ` <span class="k" style="opacity:0.6">(前: ${esc(String(e._prevValue))})</span>` : "";
      const cls = hasExtra && idx >= LIMIT ? ' class="extra"' : "";
      h += `<div${cls}><div class="k">${esc(e.label)}</div><div class="v ${diffClass}">${v}${diffIcon}${prevDisplay}</div></div>`;
    });
    if (hasExtra) {
      const n = card.evidence.length - LIMIT;
      h += `<div class="more-toggle"><button data-fact-toggle data-more="+${n}件を表示" data-less="折りたたむ">+${n}件を表示</button></div>`;
    }
    h += "</div>";
  }

  if (card.items && card.items.length) {
    const LIMIT = 3;
    const hasExtra = card.items.length > LIMIT;
    h += '<ul class="fact-list">';
    card.items.forEach((it, idx) => {
      const title = it.title ? `<span class="title">${esc(it.title)}</span>` : "";
      const cls = hasExtra && idx >= LIMIT ? ' class="extra"' : "";
      h += `<li${cls}>${title}<span class="text">${esc(it.text)}</span>` +
           `<button data-cmd="${attr(withIntent(INTENT_ASSUMPTION, it.command))}">コピー</button></li>`;
    });
    if (hasExtra) {
      const n = card.items.length - LIMIT;
      h += `<li class="more-toggle"><button data-fact-toggle data-more="+${n}件を表示" data-less="折りたたむ">+${n}件を表示</button></li>`;
    }
    h += "</ul>";
  }

  if (card.hypothesis) {
    h += '<div class="hyp-box"><div class="k">ここから立てられる仮説例</div>' +
         `<div class="clamp2">${esc(card.hypothesis)}</div></div>`;
  }
  // 見送り（parked）カードの場合、「新しい分析に入る指示」をコピーするボタンを表示
  const isParkedCard = card.hypothesis && ["新規仮説はない", "変数はない", "閉鎖", "棄却済み"].some(p => (card.hypothesis || "").indexOf(p) >= 0);
  if (isParkedCard) {
    const unparkCmd = `見送りカード「${card.title}」を復活。新しい視点で再分析して：(1) 棄却結果・経過を反映した事実の更新、(2) 軌跡・ログの再検証、(3) 未試験の軸または設計変更の仮説立案。--specialist ${state.data?.session?.target || "default"}`;
    h += `<button class="copy unpark" data-cmd="${attr(unparkCmd)}">新しい分析に入る</button>`;
  }
  // 深掘り未了カードには専用の「深掘りする」ボタンを表示
  if (needDeepen) {
    const deepenCmd = `この事実カード「${card.title}」は深掘り未了。まず trajectory / battle_stats で射撃・接近・回避の分布を分析し、python analysis/tools/improvement_session.py deepen "" "<分析で分かったこと>" --card-id "${card.id}" --specialist ${state.data?.session?.target || "default"} で深掘りを記録する。`;
    h += `<button class="copy deepen" data-cmd="${attr(deepenCmd)}">深掘りする</button>`;
  }
  // 事実カードの仮説用フィールド（card_fill.json 由来）を表示する。未記入の枠は出さない
  if (card.cause) {
    const st = card.variable_status || "none";
    const stLabel = {open: "未試験の数値ノブ", direction: "方向カード（構造変更）", closed: "検証済みの軸（再試験禁止）", none: "仮説対象外"}[st] || st;
    h += `<div class="hyp-box"><div class="k">原因・変数（${esc(stLabel)}）</div>` +
         `<div class="clamp2">原因: ${esc(card.cause)}</div>` +
         (card.variable ? `<div class="clamp2">変数: ${esc(card.variable)}</div>` : "") +
         (card.reason ? `<div class="clamp2">理由: ${esc(card.reason)}</div>` : "") +
         `</div>`;
  }
  // 仮説登録ボタン: 深掘り未了なら深掘りを先に促す。雛形（<原因> 等）は出さず、カードの値だけで組む
  if (card.phrase) {
    const target = state.data?.session?.target || "default";
    const fillable = (card.variable_status === "open" || card.variable_status === "direction") && card.prediction;
    let hypothesisCmd = null;
    if (needDeepen) {
      hypothesisCmd = `この事実カード「${card.title}」は深掘り未了。まず trajectory / battle_stats で射撃・接近・回避の分布を分析し、python analysis/tools/improvement_session.py deepen "" "<分析で分かったこと>" --card-id "${card.id}" --specialist ${target} で深掘りを記録してから、仮説を立てる。`;
    } else if (fillable) {
      const text = `${card.phrase} の結果、原因: ${card.cause}。変数: ${card.variable}。判定指標: ${card.judge}。予測: ${card.prediction}`;
      const vname = card.variable_name || "<変数名>";
      hypothesisCmd = `python analysis/tools/improvement_session.py hypothesis "${text}" --specialist ${target} --variable ${vname} --source ${card.source || "log"}`;
    }
    if (hypothesisCmd) {
      h += `<button class="copy hypothesis" data-cmd="${attr(hypothesisCmd)}">仮説登録</button>`;
    }
  }
  if (card.metric) h += `<div class="metric">判定指標: <b>${esc(card.metric)}</b></div>`;
  h += cmdRow(card.command, card.command_label, INTENT_FACT);
  // コマンドも登録itemも持たない事実カード（独自指標・条件トリガー・スコア）は
  // 値そのものを「仮説の材料」としてコピーできるようにする（確認作業は発生しない）
  if (!card.command && !(card.items && card.items.length) && card.phrase) {
    // new fact card (no command, no items, has phrase) always shows MATERIAL button,
    // regardless of extraCls (handled/parked). this ensures unprocessed cards
    // always present as "hypothesis material" for hypothesis building.
    const intent = card.copyIntent === "review" ? INTENT_REVIEW : INTENT_MATERIAL;
    const label = card.copyLabel || "仮説の材料";
    h += `<button class="copy material" data-cmd="${attr(withIntent(intent, card.phrase))}">${esc(label)}</button>`;
  }
  return h + "</div>";
}

// 再描画の前にビルダーの入力値を保存する（自動更新で消えないように）

function syncHypothesis() {
  const box = document.querySelector(".hypho");
  if (!box) return;
  box.querySelectorAll("[data-hy]").forEach(el => {
    state.hy[el.getAttribute("data-hy")] = el.value;
  });
}

function restoreHypothesis() {
  const box = document.querySelector(".hypho");
  if (!box) return;
  box.querySelectorAll("[data-hy]").forEach(el => {
    const v = state.hy[el.getAttribute("data-hy")];
    if (v !== undefined && v !== null) el.value = v;
  });
}

// 事実・原因・変数・指標を選ぶだけで仮説の文と登録コマンドを組み立てる（読み取り専用）

function renderHypothesisBuilder(s, d) {
  const cm = (d.custom_metrics && d.custom_metrics.rows) || [];
  const facts = (s.evidence || []).filter(c => c.phrase && c.id !== "paired");
  const causes = [];
  (s.evidence || []).forEach(c => {
    if (c.id === "constraints" && c.items) {
      c.items.forEach(it => causes.push({ label: it.title, phrase: it.phrase || it.text }));
    }
  });
  const opt = (v, t) => `<option value="${attr(v)}">${esc(t)}</option>`;
  let h = '<p class="meta">選ぶだけで仮説の文と登録コマンドができる（読み取り専用・登録はコピーのみ）。' +
          '数値が無い欄は <code>&lt;…&gt;</code> のままなので Terminal で書き換える。</p>';
  h += '<div class="hypho">';
  h += '<div class="hy-row"><label>事実</label><select data-hy="fact">' +
       opt("", "（事実カードから選ぶ）") +
       facts.map(c => opt(c.id, c.title)).join("") + "</select>" +
       '<input data-hy="fact-text" placeholder="選択すると入る。手で書き直してよい"></div>';
  h += '<div class="hy-row"><label>原因</label><select data-hy="cause">' +
       opt("", "（制約から選ぶ）") +
       causes.map((c, i) => opt(String(i), c.label)).join("") + "</select>" +
       '<input data-hy="cause-text" placeholder="選択すると入る。1変数だけ書く"></div>';
  h += '<div class="hy-row"><label>変数</label>' +
       '<input data-hy="change" placeholder="1変数だけ書く（例: maxSimulShot の上限を 4 → 6）"></div>';
  h += '<div class="hy-row"><label>変数名</label>' +
       '<input data-hy="variable" placeholder="コード上の名前（例: maxSimulShot）。重複防止に使う">' +
       '<span class="meta">事実カードを選ぶと自動で入る</span></div>';
  h += '<div class="hy-row"><label>挙動指標</label><select data-hy="metric">' +
       opt("", "（選ぶ）") +
       cm.map(m => opt(m.id, `${m.label}（${m.value === null ? "値なし" : m.value} → ${m.target === null ? "目標なし" : m.target}）`)).join("") +
       "</select>" +
       '<input data-hy="metric-text" placeholder="何から何に変わるか（例: 8 発 → 20 発以上）"></div>';
  h += '<div class="hy-row"><label>判定指標</label><select data-hy="judge">' +
       opt("", "（選ぶ）") +
       ((d.paired && d.paired.files) || []).map(f => {
         const m = f.metrics || {};
         return opt("paired:" + f.name,
           `${f.name}: avg_score ${m.avg_score} / 自機生存 ${m.avg_our_alive} / 敵生存 ${m.avg_enemy_alive}`);
       }).join("") +
       "</select>" +
       '<input data-hy="judge-text" placeholder="目標値（例: avg_score 0.5 超え / 敵生存 3.0 以下）"></div>';
  h += '<div class="hy-row"><label>--source</label><select data-hy="source">' +
       ["log", "analysis", "code", "official"].map(v => opt(v, v)).join("") +
       "</select>" +
       '<span class="meta">事実カードを選ぶと自動で入る</span></div>';
  h += '<div class="hy-out"><div class="k">組み立てた仮説</div>' +
       '<div id="hypho-text" class="text">—</div></div>';
  h += '<div class="hy-copy-bar"><button id="hypho-copy" class="big" data-cmd="">' +
       "この内容で仮説を登録する（コピー）</button></div>";
  h += "</div>";
  return h;
}

function bindHypothesisBuilder(root, s, d) {
  if (!root || typeof root.querySelector !== "function") return;
  const box = root.querySelector(".hypho");
  if (!box) return;
  const q = name => box.querySelector(`[data-hy="${name}"]`);
  const facts = (s.evidence || []).filter(c => c.phrase && c.id !== "paired");
  const causes = [];
  (s.evidence || []).forEach(c => {
    if (c.id === "constraints" && c.items) {
      c.items.forEach(it => causes.push({ label: it.title, phrase: it.phrase || it.text }));
    }
  });
  const cm = (d.custom_metrics && d.custom_metrics.rows) || [];
  const pairedFiles = (d.paired && d.paired.files) || [];
  const base = 'python analysis/tools/improvement_session.py hypothesis "';
  const fmt = (v, digits) => (v === null || v === undefined ? null : num(v, digits === undefined ? 2 : digits));
  function metricText() {
    const row = cm.find(m => m.id === q("metric").value);
    if (!row) return "";
    const now = fmt(row.value, row.digits);
    const goal = fmt(row.target, row.digits);
    const unit = row.unit || "";
    const higher = row.direction !== "lower";
    if (goal === null) return higher ? `${row.label} を増やす` : `${row.label} を減らす`;
    const head = higher
      ? `${row.label} を ${goal}${unit} 以上に増やす`
      : `${row.label} を ${goal}${unit} 以下に減らす`;
    return now === null ? head : `${head}（現在 ${now}${unit}）`;
  }
  function judgeText() {
    const v = q("judge").value;
    if (!v) return "";
    const name = v.replace("paired:", "").replace(".json", "");
    const f = pairedFiles.find(x => String(x.name).replace(".json", "") === name);
    const m = (f && f.metrics) || {};
    return `判定は ${name} の avg_score ${m.avg_score ?? "<…>"}（0.5 超えが必要）と敵生存 ${m.avg_enemy_alive ?? "<…>"} で見る`;
  }
  function rebuild() {
    const card = facts.find(c => c.id === q("fact").value);
    const fact = q("fact-text").value || (card ? card.phrase : "");
    const ctext = q("cause-text").value;
    const change = q("change").value;
    const mtext = q("metric-text").value || metricText();
    const jtext = q("judge-text").value || judgeText();
    const parts = [];
    parts.push(fact ? `${fact} の結果` : "<事実>");
    if (ctext) parts.push(`${ctext} ため`);
    if (change) parts.push(`${change} とすると`);
    parts.push(mtext || "<挙動指標の予測>");
    parts.push(jtext ? `${jtext} と予測する。` : "<判定指標の目標> と予測する。");
    const text = parts.join("、").replace(/、、/g, "、");
    const out = box.querySelector("#hypho-text");
    if (out) out.textContent = text;
    const vname = (q("variable").value || "").trim() || "<変数名>";
    const line = INTENT_HYPOTHESIS +
      base + text + '" --specialist ' + (s.target || "default") +
      " --variable " + vname +
      " --source " + q("source").value;
    box.querySelectorAll("button[data-cmd]").forEach(b => { b.dataset.cmd = line; });
  }
  const factEl = q("fact");
  if (factEl) factEl.addEventListener("change", () => {
    const card = facts.find(c => c.id === factEl.value);
    q("fact-text").value = card ? card.phrase : "";
    if (card) {
      q("source").value = card.source || "log";
      if (q("variable") && card.variable_name) q("variable").value = card.variable_name;
    }
    rebuild();
  });
  const causeEl = q("cause");
  if (causeEl) causeEl.addEventListener("change", () => {
    const c = causes[Number(causeEl.value)];
    q("cause-text").value = c ? c.phrase : "";
    if (c) q("source").value = "code";
    rebuild();
  });
  ["metric", "judge", "source"].forEach(name => {
    const el = q(name);
    if (el) el.addEventListener("change", rebuild);
  });
  ["fact-text", "cause-text", "change", "variable", "metric-text", "judge-text"].forEach(name => {
    const el = q(name);
    if (el) el.addEventListener("input", rebuild);
  });
  rebuild();
}

function renderDirections(s) {
  const dir = (s && s.directions) || {};
  const items = dir.items || [];
  if (!items.length) return "";
  let h = "<h2>設計の方向（1変数では表せない材料）</h2>";
  if (dir.note) h += `<p class="meta">${esc(dir.note)}</p>`;
  items.forEach(it => {
    h += '<div class="fact direction">';
    h += '<div class="fact-head">' +
         `<span class="title">${esc(it.title)}</span>` +
         '<span class="badge">方向</span>' +
         '<span class="badge">設計</span></div>';
    if (it.summary) h += `<div class="summary">${esc(it.summary)}</div>`;
    if (it.why && it.why.length) {
      h += '<div class="k">なぜ直接接近が失敗するか（実測）</div><ul class="fact-list">';
      it.why.forEach(x => { h += `<li><span class="text">${esc(x)}</span></li>`; });
      h += "</ul>";
    }
    if (it.steps && it.steps.length) {
      h += '<div class="k">候補の設計（1変数ずつに割ってから着手）</div><ul class="fact-list">';
      it.steps.forEach(x => { h += `<li><span class="text">${esc(x)}</span></li>`; });
      h += "</ul>";
    }
    if (it.metrics) h += `<div class="metric">判定指標: <b>${esc(it.metrics)}</b></div>`;
    if (it.records && it.records.length) {
      h += `<div class="meta">記録: ${it.records.map(esc).join(" / ")}</div>`;
    }
    h += "</div>";
  });
  return h;
}

function renderHypothesis(d) {
  syncHypothesis();
  const s = d.session;
  const sessions = s.sessions || [];
  const cur = sessions.find(x => x.specialist === s.target) || sessions[sessions.length - 1];
  let h = "";
  if (!sessions.length) {
    h += '<div class="empty">セッション記録がありません。' +
         '<code>python analysis/tools/improvement_session.py start --specialist default</code></div>';
  }
  if (cur) {
    h += cards([
      { k: "対象 specialist", v: cur.specialist, cls: cur.specialist === s.submitted ? "" : "warn" },
      { k: "提出用 specialist", v: s.submitted || "—", cls: "ok" },
      { k: "開始", v: (cur.started || "—").replace("T", " ") },
      { k: "仮説", v: (cur.hypotheses || []).length, cls: (cur.hypotheses || []).length ? "ok" : "warn" },
      { k: "前提", v: (cur.assumptions || []).length },
    ]);
    if (cur.specialist !== s.submitted) {
      h += `<p class="meta">対象は <b>${esc(cur.specialist)}</b>（ローカル評価専用）。` +
           `提出するのは <b>${esc(s.submitted)}</b>。${esc(cur.specialist)} を submit しない。</p>`;
    }
  }

  h += "<h2>事実カード（ここから仮説を立てる材料）</h2>";
  const facts = (s.evidence || []).filter(c => c.id !== "paired" && c.kind !== "assumption" && c.kind !== "rule");
  const premises = (s.evidence || []).filter(c => c.kind === "assumption" || c.kind === "rule");
  if (!facts.length) {
    h += '<div class="empty">事実カードを組み立てるデータがありません（ログ・軌跡）。</div>';
  } else {
    h += '<div class="facts">' + renderFactGroups(facts) + "</div>";
  }
  if (premises.length) {
    h += "<h2>前提（参照用・処理済み管理の対象外）</h2>";
    h += '<div class="facts">' + premises.map(c => renderFact(c, "")).join("") + "</div>";
  }

  h += renderDirections(s);

  const ow = s.open_work || {};
  const unv = ow.unverified || [], nxt = ow.next_steps || [];
  if (unv.length || nxt.length) {
    h += "<h2>未着手の宿題</h2>" + '<ul class="fact-list">';
    unv.forEach(x => { h += `<li><span class="title">${esc(x.id)} 未検証</span><span class="text">${esc(x.text)}</span></li>`; });
    nxt.forEach(x => { h += `<li><span class="title">${esc(x.id)}${x.at ? " " + esc(x.at) : ""} 次の一手</span><span class="text">${esc(x.text)}</span></li>`; });
    h += "</ul>";
  }

  h += "<h2>仮説ビルダー（選んで登録）</h2>";
  h += renderHypothesisBuilder(s, d);

  document.getElementById("hyp").innerHTML = h;
  restoreHypothesis();
  bindCopy(document.getElementById("hyp"));
  bindFactToggle(document.getElementById("hyp"));
  bindHypothesisBuilder(document.getElementById("hyp"), s, d);
}

function hypOptionLabel(h) {
  const t = String(h.text || "").replace(/\s+/g, " ").trim();
  const short = t.length > 54 ? t.slice(0, 53) + "…" : t;
  return `${h.id || "?"} — ${short}`;
}

function withHypothesis(cmd, id) {
  if (!cmd || !id) return cmd;
  return `${cmd} --hypothesis ${id}`;
}
