function agentTreeHtml(files, notPackaged) {
  // agent/ 配下のフラットなファイル一覧を、ディレクトリ構造のツリーにする
  const skip = notPackaged || new Set();
  const root = { dirs: {}, files: [] };
  for (const f of files || []) {
    const parts = String(f.path || "").split("/").filter(Boolean);
    if (!parts.length) continue;
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      const name = parts[i];
      if (!node.dirs[name]) node.dirs[name] = { dirs: {}, files: [] };
      node = node.dirs[name];
    }
    node.files.push({
      name: parts[parts.length - 1],
      path: String(f.path || ""),
      lines: f.lines,
      bytes: f.bytes,
    });
  }
  const lines = [];
  function walk(node, prefix) {
    const items = [
      ...Object.keys(node.dirs).map(n => ({ dir: true, name: n })),
      ...node.files.map(f => ({ dir: false, name: f.name })),
    ].sort((a, b) => a.name.localeCompare(b.name));
    items.forEach((it, idx) => {
      const last = idx === items.length - 1;
      const branch = last ? "└─ " : "├─ ";
      if (it.dir) {
        lines.push(prefix + branch + it.name + "/");
        walk(node.dirs[it.name], prefix + (last ? "   " : "│  "));
      } else {
        const f = node.files.find(x => x.name === it.name);
        const mark = skip.has(f.path) ? "  ※提出 zip には入らない" : "";
        lines.push(prefix + branch + it.name + "  (" + (f ? f.lines : 0) + "行)" + mark);
      }
    });
  }
  walk(root, "");
  return lines.map(l => esc(l)).join("\n");
}

