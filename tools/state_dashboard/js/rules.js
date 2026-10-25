function renderRules(d) {
  const r = d.rules || { meta: {}, groups: [] };
  const m = r.meta || {};
  let h = cards([
    { k: "コンペ", v: m.name || "—", cls: "" },
    { k: "対象", v: m.division || "—" },
    { k: "task key", v: (m.task_key || "—").slice(0, 8) },
    { k: "参照元", v: (r.source_files ? Object.values(r.source_files).filter(Boolean).length : 0) + " / 2" },
  ]);
  if (m.url) {
    h += `<p><a href="${esc(m.url)}" target="_blank" rel="noreferrer" style="color:var(--accent)">公式ページを開く（規約の正は公式ページ）</a></p>`;
  }

  h += '<div class="rule-card"><h3>出所</h3><div class="rule-groups">';
  (m.sources || []).forEach(s => {
    h += `<div class="rule-group"><div class="rule-group-title">${esc(s.label)}</div>` +
         `<ul class="rule-items"><li><code>${esc(s.path)}${s.lines ? ":" + esc(s.lines) : ""}</code></li>` +
         `<li>${esc(s.note || "")}</li></ul></div>`;
  });
  h += "</div>";
  if (m.note) h += `<p class="meta">${esc(m.note)}</p>`;
  h += "</div>";

  (r.groups || []).forEach(g => {
    h += `<div class="rule-card"><h3>${esc(g.title)}</h3><div class="rule-groups"><div class="rule-group">`;
    h += `<ul class="rule-items">`;
    (g.items || []).forEach(it => { h += `<li>${inlineCode(it)}</li>`; });
    h += "</ul></div></div></div>";
  });
  document.getElementById("rules").innerHTML = h;
}
