function renderSession(d) {
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
      { k: "仮説", v: (cur.hypotheses || []).length, cls: (cur.hypotheses || []).length ? "ok" : "warn" },
      { k: "サイクル", v: (cur.cycles || []).length },
    ]);
  }

  h += "<h2>改善サイクル（現在地）</h2>" + renderSteps(s.steps);

  if (cur) {
    const items = [
      ...(cur.assumptions || []).map(a => ["前提", JSON.stringify(a)]),
      ...(cur.hypotheses || []).map(x => ["仮説", JSON.stringify(x)]),
      ...(cur.cycles || []).map(x => ["サイクル", JSON.stringify(x)]),
    ];
    h += "<h2>仮説・サイクル・記録</h2>";
    h += items.length
      ? table([{label:"種別",num:false},{label:"内容",num:false}],
          items.map(i => [esc(i[0]), `<code>${esc(i[1])}</code>`]))
      : '<div class="empty">まだ記録がありません。</div>';
  }

  document.getElementById("session").innerHTML = h;
  bindCopy(document.getElementById("session"));
}
