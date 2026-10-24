const GIT_INSTRUCTIONS = [
  ["コミット＆プッシュ",
   "変更をコミットしてプッシュして。事前に git status と git diff を確認し、ステージ対象のファイル一覧とコミットメッセージ案を提示して承認を得ること"],
  ["PR作成", "この変更の PR を作成して。タイトルと本文は日本語で書くこと"],
  ["CI確認", "PR の CI テスト結果を確認して。失敗していれば原因を報告して"],
  ["マージ", "PR をマージして"],
];

const GIT_CMD_ROW = '<div class="cmd-row">' +
  '<button class="copy" data-cmd="status">ステータス表示</button>' +
  '<button class="copy" data-cmd="log -1">最近のコミット</button>' +
  '<button class="copy" data-cmd="branch">ブランチ表示</button>' +
  '</div><div class="cmd-row"><span class="row-label">指示</span>' +
  GIT_INSTRUCTIONS.map(([label, text]) =>
    `<button class="copy" data-cmd="${attr(text)}">${esc(label)}</button>`).join("") +
  '</div>';

function renderGit(d) {
  const g = d.git;
  const ab = g.ahead_behind;
  const total = g.dirty.modified + g.dirty.untracked + g.dirty.other;
  const parts = [];
  if (g.dirty.modified) parts.push("変更 " + g.dirty.modified);
  if (g.dirty.untracked) parts.push("未追跡 " + g.dirty.untracked);
  if (g.dirty.other) parts.push("その他 " + g.dirty.other);
  const branchV = g.branch + (ab ? `（ahead ${ab.ahead} / behind ${ab.behind}）` : "");
  let h = GIT_CMD_ROW + cards([
    { k: "ブランチ", v: branchV, cls: ab && ab.ahead ? "warn" : "" },
    { k: "未コミット", v: total ? `${total}（${parts.join("・")}）` : "0",
      cls: total ? "warn" : "ok" },
  ]);
  h += "<h2>リモート</h2>";
  h += table([{label:"項目",num:false},{label:"値",num:false}], [
    ["origin", esc(g.remote || "未設定")], ["upstream", esc(g.upstream || "未設定")],
  ]);
  h += "<h2>直近のコミット</h2>";
  h += g.recent.length ? "<pre>" + esc(g.recent.join("\n")) + "</pre>" : '<div class="empty">なし</div>';
  const rcards = (g.review && g.review.cards) || [];
  if (g.review && g.review.error) {
    h += `<p class="meta">文章レビュー取得失敗: ${esc(g.review.error)}</p>`;
  } else {
    h += "<h2>文章レビュー（文字化け・最新性）</h2>";
    if (g.review && g.review.note) h += `<p class="meta">${esc(g.review.note)}</p>`;
    if (rcards.length) h += renderFactGroups(rcards);
  }
  document.getElementById("git").innerHTML = h;
  bindCopy(document.getElementById("git"));
  bindFactToggle(document.getElementById("git"));
}
