function renderEnv(d) {
  const e = d.environment;
  const drift = e.deploy_drift;
  const driftCls = drift === null ? "" : (drift.args_match && drift.config_match ? "ok" : "warn");
  const driftTxt = drift === null ? "未配置"
    : ((drift.args_match && drift.config_match) ? "一致" : ",要再ビルド");
  let h = cards([
    { k: "specialist (repo)", v: e.repo_specialist },
    { k: "workspace", v: e.workspace.exists ? e.workspace.size_h : "無し", cls: e.workspace.exists ? "" : "bad" },
    { k: "シミュレータ", v: e.workspace.simulator_ready ? "配置済み" : "未配置", cls: e.workspace.simulator_ready ? "ok" : "bad" },
    { k: "配置ドリフト", v: driftTxt, cls: driftCls },
    { k: "ホスト", v: e.host.python },
  ]);
  h += "<h2>Docker コンテナ</h2>";
  if (!e.docker.available) h += '<div class="empty">docker コマンドを実行できません（Docker Desktop が起動中か確認）</div>';
  else if (!e.docker.containers.length) h += '<div class="empty">起動中のコンテナはありません</div>';
  else h += table([{label:"コンテナ"},{label:"ステータス"},{label:"イメージ"}],
    e.docker.containers.map(c => [esc(c.name), esc(c.status), esc(c.image)]));
  h += "<h2>配置（workspace/Agents）</h2>";
  h += table([{label:"Agent ディレクトリ"},{label:"備考"}],
    (e.workspace.agents.length ? e.workspace.agents : ["—"]).map(a =>
      [esc(a), a === "MyAgent" ? "ビルドした提出物" : (a === "BenchMark" ? "公式ベンチマーク" : "")]));
  h += "<h2>ホスト情報</h2>";
  h += table([{label:"項目"},{label:"値"}], [
    ["OS", esc(e.host.platform)],
    ["Python (ホスト)", esc(e.host.python)],
    ["numpy (ホスト)", e.host.numpy ? "導入済み" : "未導入（コンテナ内で実行するツール.matrix)"],
  ]);
  document.getElementById("env").innerHTML = h;
}