function renderAgents(d) {
  const a = d.agents || {};
  let h = cards([
    { k: "現在の specialist", v: a.specialist || "（未設定）", cls: a.specialist ? "ok" : "warn" },
    { k: "登録済み specialist", v: (a.known_specialists || []).join(" / ") || "（判定不能）" },
    { k: "Agent クラス", v: (a.agents || []).length + " 個" },
    { k: "Specialist（方針）", v: (a.specialists || []).length + " 個" },
    { k: "プリセット", v: (a.presets || []).length + " 個" },
  ]);

  h += "<h2>3層アーキテクチャ（観測・判断・実行）</h2>";
  h += table([{label:"層"},{label:"ディレクトリ"},{label:"ファイル"},{label:"責務"}], [
    ["観測層 (Observation)", "strategy/observation/", "mixin.py (ObservationMixin), escort_id.py (EscortIdentifier)", "センサデータ収集・観測構築・トラック管理・護衛識別"],
    ["判断層 (Judgment)", "strategy/judgment/", "judgment.py (judge→Judgment), target_selection.py, threat_assessment.py, track_history.py, fire_decision.py, navigation.py", "目標選択・脅威評価・回避・航法・射撃判断"],
    ["実行層 (Execution)", "strategy/execution/", "execution.py (execute), deploy.py (DeployMixin), control.py (ControlMixin)", "判断→アクションインデックス変換・ミサイル発射・運動指令"],
    ["統合 (Orchestrator)", "strategy/specialists/default/", "policy.py (step = judge → execute)", "3層を連結"],
  ]);
  h += '<p class="meta">agent.py: ObservationMixin(strategy/observation/) / DeployMixin+ControlMixin(strategy/execution/) で層を分離。判断は DefaultPolicy(strategy/judgment/) に委譲。</p>';
  h += table([{label:"名前"},{label:"状態"},{label:"クラス"},{label:"説明"},{label:"行"}],
    (a.specialists || []).map(sp => [
      esc(sp.name),
      sp.active ? '<span class="ok">使用中</span>' : "",
      esc((sp.classes || []).join(", ")),
      esc(sp.summary || ""),
      String(sp.lines),
    ]));
  (a.specialists || []).forEach(sp => {
    if (!sp.arg_keys || !sp.arg_keys.length) return;
    h += `<div class="meta">${esc(sp.name)} が args.json から読む設定: <code>${esc(sp.arg_keys.join(", "))}</code></div>`;
  });

  h += "<h2>Agent クラス本体（agent/strategy/agents/）</h2>";
  if (!(a.agents || []).length) {
    h += '<p class="meta">このディレクトリには .py がありません。</p>';
  } else {
    h += table([{label:"モジュール"},{label:"クラス"},{label:"説明"},{label:"行"}],
      (a.agents || []).map(ag => [
        esc(ag.name), esc((ag.classes || []).join(", ")), esc(ag.summary || ""), String(ag.lines),
      ]));
  }

  h += "<h2>プリセット（agent/presets/）</h2>";
  if (!(a.presets || []).length) {
    h += '<p class="meta">プリセットはありません。</p>';
  } else {
    h += table([{label:"名前"},{label:"specialist"},{label:"設定数"},{label:"ファイル"}],
      (a.presets || []).map(ps => [
        esc(ps.name), esc(ps.specialist || ""), String(ps.arg_count), esc(ps.file),
      ]));
  }

  h += "<h2>アイデア（agent/strategy/ideas/）</h2>";
  if (!(a.ideas || []).length) {
    h += '<p class="meta">まだideaは追加されていません。</p>';
  } else {
    h += table([{label:"名前"},{label:"ファイル"}],
      (a.ideas || []).map(id => [esc(id.name), esc((id.files || []).join(", "))]));
  }

  // 提出 zip に入らないファイルを実データから求める（パスで比較する）
  const zipSet = new Set(((d.submission || {}).zip_files) || []);
  const notPackaged = new Set((a.files || [])
    .map(f => String(f.path || ""))
    .filter(p => p && !zipSet.has(p)));
  const zipCount = zipSet.size;

  h += `<h2>agent/ 配下のソース（提出 zip は ${zipCount} ファイル）</h2>`;
  const fileCount = (a.files || []).length;
  const totalLines = (a.files || []).reduce((s, f) => s + (f.lines || 0), 0);
  const excluded = notPackaged.size
    ? `提出 zip にはこのうち ${zipCount} ファイルが入り、${notPackaged.size} ファイル（${Array.from(notPackaged).join(", ")}）は入らない。`
    : `提出 zip にはこの ${fileCount} ファイルすべてが入る。`;  h += `<p class="meta">${fileCount} ファイル / 合計 ${totalLines} 行（ディレクトリごとにまとめたツリー）。${esc(excluded)}</p>`;
  h += "<pre>" + agentTreeHtml(a.files, notPackaged) + "</pre>";

  const argsJson = JSON.stringify(a.args || {}, null, 2);
  h += "<h2>args.json（現在の設定）</h2>";
  h += `<div class="cmd"><span class="title">args.json をコピー</span>` +
    `<span class="muted" style="flex:1">下の JSON 項と同一</span>` +
    `<button data-cmd="${attr(argsJson)}">コピー</button></div>`;
  h += "<pre>" + esc(argsJson) + "</pre>";

  const cfg = a.config || {};
  h += "<h2>config.json（提出の modelConfig）</h2>";
  h += '<p class="meta">specialist が使う modelConfig。turnTable / speedTable は行動（turn/speed の index）の値。</p>';
  (cfg.sections || []).forEach(sec => {
    h += `<h3>${esc(sec.name)}</h3>`;
    if (sec.rows && sec.rows.length) {
      h += table([{label:"項目"},{label:"値"}], sec.rows.map(r => [esc(r.key), esc(r.value)]));
    }
    Object.keys(sec.tables || {}).forEach(k => {
      const vals = sec.tables[k] || [];
      h += `<div class="meta">${esc(k)} (${vals.length}):</div>`;
      h += `<pre>${esc(vals.map(v => String(v)).join(", "))}</pre>`;
    });
  });
  if (cfg.raw) {
    h += `<div class="cmd"><span class="title">config.json をコピー</span>` +
      `<span class="muted" style="flex:1">下の JSON 項と同一</span>` +
      `<button data-cmd="${attr(cfg.raw)}">コピー</button></div>`;
    h += "<pre>" + esc(cfg.raw) + "</pre>";
  }

  document.getElementById("agents").innerHTML = h;
  bindCopy(document.getElementById("agents"));
}

// ── 観測・判断・行動 の描画（それぞれ独立した関数）─────────────────
