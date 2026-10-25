function renderVerify(d) {
  const s = d.session || {};
  const hyps = s.hypotheses || [];
  // 未検証かどうかは serve.py の pending（validate/record 紐付けを除外）を唯一の正とする
  const pendIds = new Set(s.pending || []);
  const pend = hyps.filter(h => pendIds.has(h.id));
  if (!hyps.length) {
    document.getElementById("verify").innerHTML =
      '<div class="empty">検証する仮説がありません。<br>' +
      '「改善サイクル」タブで仮説を登録すると、ここに検証コマンドが表示されます。<br>' +
      '<code>python analysis/tools/improvement_session.py hypothesis "..." --specialist ' +
      esc(s.target || "default") + ' --source log</code></div>';
    return;
  }
  if (!pend.length) {
    document.getElementById("verify").innerHTML =
      '<div class="empty">未検証の仮説はありません（' + hyps.length + ' 件すべて検証済み）。</div>';
    return;
  }
  if (!state.verifyHyp || !pend.some(h => h.id === state.verifyHyp)) {
    state.verifyHyp = pend[pend.length - 1].id;
  }
  const sel = state.verifyHyp;
  let h = '<div class="verify-pick"><label for="verify-hyp">検証する仮説</label>' +
          `<select id="verify-hyp">` +
          pend.map(x => `<option value="${attr(x.id)}"${x.id === sel ? " selected" : ""}>` +
                        `${esc(hypOptionLabel(x))}</option>`).join("") +
          `</select></div>`;
  const cur = pend.find(x => x.id === sel);
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
  h += cmdRow(
    `変数 ${varName || "（仮説に未設定）"} を agent/args.json / agent/strategy/specialists/default.py に 1変数だけ実装する（他変数は据置、悪化時に原因を切り分けられるよう同時変更しない）。実装後に②build_submission→③1戦ゲート→④ペア評価→⑤validate へ進む。`,
    "① 実装（1変数）", INTENT_IMPL);
  h += cmdRow("python scripts/build_submission.py --deploy", "② ビルド＆デプロイ");
  h += cmdRow(
    'docker exec atla5-cpu bash -lc "cd /workspace && python validate.py --youth 1 --num-validation 1 --visualize 0"',
    "③ 1戦ゲート（悪化なら即 revert・以降の実行を中止）");
  h += cmdRow(
    `docker exec atla5-cpu bash -lc "cd /workspace && python /repo/local_test/run_eval_paired.py --seeds 1,2,3 --colors both --label ${label} --out /workspace/paired/${label}.json"`,
    `④ seed固定ペア評価（label=${label}）`);
  h += cmdRow(
    `python analysis/tools/improvement_session.py validate --specialist ${tgt} --paired workspace/paired/${label}.json --hypothesis ${sel}`,
    "⑤ 仮説IDと紐付け消化（validate。これで pending から消える）");
  h += cmdRow(
    `python analysis/tools/improvement_session.py record --specialist ${tgt} --kind observation --source log --hypothesis ${sel} --direction "<方向>" --changes "<①で実装した内容>" --verification "<ペア評価の判定>" --next-steps "<次>"`,
    "⑥ record で記録（<> を埋めて実行）。採用なら revert せず、不採用なら ① の変更を revert");
  document.getElementById("verify").innerHTML = h;
  const pick = document.getElementById("verify-hyp");
  if (pick) {
    pick.addEventListener("change", () => { state.verifyHyp = pick.value; renderVerify(d); });
  }
  bindCopy(document.getElementById("verify"));
}
