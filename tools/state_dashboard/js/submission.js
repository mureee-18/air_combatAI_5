function renderSub(d) {
  const s = d.submission;
  let h = cards([
    { k: "specialist", v: s.specialist, cls: s.specialist_allowed ? "ok" : "bad" },
    { k: "提出可能", v: s.specialist_allowed ? "YES" : "NO", cls: s.specialist_allowed ? "ok" : "bad" },
    { k: "submit.zip", v: s.zip.exists ? s.zip.size_h : "未ビルド", cls: s.zip.exists ? "ok" : "warn" },
    { k: "ゲート", v: s.gate_ok ? "OK" : "BLOCK", cls: s.gate_ok ? "ok" : "warn" },
  ]);
  const argsJson = JSON.stringify(s.args, null, 2);
  const gateText = s.gate_output.join("\n");
  h += "<h2>args.json</h2>";
  h += `<div class="cmd"><span class="title">args.json をコピー</span>` +
    `<span class="muted" style="flex:1">下の JSON 項と同一</span>` +
    `<button data-cmd="${attr(argsJson)}">コピー</button></div>`;
  h += "<pre>" + esc(argsJson) + "</pre>";
  h += "<h2>提出コマンド</h2>";
  const subGroup = (d.commands || []).find(g => g.group === "提出");
  (subGroup ? subGroup.items : []).forEach(it => { h += cmdRow(it.cmd, it.title); });
  h += "<h2>提出物のルートファイル</h2>";
  h += table([{label:"ファイル"},{label:"有無"}],
    Object.keys(s.zip_entries).map(k => [esc(k), s.zip_entries[k] ? '<span class="ok">あり</span>' : '<span class="bad">なし</span>']));
  h += "<h2>提出 zip の中身</h2>";
  if ((s.zip_files || []).length) {
    h += `<p class="meta">${s.zip_files.length} ファイル（実際に提出されるもの）</p>`;
    h += "<pre>" + esc((s.zip_files || []).join("\n")) + "</pre>";
  } else {
    h += '<p class="meta">zip が無い、または空です。python scripts/build_submission.py でビルドしてください。</p>';
  }
  h += "<h2>提出前ゲート（tools/hooks/pre_submit_gate.py）</h2>";
  h += "<p class=\"meta\">ゲートは <code>" + esc(s.confirm_env) + "=1</code> なしの実行を BLOCK 扱いします（意図した設計）。</p>";
  h += `<div class="cmd"><span class="title">ゲート出力をコピー</span>` +
    `<span class="muted" style="flex:1">下の出力欄と同一</span>` +
    `<button data-cmd="${attr(gateText)}">コピー</button></div>`;
  h += "<pre>" + esc(gateText) + "</pre>";
  if (s.zip.exists) h += `<p class="meta">ビルド日時: ${esc(s.zip.mtime)} / サイズ: ${esc(s.zip.size_h)}</p>`;
  document.getElementById("sub").innerHTML = h;
  bindCopy(document.getElementById("sub"));
}
