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

buildNav();
showTab((location.hash || "#git").slice(1));
window.addEventListener("hashchange", () => showTab((location.hash || "#git").slice(1)));
document.addEventListener("visibilitychange", () => {
  const auto = document.getElementById ? document.getElementById("auto") : null;
  if (!document.hidden && auto && auto.checked) load(true);
});
window.addEventListener("resize", () => { if (traj.data) drawTraj(); });
load(false);
document.getElementById("refresh").addEventListener("click", () => load(true));
document.getElementById("auto").addEventListener("change", () => schedule());
document.getElementById("interval").addEventListener("change", () => schedule());
function schedule() {
  clearInterval(state.timer);
  if (document.getElementById("auto").checked) {
    state.timer = setInterval(() => load(false), Number(document.getElementById("interval").value));
  }
}
schedule();

