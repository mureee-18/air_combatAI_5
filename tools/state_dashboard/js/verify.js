function renderVerify(d) {
  const s = d.session || {};
  const hyps = s.hypotheses || [];
  // 未検証かどうかは serve.py の pending（validate/record 紐付けを除外）を唯一の正とする
  const pendIds = new Set(s.pending || []);
  const recIds = new Set(s.recordable || []);
  const pend = hyps.filter(h => pendIds.has(h.id));
  const rec = hyps.filter(h => recIds.has(h.id));
  if (!hyps.length) {
    document.getElementById("verify").innerHTML =
      '<div class="empty">検証する仮説がありません。<br>' +
      '「改善サイクル」タブで仮説を登録すると、ここに検証コマンドが表示されます。<br>' +
      '<code>python analysis/tools/improvement_session.py hypothesis "..." --specialist ' +
      esc(s.target || "default") + ' --source log</code></div>';
    return;
  }
  if (!pend.length && !rec.length) {
    document.getElementById("verify").innerHTML =
      '<div class="empty">未検証・記録待ちの仮説はありません（' + hyps.length + ' 件すべて検証済み）。</div>';
    return;
  }
  // 未検証があればそちらを優先、なければ記録待ち
  const allWork = pend.length ? pend : rec;
  if (!state.verifyHyp || !allWork.some(h => h.id === state.verifyHyp)) {
    state.verifyHyp = allWork[allWork.length - 1].id;
  }
  const sel = state.verifyHyp;
  const cur = allWork.find(x => x.id === sel) || pend.find(x => x.id === sel) || rec.find(x => x.id === sel);
  let h = '<div class="verify-pick"><label for="verify-hyp">検証する仮説</label>' +
          `<select id="verify-hyp">` +
          allWork.map(x => `<option value="${attr(x.id)}"${x.id === sel ? " selected" : ""}>` +
                        `${esc(hypOptionLabel(x))}</option>`).join("") +
          `</select></div>`;
  if (cur) {
    h += '<div class="verify-block">' +
         `<h3>${esc(cur.id)}<span class="badge">${esc(cur.source || "")}</span></h3>` +
         `<div class="verify-text">${esc(cur.text || "")}</div></div>`;
  }
  h += `<h2>この仮説（${esc(sel)}）の検証コマンド</h2>`;
  h += '<p class="meta">コピーして Terminal で実行（このタブは読み取り専用）。判定は ' +
       '<b>avg_score / avg_our_alive / avg_enemy_alive</b>。実装はこの検証フローの一部。</p>';
  const tgt = s.target || "default";
  const varName = (cur && cur.variable) || "";
  const label = (varName || "hyp").replace(/[^A-Za-z0-9_]/g, "_");
  const isPending = pendIds.has(sel);
  if (isPending) {
    h += '<p class="meta">実装後に 1 コマンドで baseline check → build → 1戦ゲート → paired評価 → validate → record まで実行します。</p>';
    h += cmdRow(
      `python analysis/tools/verify_cycle.py --specialist ${tgt} --label ${label} --set <変数>=<値> && python analysis/tools/improvement_session.py validate --specialist ${tgt} --paired workspace/paired/${label}.json --hypothesis ${sel} && python analysis/tools/improvement_session.py record --specialist ${tgt} --kind observation --source log --hypothesis ${sel} --direction "<方向>" --changes "<実装した内容>" --verification "<ペア評価の判定>" --next-steps "<次>"`,
      "① 一括検証（baseline check → build → 1戦ゲート → paired評価 → validate → record）", INTENT_IMPL);
  } else {
    h += '<p class="meta">検証済み。record のみ実行して記録を完了する。</p>';
    h += cmdRow(
      `python analysis/tools/improvement_session.py record --specialist ${tgt} --kind observation --source log --hypothesis ${sel} --direction "<方向>" --changes "<実装した内容>" --verification "<ペア評価の判定>" --next-steps "<次>"`,
      "record で記録（<> を埋めて実行）", INTENT_IMPL);
  }
  document.getElementById("verify").innerHTML = h;
  const pick = document.getElementById("verify-hyp");
  if (pick) {
    pick.addEventListener("change", () => { state.verifyHyp = pick.value; renderVerify(d); });
  }
  bindCopy(document.getElementById("verify"));
}
