const TABS = [
  ["env", "環境"], ["sub", "提出"], ["agents", "エージェント"], ["decision", "観測・判断・行動"], ["eval", "評価"], ["logs", "ログ"],
  ["hyp", "仮説登録"], ["session", "改善サイクル"], ["verify", "検証"], ["git", "git"], ["cmd", "コマンド"], ["rules", "ルール"],
  ["traj", "自機視点"], ["battle", "戦場俯瞰"],
];

const nav = document.getElementById("nav");

const state = { data: null, timer: null, selected: null, verifyHyp: "", hy: {} };

function esc(s) {
  return String(s === null || s === undefined ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
// HTML 属性値用のエスケープ（コマンド内の " が属性を壊すため必須）

function attr(s) {
  return esc(s).replace(/"/g, "&quot;");
}

function num(v, digits) {
  if (v === null || v === undefined || v === "") return "—";
  return Number(v).toFixed(digits === undefined ? 2 : digits);
}

function table(headers, rows) {
  if (!rows.length) return '<div class="empty">データがありません</div>';
  let h = "<table><thead><tr>";
  headers.forEach(x => h += `<th>${esc(x.label)}</th>`);
  h += "</tr></thead><tbody>";
  rows.forEach(r => {
    h += "<tr>";
    r.forEach((c, i) => {
      const cls = headers[i].num ? ' class="num"' : "";
      h += `<td${cls}>${c}</td>`;
    });
    h += "</tr>";
  });
  return h + "</tbody></table>";
}

function cards(items) {
  return '<div class="cards">' + items.map(i =>
    `<div class="card"><div class="k">${esc(i.k)}</div><div class="v ${i.cls || ""}">${esc(i.v)}</div></div>`
  ).join("") + "</div>";
}

function copy(text, btn) {
  const flash = (label, ms) => {
    const old = btn.textContent;
    btn.textContent = label;
    setTimeout(() => { btn.textContent = old; }, ms);
  };
  const ok = () => flash("コピー済", 1200);
  const ng = () => flash("コピー失敗", 2000);
  const legacy = () => {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      const done = document.execCommand("copy");
      document.body.removeChild(ta);
      if (done) ok(); else ng();
    } catch (e) {
      ng();
    }
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(ok).catch(legacy);
  } else {
    legacy();
  }
}

const INTENT_FACT = "# 事実確認（仮説登録なし）— 実行して結果のみ報告\n";

const INTENT_MATERIAL = "# 仮説の材料 — この事実を前提に仮説を1本立ててください\n";

const INTENT_ASSUMPTION = "# 前提登録 — この行をAIに貼って登録依頼\n";

const INTENT_HYPOTHESIS = "# 仮説登録 — この行をAIに貼って登録依頼\n";

const INTENT_REVIEW = "# 文書レビュー — この指摘の修正をお願いします\n";

const INTENT_REOPEN = "# 見直し依頼 — この材料は対応不要とされているが、見直しを求めます。理由も書いてください\n";

const INTENT_IMPL = "# 実装依頼 — この行をAIに貼って1変数の実装を依頼（実装→build_submission --deploy→③ゲート→④ペア評価→⑤validate）\n";

function withIntent(intent, cmd) {
  return cmd ? intent + cmd : cmd;
}

function cmdRow(cmd, label, intent) {
  if (!cmd) return "";
  const copied = intent ? intent + cmd : cmd;
  return `<div class="cmd"><span class="title">${esc(label || "コマンド")}</span>` +
         `<code>${esc(cmd)}</code><button data-cmd="${attr(copied)}">コピー</button></div>`;
}

function bindCopy(root) {
  root.querySelectorAll("button[data-cmd]").forEach(btn => {
    btn.addEventListener("click", () => copy(btn.dataset.cmd, btn));
  });
}

// 処理済み＝記録連動のみ。コピーしただけでは付けない。

function showTab(key) {
  TABS.forEach(([k]) => {
    document.getElementById("nav-" + k).classList.toggle("active", k === key);
    document.getElementById("tab-" + k).classList.toggle("active", k === key);
  });
  location.hash = key;
  if (key === "traj") {
    loadTrajEntries(false);
    if (traj.data) drawTraj();
  }
}

function buildNav() {
  TABS.forEach(([k, label]) => {
    const b = document.createElement("button");
    b.id = "nav-" + k; b.textContent = label;
    b.addEventListener("click", () => showTab(k));
    nav.appendChild(b);
  });
}

async function load(force) {
  try {
    try {
      const bres = await fetch("/api/build", { cache: "no-store" });
      const bdata = await bres.json();
      const meta = document.querySelector ? document.querySelector('meta[name="x-build"]') : null;
      const cur = meta ? meta.getAttribute("content") : "";
      if (cur && bdata.build && bdata.build !== cur) {
        try { sessionStorage.setItem("dash-keep-tab", "1"); } catch (e) {}
        location.reload();
        return;
      }
    } catch (e) {}
    const res = await fetch("/api/summary" + (force ? "?force=1" : ""), { cache: "no-store" });
    const data = await res.json();
    state.data = data;
    const stampEl = document.getElementById("stamp");
    const ageMs = Date.parse(String(data.generated_at || "").replace(" ", "T"));
    const stale = !isNaN(ageMs) && (Date.now() - ageMs > 180000);
    stampEl.textContent = "更新 " + data.generated_at + (stale ? "（古い可能性あり・再読み込み推奨）" : "");
    if (stampEl.classList) stampEl.classList.toggle("warn", !!stale);
    // Compute evidence diffs before rendering
    markEvidenceDiffs(data);
    renderEnv(data); renderSub(data); renderAgents(data); renderDecision(data); renderEval(data); renderLogs(data);
    renderHypothesis(data); renderSession(data); renderVerify(data); renderGit(data); renderCmd(data); renderRules(data);
  } catch (err) {
    document.getElementById("stamp").textContent = "読み込み失敗: " + err;
  }
}

function markEvidenceDiffs(data) {
  if (!data.session?.evidence) return;
  const prev = JSON.parse(localStorage.getItem("prev_evidence") || "{}");
  const curr = {};
  data.session.evidence.forEach(card => {
    const cardId = card.id || card.title;
    curr[cardId] = card.evidence || [];
    const prevCard = prev[cardId] || [];
    (card.evidence || []).forEach((e, i) => {
      const prevE = prevCard.find(p => p.label === e.label);
      if (!prevE) {
        e._diff = "new";
      } else if (prevE.value !== e.value) {
        e._diff = "changed";
        e._prevValue = prevE.value;
      }
    });
  });
  localStorage.setItem("prev_evidence", JSON.stringify(curr));
}
