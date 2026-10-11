"""開発状況ダッシュボードの回帰テスト.

`--once` / HTTP エンドポイントが壊れていないこと、
そして収集 JSON のキー構成が変わっていないことを確認する。
"""

import importlib.util
import json
import re
import shutil
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVE_PATH = REPO_ROOT / "tools" / "state_dashboard" / "serve.py"
INDEX_PATH = REPO_ROOT / "tools" / "state_dashboard" / "index.html"

TABS = ["環境", "提出", "評価", "ログ", "仮説登録", "改善サイクル", "git", "コマンド",
        "コンペルール", "自機視点", "戦場俯瞰"]


def load_serve():
    spec = importlib.util.spec_from_file_location("state_dashboard_serve", SERVE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


serve = load_serve()


def test_index_has_all_tabs():
    html = INDEX_PATH.read_text(encoding="utf-8")
    for tab in TABS:
        assert f'"{tab}"' in html or f">{tab}<" in html
    assert 'id="auto"' in html
    assert "api/summary" in html


def test_index_has_trajectory_replay_wiring():
    html = INDEX_PATH.read_text(encoding="utf-8")
    assert 'id="tab-traj"' in html
    assert "api/replays" in html
    assert "api/replay?log=" in html
    for hook in ["traj-canvas", "traj-seek", "traj-play", "drawTraj", "openTraj"]:
        assert hook in html
    for hook in ["traj-shots", "traj-aim", "missile_model", "frame.aim", "frame.shots", "戦域境界"]:
        assert hook in html
    for hook in ["drawAimLayer", "drawShotsLayer", "ロック", "残弾", "発射!", "shotTargetCache", "撃った相手",
             "pushFrameToasts", "drawEventToasts", "EVENT_TOAST_FRAMES", "初発見", "命中", "空振り"]:
        assert hook in html
    # 射撃の視認性: 弾の実線は白縁取り付き3px、ロック線は白破線、編隊軌跡は減光
    for hook in ["弾の実線（発射点→現在）: 目標ロストリングと同じ太さ（1.5px）に細い白縁取り",
                 "ロック線は各機のスロット色の破線（実線の編隊軌跡と破線なら区別でき、同色同士で埋もれない）",
                 "trajColor(slot) + \"4d\""]:
        assert hook in html, f"missing visual hook: {hook}"
    for hook in ["TRAJ_SENSOR_COLORS", "探知/再探知", "目標ロスト", "レーダ ≤80 km", "IRST ≤120 km"]:
        assert hook in html
    assert "enemy_xy" not in html  # 座標復元は Python 側。JS で二重実装しない


def test_index_has_battle_overview_wiring():
    html = INDEX_PATH.read_text(encoding="utf-8")
    assert 'id="tab-battle"' in html
    for hook in ["battle-canvas", "battle-seek", "battle-play", "drawBattle", "openBattle",
                 "buildBattleShell", "renderBattleLegend", "drawBattleIcon"]:
        assert hook in html
    for hook in ["frame.teams", "戦場俯瞰", "buildBattleShell"]:
        assert hook in html
    assert 'side === "own"' in html


def test_index_eval_goal_board_replaces_detail_rows():
    html = INDEX_PATH.read_text(encoding="utf-8")
    for hook in ["目標（独自指標）", "renderGoals", "goalPct", "goalStatus",
                 "add_metric.py --id", 'bindCopy(document.getElementById("eval"))',
                 "目標の編集"]:
        assert hook in html, f"missing goal board hook: {hook}"
    # 明細（1戦ごとの表）は消して同じ場所に目標ボードを置く
    assert "<h2>明細</h2>" not in html
    assert 'id="rows"' not in html
    assert "renderRows" not in html


def test_commands_include_trajectory_restore():
    joined = "\n".join(item["cmd"] for group in serve.COMMANDS for item in group["items"])
    assert "tools/battle_analyzer/trajectory.py" in joined


def test_collect_replays_shape():
    replays = serve.collect_replays(limit=3)
    assert set(replays.keys()) == {"entries", "scanned_skipped", "limit"}
    assert len(replays["entries"]) <= 3
    for entry in replays["entries"]:
        assert set(entry.keys()) == {"log", "mtime", "age_s", "size_h", "frames", "own_length", "has_ammo"}
        assert entry["log"].startswith("workspace/results")
        assert entry["log"].endswith(".json")


def test_replay_payload_rejects_unsafe_or_non_replayable_paths():
    for bad in ["", "../../secrets.json", "agent/args.json", "workspace/results/does_not_exist/log_0.json"]:
        with pytest.raises(ValueError):
            serve.replay_payload(bad)


@pytest.mark.skipif(
    not list(REPO_ROOT.glob("workspace/results*/**/log_*.json")),
    reason="実ログが無い環境ではスキップ",
)
def test_replay_payload_round_trip_on_real_log():
    for entry in serve.collect_replays(limit=5)["entries"]:
        payload = serve.replay_payload(entry["log"])
        assert payload["frame_count"] == entry["frames"]
        assert set(payload.keys()) == {
            "log",
            "slots",
            "frame_count",
            "own_length",
            "has_ammo",
            "bounds",
            "sensor_ranges",
            "missile_model",
            "frames",
            "events",
            "result",
        }
        assert len(payload["frames"]) == payload["frame_count"]
        assert payload["slots"]
        assert payload["missile_model"]["speed_kms"] > 0
        for frame in payload["frames"]:
            assert set(frame.keys()) == {
                "t",
                "ptime",
                "own",
                "enemy",
                "threat",
                "aim",
                "shots",
                "teams",
                "action",
                "events",
            }
            assert isinstance(frame["aim"], list)
            assert isinstance(frame["shots"], list)
            for shot in frame["shots"]:
                assert shot["t0"] <= frame["t"]
                assert shot["age"] <= shot["flight"]
        return
    pytest.skip("自作 Agent 形式のログがありません")


def test_collect_environment_shape():
    env = serve.collect_environment()
    assert set(env.keys()) == {"host", "docker", "workspace", "deploy_drift", "repo_specialist"}
    assert set(env["workspace"].keys()) >= {"exists", "simulator_ready", "size_h", "agents"}
    assert isinstance(env["docker"]["containers"], list)


def test_collect_paired_shape():
    paired = serve.collect_paired()
    assert set(paired.keys()) >= {"files", "best"}
    for entry in paired["files"]:
        assert set(entry.keys()) == {"name", "mtime", "metrics", "rows"}


def test_collect_git_shape():
    git = serve.collect_git()
    assert set(git.keys()) == {"branch", "head", "remote", "upstream", "ahead_behind", "dirty", "recent", "review"}
    assert set(git["dirty"].keys()) == {"modified", "untracked", "other"}
    assert isinstance(git["review"].get("cards"), list)


def test_commands_are_documented_and_copyable():
    all_cmds = [item["cmd"] for group in serve.COMMANDS for item in group["items"]]
    joined = "\n".join(all_cmds)
    assert "run_eval_paired.py" in joined
    assert "tools/hooks/pre_submit_gate.py" in joined
    assert "scripts/build_submission.py" in joined
    assert all(cmd.strip() for cmd in all_cmds)


def test_rules_json_contract():
    rules = serve.collect_rules()
    assert set(rules.keys()) >= {"meta", "groups", "source_files"}
    assert rules["meta"]["division"] == "ユース部門"
    assert rules["meta"]["task_key"] == "5564d022dac44dd498c97aa82efab260"
    titles = [g["title"] for g in rules["groups"]]
    assert any("採点式" in t for t in titles)
    assert any("提出ルール" in t for t in titles)
    for group in rules["groups"]:
        assert group["items"]
        for item in group["items"]:
            assert isinstance(item, str) and item.strip()


def test_scoring_formula_matches_fight_py():
    fight = REPO_ROOT / "workspace" / "src" / "fight.py"
    if not fight.exists():
        pytest.skip("fight.py が無い環境ではスキップ")
    source = fight.read_text(encoding="utf-8")
    assert "0.6" in source and "0.3 * hit_rate" in source
    assert "time_bonus" in source
    rules_text = json.dumps(serve.collect_rules(), ensure_ascii=False)
    assert "0.6 + 0.3" in rules_text
    assert "0.1" in rules_text


def test_collect_session_keeps_legacy_keys_and_adds_workflow():
    session = serve.collect_session()
    # 既存契約: sessions 配列はそのまま残す
    assert isinstance(session["sessions"], list)
    for entry in session["sessions"]:
        assert {"specialist", "started", "assumptions", "hypotheses", "cycles"} <= set(entry.keys())
    # 追加情報
    assert {"target", "submitted", "steps", "evidence"} <= set(session.keys())
    assert {"hypotheses", "cycles"} <= set(session.keys())
    assert session["submitted"] == (serve.load_json(serve.REPO_ROOT / "agent" / "args.json") or {}).get(
        "specialist"
    )


def test_session_steps_are_ordered_and_labelled():
    session = serve.collect_session()
    if not session["sessions"]:
        pytest.skip("セッション記録が無い環境ではスキップ")
    steps = session["steps"]
    assert [s["key"] for s in steps] == ["hypothesis", "change", "verify", "validate", "record"]
    order = {"done": 0, "current": 1, "todo": 2}
    assert [order[s["state"]] for s in steps] == sorted(order[s["state"]] for s in steps)
    for step in steps:
        assert step["label"] and step["hint"] and step["detail"]
        if step["key"] != "change":
            assert step["command"].startswith("python ") or "docker exec" in step["command"]
    # verify / validate / record は --hypothesis を差し込む対象を指定する
    assert steps[2]["hyp_arg"] == "command"
    assert steps[3]["hyp_arg"] == "command2"
    assert steps[4]["hyp_arg"] == "command"


def test_session_evidence_cards_are_observable_and_have_sources():
    cards = serve.collect_session()["evidence"]
    assert cards, "事実カードが1つも生成されていない"
    for card in cards:
        assert card["kind"] in {"observation", "assumption", "rule"}
        assert card["source"] in {"log", "code", "official"}
        assert card["title"].strip()
        if card["kind"] == "rule":
            assert card["source"] == "official"
        if card.get("items"):
            for item in card["items"]:
                assert item["text"].strip()
                # 前提テキストが引用符で閉じられないこと（囲みの2個だけが "）
                assert item["command"].count('"') == 2
                assert "--specialist" in item["command"]
        else:
            assert card["evidence"], f"{card['id']} に観測値がない"
            for row in card["evidence"]:
                assert row["label"] and row["value"] is not None


def test_session_evidence_paired_card_reflects_metrics():
    paired = serve.collect_paired()
    with_metrics = [f for f in paired["files"] if (f.get("metrics") or {}).get("avg_score") is not None]
    cards = serve.collect_session()["evidence"]
    card = next((c for c in cards if c["id"] == "paired"), None)
    if len(with_metrics) < 2:
        assert card is None
        return
    assert card is not None
    labels = [row["label"] for row in card["evidence"]]
    for entry in with_metrics:
        name = (entry.get("metrics") or {}).get("label") or entry["name"]
        assert f"{name} avg_score" in labels


def test_session_steps_mark_hypothesis_current_when_empty():
    session = serve.collect_session()
    if not session["sessions"]:
        pytest.skip("セッション記録が無い環境ではスキップ")
    current = session["sessions"][-1]
    steps = {s["key"]: s for s in session["steps"]}
    if not current["hypotheses"]:
        assert steps["hypothesis"]["state"] in {"current", "done"}


def test_index_renders_session_steps_and_fact_cards():
    html = INDEX_PATH.read_text(encoding="utf-8")
    for hook in ["renderSteps", "renderFact", "STEP_STATE_LABEL", "bindCopy", "attr"]:
        assert hook in html
    assert "fact-grid" in html and "hyp-box" in html
    # コマンド内の " が data-cmd を壊さないこと
    assert 'data-cmd="${attr(' in html
    assert 'data-cmd="${esc(' not in html


def test_index_has_verify_tab_with_hypothesis_selector():
    html = INDEX_PATH.read_text(encoding="utf-8")
    # 「検証」タブが追加されている
    assert 'id="tab-verify"' in html
    assert '<div id="verify"></div>' in html
    assert '"verify", "検証"' in html
    # renderVerify が仮説セレクタを持ち、選択 id を --hypothesis として差し込む
    start = html.index("function renderVerify")
    end = html.index("const GIT_INSTRUCTIONS")
    block = html[start:end]
    assert 'id="verify-hyp"' in block
    assert "withHypothesis(val.command2" in block
    assert "--hypothesis" in html
    # 1〜3 に分割せず、ペア評価+記録を1コマンドに集約する
    assert "cmdRow([runPair, recPair]" in block
    assert 'join(" ; ")' in block
    assert "steps.forEach" not in block
    # 検証タブにはカード（対象 specialist / 検証する仮説 / 現在地）を出さない
    assert "cards(" not in block
    assert "現在地" not in block
    # 検証済みの仮説はセレクタから除外し、未検証の仮説だけ表示する
    assert "hyps.filter(h => !verified.has(h.id))" in block
    assert "検証済み" in block  # 全件検証済みのときのメッセージ
    assert 'bindCopy(document.getElementById("verify"))' in block
    # 仮説が無いときはコマンドを描画しない（早期 return 後に1コマンドを描く）
    assert block.index("cmdRow([runPair, recPair]") > block.index("return;")


def test_index_hypothesis_tab_hides_registered_fact_cards():
    # 「仮説登録」タブは登録済み（過去の検証）を材料にした事実カードを出さない
    html = INDEX_PATH.read_text(encoding="utf-8")
    start = html.index("function renderHypothesis")
    end = html.index("function renderSession")
    block = html[start:end]
    assert 'c.id !== "paired"' in block
    assert "sortByHandled(facts.slice())" in block
    assert "s.evidence.map(renderFact)" not in block


def test_handled_materials_sink_and_clear():
    html = INDEX_PATH.read_text(encoding="utf-8")
    assert "opencode-handled-materials-v1" in html
    assert "data-handled-key" in html
    assert "sortByHandled" in html
    assert "reset-handled" in html
    assert ".fact.handled" in html


def test_index_improvement_cycle_tab_unchanged():
    # 「改善サイクル」タブ（renderSteps）は読み取り専用のまま。コマンドは描画しない
    html = INDEX_PATH.read_text(encoding="utf-8")
    start = html.index("function renderSteps")
    end = html.index("function renderFact")
    assert "cmdRow" not in html[start:end]


def test_fact_cards_have_phrase_for_the_hypothesis_builder():
    # 仮説ビルダーへ差し込む短句（phrase）が各カードに用意されていること
    cards = serve.collect_session()["evidence"]
    for card in cards:
        assert card.get("phrase"), f"{card['id']} に phrase がない"
        assert len(card["phrase"]) <= 120, f"{card['id']} の phrase が長すぎる"
    for card in cards:
        if card["id"] == "constraints":
            for item in card["items"]:
                assert item.get("phrase")


def test_hypothesis_builder_has_inputs_and_one_copy_button():
    html = INDEX_PATH.read_text(encoding="utf-8")
    for key in ("fact", "cause", "change", "metric", "judge", "source"):
        assert f'data-hy="{key}"' in html
    assert 'id="hypho-text"' in html
    assert 'id="hypho-copy"' in html
    assert "bindHypothesisBuilder" in html
    assert "renderHypothesisBuilder(s, d)" in html
    # コピーの無音失敗を防ぐ表示と、AIに貼って登録させる見出し行
    assert "コピー失敗" in html
    assert "# 仮説登録 — この行をAIに貼って登録依頼\\n" in html


HARNESS_JS = r"""
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf-8");
const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join("\n");
const payload = JSON.parse(fs.readFileSync(process.argv[3], "utf-8"));
function stubEl() {
  return {
    value: "", textContent: "", dataset: {}, listeners: {},
    addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); },
    fire(t) { (this.listeners[t] || []).forEach(fn => fn()); },
  };
}
const els = {};
function el(id) {
  if (!els[id]) {
    els[id] = Object.assign(stubEl(), {
      innerHTML: "",
      classList: { toggle() {}, add() {}, remove() {} },
      appendChild() {}, prepend() {}, getContext() { return null; },
      querySelectorAll() { return []; },
    });
  }
  return els[id];
}
global.document = { getElementById: el, querySelectorAll: () => [], createElement: () => el("c"),
  addEventListener() {} };
global.window = { addEventListener() {} };
global.location = { hash: "" };
global.navigator = { clipboard: { writeText: () => Promise.resolve() } };
global.setInterval = () => 0;
global.clearInterval = () => {};
global.fetch = () => Promise.resolve({ json: () => Promise.resolve(payload) });
eval(js);

const s = payload.session, d = payload;
const hy = {};
["fact","cause","change","metric","judge","source",
 "fact-text","cause-text","metric-text","judge-text"].forEach(n => { hy[n] = stubEl(); });
const out = stubEl(), btn = stubEl();
const box = {
  querySelector(sel) {
    const m = sel.match(/data-hy="([^"]+)"/);
    if (m) return hy[m[1]];
    return sel === "#hypho-text" ? out : null;
  },
  querySelectorAll(sel) { return sel === "button[data-cmd]" ? [btn] : []; },
};
const root = { querySelector(sel) { return sel === ".hypho" ? box : null; } };

const card = (s.evidence || []).find(c => c.id === "constraints");
const metric = ((d.custom_metrics || {}).rows || []).find(m => m.id === "launch_count");
const files = (d.paired || {}).files || [];
const def = files.filter(f => String(f.name).indexOf("default") >= 0)[0];
if (!card || !metric || !def) { console.log("SKIP"); process.exit(0); }

hy.fact.value = "constraints";
hy.metric.value = "launch_count";
hy.judge.value = "paired:" + def.name;
hy.change.value = "maxSimulShot の上限を 4 から 6 に上げる";
bindHypothesisBuilder(root, s, d);
hy.fact.fire("change");
hy.metric.fire("change");
hy.judge.fire("change");
console.log("TEXT<<<" + out.textContent + ">>>");
console.log("CMD<<<" + btn.dataset.cmd + ">>>");
"""


def card_phrase_appears(text: str) -> bool:
    cards = serve.collect_session()["evidence"]
    card = next((c for c in cards if c.get("id") == "constraints"), None)
    if not card:
        return True
    return card["phrase"][:20] in text


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js がない")
def test_hypothesis_builder_generates_command_in_browser_logic(tmp_path):
    # 選択 → 文 → hypothesis コマンドが実際に組まれること（Node で実行）
    payload = tmp_path / "summary.json"
    payload.write_text(
        json.dumps(serve.collect_summary(), ensure_ascii=False), encoding="utf-8"
    )
    script = tmp_path / "harness.js"
    script.write_text(HARNESS_JS, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(script), str(INDEX_PATH), str(payload)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    if "SKIP" in proc.stdout:
        pytest.skip("軌跡・独自指標・ペア評価のデータがない")
    text = re.search(r"TEXT<<<(.*?)>>>", proc.stdout, re.S).group(1)
    cmd = re.search(r"CMD<<<(.*?)>>>", proc.stdout, re.S).group(1)
    assert card_phrase_appears(text), text
    data = json.loads(payload.read_text(encoding="utf-8"))
    row = next(m for m in data["custom_metrics"]["rows"] if m["id"] == "launch_count")
    digits = row.get("digits", 2)
    for v in (row["value"], row["target"]):
        if v is not None:
            assert f"{float(v):.{digits}f}" in text, text
    assert "<事実>" not in text and "undefined" not in text and "NaN" not in text
    assert "、、" not in text
    assert cmd.startswith("# 仮説登録 — この行をAIに貼って登録依頼\n"
                          'python analysis/tools/improvement_session.py hypothesis "')
    assert f"--specialist {serve.collect_session()['target']}" in cmd
    assert re.search(r"--source (log|analysis|code|official)$", cmd)


def test_http_endpoints():
    server = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(f"{base}/api/health", timeout=30) as res:
            assert json.loads(res.read()) == {"ok": True}

        with urllib.request.urlopen(f"{base}/api/build", timeout=30) as res:
            build = json.loads(res.read().decode("utf-8"))
        assert len(build["build"]) == 12

        with urllib.request.urlopen(base + "/", timeout=30) as res:
            html = res.read().decode("utf-8")
            assert res.status == 200
            assert "air_combatAI_5" in html
        assert f'<meta name="x-build" content="{build["build"]}">' in html

        with urllib.request.urlopen(f"{base}/api/summary", timeout=180) as res:
            payload = json.loads(res.read().decode("utf-8"))
        assert set(payload.keys()) == {
            "generated_at",
            "repo_root",
            "environment",
            "submission",
            "paired",
            "logs",
            "session",
            "git",
            "rules",
            "commands",
            "custom_metrics",
        }
        assert {"target", "submitted", "steps", "evidence"} <= set(payload["session"].keys())

        with urllib.request.urlopen(f"{base}/api/replays", timeout=180) as res:
            replays = json.loads(res.read().decode("utf-8"))
        assert set(replays.keys()) == {"entries", "scanned_skipped", "limit"}

        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(f"{base}/api/replay?log=agent/args.json", timeout=60)
        assert err.value.code == 400

        if replays["entries"]:
            quoted = urllib.parse.quote(replays["entries"][0]["log"])
            with urllib.request.urlopen(f"{base}/api/replay?log={quoted}", timeout=180) as res:
                replay = json.loads(res.read().decode("utf-8"))
            assert replay["frame_count"] == len(replay["frames"])
            assert replay["frame_count"] > 0
    finally:
        server.shutdown()
        server.server_close()


def test_escort_branch_hypothesis_splits_reached_and_unreached():
    assert serve._escort_branch_hypothesis(None) is None
    assert "N-029" in serve._escort_branch_hypothesis(152.7)
    assert "ELIMINATION" in serve._escort_branch_hypothesis(19.6)


def test_wipe_games_picks_zero_alive_only():
    rows = [
        {"color": "Red", "seed": 1, "our_alive": 3.0},
        {"color": "Blue", "seed": 3, "our_alive": 0.0},
        {"color": "Red", "seed": 2},
    ]
    wipes = serve._wipe_games(rows)
    assert len(wipes) == 1
    assert wipes[0]["seed"] == 3
    assert serve._wipe_games([]) == []
    assert serve._wipe_games(None) == []