function renderLogs(d) {
  const l = d.logs;
  let h = cards([
    { k: "世代数", v: l.generations.length },
    { k: "合計サイズ", v: l.total_size_h },
  ]);
  h += "<h2>ログ世代（workspace/results*）</h2>";
  h += table([{label:"世代"},{label:"ログ数",num:true},{label:"サイズ",num:true},{label:"更新",num:false},{label:"最新ログ",num:false}],
    l.generations.map(g => [esc(g.name), g.logs, esc(g.size_h), esc(g.mtime), esc(g.newest || "—")]));
  const s = l.newest_stats;
  h += "<h2>最新ログの挙動指標</h2>";
  if (!s) h += '<div class="empty">解析できるログがありません</div>';
  else if (s.error) h += `<pre>${esc(s.error)}</pre>`;
  else {
    h += `<p class="meta">${esc(s.log)} / ${s.steps} ステップ / <span class="pill">${esc(s.mode)}</span></p>`;
    h += table([{label:"機体"},{label:"敵探知",num:true},{label:"被弾警報",num:true},{label:"射撃指示",num:true},
                {label:"護衛対象機",num:true},{label:"最近接[km]",num:true},{label:"最小残弾",num:true}],
      s.agents.map(a => [esc(a.agent), a.enemy_seen, a.threat, a.fire_orders, a.escorted_seen,
        a.min_dist_km === null ? "—" : num(a.min_dist_km, 1), a.min_rmsls === null ? "—" : a.min_rmsls]));
    if (s.mode !== "自作エージェント") {
      h += '<p class="meta">baseline / BenchMark のログは observation がスカラー構造のため指標は 0 になります。自作エージェントのログを選ぶと値が出ます。</p>';
    }
  }
  document.getElementById("logs").innerHTML = h;
}
