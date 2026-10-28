"""開発状況ダッシュボードの回帰テスト.

`--once` / HTTP エンドポイントが壊れていないこと、
そして収集 JSON のキー構成が変わっていないことを確認する。
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
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


def dashboard_source() -> str:
    """index.html 本体と、分割された js/*.js を元の読み込み順で連結して返す（コード分離後の回帰検査用）。"""
    import re
    html = INDEX_PATH.read_text(encoding="utf-8")
    parts = [html]
    js_dir = INDEX_PATH.parent / "js"
    ordered = []
    for name in re.findall(r'<script src="js/([^"]+)"', html):
        path = js_dir / name
        if path.is_file():
            ordered.append(path)
    if not ordered and js_dir.is_dir():
        ordered = sorted(js_dir.glob("*.js"))
    for path in ordered:
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)

TABS = ["環境", "提出", "エージェント", "観測・判断・行動", "評価", "ログ", "仮説登録",
        "改善サイクル", "git", "コマンド", "コンペルール", "自機視点", "戦場俯瞰"]


def load_serve():
    spec = importlib.util.spec_from_file_location("state_dashboard_serve", SERVE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _decision_module():
    path = REPO_ROOT / "tools" / "battle_analyzer"
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    import decision_trace
    importlib.reload(decision_trace)
    for name in ("observation", "decision", "action"):
        importlib.reload(getattr(decision_trace, name))
    return decision_trace


serve = load_serve()


def test_index_has_all_tabs():
    html = dashboard_source()
    for tab in TABS:
        assert f'"{tab}"' in html or f">{tab}<" in html
    assert 'id="auto"' in html
    assert "api/summary" in html


def test_index_has_trajectory_replay_wiring():
    html = dashboard_source()
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
    html = dashboard_source()
    assert 'id="tab-battle"' in html
    for hook in ["battle-canvas", "battle-seek", "battle-play", "drawBattle", "openBattle",
                 "buildBattleShell", "renderBattleLegend", "drawBattleIcon"]:
        assert hook in html
    for hook in ["frame.teams", "戦場俯瞰", "buildBattleShell"]:
        assert hook in html
    assert 'side === "own"' in html


def test_index_eval_goal_board_replaces_detail_rows():
    html = dashboard_source()
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


def test_session_has_open_work():
    session = serve.collect_session()
    assert isinstance(session.get("open_work"), dict)
    assert isinstance(session["open_work"].get("unverified"), list)
    assert isinstance(session["open_work"].get("next_steps"), list)


def test_pending_excludes_validated_and_recorded():
    """検証タブの pending は validate か record で紐付いた仮説を除外する（唯一の正）."""
    state = {
        "hypotheses": [{"id": "N-1"}, {"id": "N-2"}, {"id": "N-3"}],
        "cycles": [{"kind": "validate", "hypothesis": "N-1"}],
        "records": [{"hypothesis": "N-2"}],
    }
    assert serve._pending_hypothesis_ids(state) == ["N-3"]


def test_pending_key_in_session_payload():
    session = serve.collect_session()
    assert isinstance(session.get("pending"), list)
    ids = {h["id"] for h in session["hypotheses"]}
    assert set(session["pending"]) <= ids


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
    if len(with_metrics) < 2:
        pytest.skip("ペア評価データが無い環境ではスキップ")
    session = serve.collect_session()
    target = session.get("target") or "default"
    cards = session["evidence"]
    card = next((c for c in cards if c["id"] == "paired"), None)
    assert card is not None
    labels = [row["label"] for row in card["evidence"]]
    assert any(target in label for label in labels)
    assert any("baseline" in label for label in labels)


def test_session_steps_mark_hypothesis_current_when_empty():
    session = serve.collect_session()
    if not session["sessions"]:
        pytest.skip("セッション記録が無い環境ではスキップ")
    current = session["sessions"][-1]
    steps = {s["key"]: s for s in session["steps"]}
    if not current["hypotheses"]:
        assert steps["hypothesis"]["state"] in {"current", "done"}


def test_index_renders_session_steps_and_fact_cards():
    html = dashboard_source()
    for hook in ["renderSteps", "renderFact", "STEP_STATE_LABEL", "bindCopy", "attr"]:
        assert hook in html
    assert "fact-grid" in html and "hyp-box" in html
    # コマンド内の " が data-cmd を壊さないこと
    assert 'data-cmd="${attr(' in html
    assert 'data-cmd="${esc(' not in html


def test_index_has_agents_tab_showing_package_contents():
    html = dashboard_source()
    # 「エージェント」タブがystsAccessibleで、提出パッケージの中身を表示する
    assert 'id="tab-agents"' in html
    assert '<div id="agents"></div>' in html
    assert '["agents", "エージェント"]' in html
    start = html.index("function renderAgents")
    end = html.index("function renderEval")
    block = html[start:end]
    # Agent クラス本体・Specialist・プリセット・アイデア・args.json を並べる
    assert "Agent クラス本体" in block
    assert "Specialist（方針）" in block
    assert "プリセット" in block
    assert "args.json" in block
    assert "d.agents" in block
    # 提出 zip の中身を出す（実体が「提出パッケージ」）
    assert "提出 zip の中身" in html
    assert "s.zip_files" in html
    assert "提出物のルートファイル" in html
    # agent/ ソースの見出しは実態に合わせる（zip 10 ファイル、main.py は入らない）
    assert "agent/ 配下のソース" in html
    assert "提出パッケージのファイル（agent/）" not in html
    # ファイル一覧はディレクトリ構造のツリーで見やすくする
    assert "agentTreeHtml" in block
    # 描画パイプラインから呼ばれる
    assert "renderAgents(data)" in html


def test_index_has_decision_tab_splitting_observation_decision_action():
    html = dashboard_source()
    assert 'id="tab-decision"' in html
    assert '<div id="decision"></div>' in html
    assert '["decision", "観測・判断・行動"]' in html
    # 観測・判断・行動 の描画は独立した関数（1つの関数に埋め込まない）
    for fn in ("renderObservationHtml", "renderDecisionHtml", "renderActionHtml", "renderAircraft"):
        assert f"function {fn}(" in html, f"{fn} が独立していない"

    def fn_block(name):
        s = html.index(f"function {name}(")
        e = html.index("\nfunction ", s + 10)
        return html[s:e]

    # 観測の中 Villain 入れない: 観測だけ应是ログの値
    assert "can_fire" not in fn_block("renderObservationHtml")
    assert "off_nose" not in fn_block("renderObservationHtml")
    # 行動の中は判定しない
    assert "can_fire" not in fn_block("renderActionHtml")
    assert "off_nose" not in fn_block("renderActionHtml")
    # 判断だけが撃てるかの判定を持つ
    assert "can_fire" in fn_block("renderDecisionHtml")
    # renderDecision は機体ごとの描画を renderAircraft に委譲する
    rdec = fn_block("renderDecision")
    assert "renderAircraft(ac)" in rdec
    for label in ("観測: 自機", "判断: 標的", "行動: 機首"):
        assert label not in rdec, f"{label} の描画が renderDecision に残っている"
    # ログ選択とフレーム移動
    assert "/api/decision" in rdec
    assert "/api/replays" in rdec
    assert "renderDecision(data)" in html


def test_decision_trace_is_split_into_separate_modules():
    pkg = REPO_ROOT / "tools" / "battle_analyzer" / "decision_trace"
    # 観測・判断・行動 はそれぞれ別ファイル
    assert pkg.is_dir(), "decision_trace はディレクトリ（パッケージ）であるべき"
    for name in ("observation.py", "decision.py", "action.py", "__init__.py"):
        assert (pkg / name).exists(), f"{name} が無い"
    # 旧 singularity ファイルは残さない
    assert not (pkg.parent / "decision_trace.py").exists(), "単一ファイル版が残っている"
    # 各モジュールは自分の責務だけを持つ
    obs = (pkg / "observation.py").read_text(encoding="utf-8")
    dec = (pkg / "decision.py").read_text(encoding="utf-8")
    act = (pkg / "action.py").read_text(encoding="utf-8")
    assert "def read_own" in obs and "def read_enemies" in obs and "def read_threat" in obs
    assert "def read_turn" in act and "def read_speed" in act and "def read_target" in act
    assert "can_fire" in dec and "off_nose" in dec
    # 行動の判定（撃てるか）は判断側、観測は派生しない
    assert "can_fire" not in obs


def test_decision_trace_splits_observation_decision_action():
    trace = _decision_module()
    logs = sorted(REPO_ROOT.glob("workspace/results*/**/log_*.json"))
    if not logs:
        pytest.skip("実ログが無い環境ではスキップ")
    cfg = json.loads((REPO_ROOT / "agent" / "config.json").read_text(encoding="utf-8"))
    out = trace.build_frame(logs[0], 0, cfg)
    assert out["frames"] >= 1
    assert out["aircraft"], "機体の情報が無い"
    ac = out["aircraft"][0]
    # 観測: 自機・敵・脅威（ログが持つ値）
    assert set(ac["observation"]) == {"own", "enemies", "threat"}
    assert "ammo" in ac["observation"]["own"]
    # 判断: 標的・照準・機首ずれ・撃てるか
    assert set(ac["decision"]) >= {"target", "aim", "off_nose", "can_fire"}
    # 行動: turn / speed / target を項目ごとに
    assert set(ac["action"]) == {"turn", "speed", "target"}
    assert set(ac["action"]["turn"]) == {"index", "value", "unit", "table"}
    assert ac["action"]["turn"]["table"] == "turnTable"
    assert ac["action"]["speed"]["table"] == "speedTable"


def test_index_has_verify_tab_with_hypothesis_selector():
    html = dashboard_source()
    # 「検証」タブが追加されている
    assert 'id="tab-verify"' in html
    assert '<div id="verify"></div>' in html
    assert '"verify", "検証"' in html
    # renderVerify が仮説セレクタを持ち、選択 id を --hypothesis として差し込む
    start = html.index("function renderVerify")
    end = html.index("const GIT_INSTRUCTIONS")
    block = html[start:end]
    assert 'id="verify-hyp"' in block
    # 選択した仮説 id を --hypothesis として各コマンドに差し込む
    assert "--hypothesis ${sel}" in block
    assert "--hypothesis" in html
    # 検証フローは 1 行に統合（verify_cycle → validate → record を && で連結）。
    # コピーボタン付き(cmdRow) は 1 つ
    steps = (
        "① 一括検証",
    )
    for step in steps:
        assert step in block, f"検証タブに {step} が無い"
    assert block.count("cmdRow(") >= 1, "コピーボタン（cmdRow）が無い"
    assert 'INTENT_IMPL' in block, "①実装行にコピーボタンの指示（INTENT_IMPL）が無い"
    assert "verify_cycle.py" in block
    assert "improvement_session.py validate" in block
    assert "improvement_session.py record" in block
    # 検証タブにはカード（対象 specialist / 検証する仮説 / 現在地）を出さない
    assert "cards(" not in block
    assert "現在地" not in block
    # 未検証かの判定は serve.py の pending（唯一の正）を使い、フロントで再計算しない
    assert "new Set(s.pending" in block
    assert "hyps.filter(h => pendIds.has(h.id))" in block
    assert "verified" not in block
    assert "検証済み" in block  # 全件検証済みのときのメッセージ
    assert 'bindCopy(document.getElementById("verify"))' in block


def test_index_hypothesis_tab_hides_registered_fact_cards():
    # 「仮説登録」タブは登録済み（過去の検証）を材料にした事実カードを出さない
    html = dashboard_source()
    start = html.index("function renderHypothesis")
    end = html.index("function renderSession")
    block = html[start:end]
    assert 'c.id !== "paired"' in block
    assert "renderFactGroups(facts)" in block
    assert "s.evidence.map(renderFact)" not in block


def test_handled_materials_sink_and_clear():
    html = dashboard_source()
    assert "opencode-handled-materials" not in html
    assert "data-handled-key" not in html
    assert "sortByHandled" in html
    # new fact card には handled クラスが付与されない（badge non-display）
    # CSS .fact.handled セレクタは stylesheet に残るため、HTML class 属性のみチェック
    assert 'class="handled"' not in html
    assert "renderFactGroups" in html
    assert "fact-group-title" in html
    assert "fact.fresh" in html
    assert "未処理（" in html
    assert "mark-handled" not in html
    assert 'id="hypho-copy"' in html
    assert "border-style: dashed" in html
    assert "INTENT_REVIEW" in html
    assert "# 文書レビュー" in html
    assert "copyIntent" in html
    assert "INTENT_REOPEN" in html
    # "見直しを依頼" は新規fact cardでは材料ボタンが優先されます
    assert "仮説の材料" in html
    assert "前提（参照用" in html
    assert "/api/build" in html
    assert "dash-keep-tab" in html
    assert "visibilitychange" in html
    assert "古い可能性あり" in html
    assert ".meta.warn" in html
    assert "recordedPhrases" in html
    assert "recorded_materials" in html
    assert "reset-handled" not in html
    assert "handledThreshold" not in html
    assert "agent_mtime" not in html


def test_session_exposes_recorded_materials():
    session = serve.collect_session()
    assert isinstance(session.get("recorded_materials"), list)


def test_index_improvement_cycle_tab_unchanged():
    # 「改善サイクル」タブ（renderSteps）は読み取り専用のまま。コマンドは描画しない
    html = dashboard_source()
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
    html = dashboard_source()
    for key in ("fact", "cause", "change", "variable", "metric", "judge", "source"):
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
const path = require("path");
const html = fs.readFileSync(process.argv[2], "utf-8");
const baseDir = path.dirname(process.argv[2]);
const external = [...html.matchAll(/<script src="js\/([^"]+)"/g)]
  .map(m => fs.readFileSync(path.join(baseDir, "js", m[1]), "utf-8"));
const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const js = external.concat(inline).join("\n");
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
["fact","cause","change","variable","metric","judge","source",
 "fact-text","cause-text","variable-text","metric-text","judge-text"].forEach(n => { hy[n] = stubEl(); });
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
hy.variable.value = "maxSimulShot";
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
    assert "--variable maxSimulShot" in cmd
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
            "agents",
        }
        assert {"target", "submitted", "steps", "evidence"} <= set(payload["session"].keys())
        # エージェント（提出パッケージ）の中身
        agents = payload["agents"]
        assert agents["specialist"] == (agents["args"] or {}).get("specialist")
        assert agents["files"], "agent/ 配下のファイルが列挙されていない"
        assert any(f["path"] == "strategy/agents/escort_hunter.py" for f in agents["files"])
        assert any(sp["name"] == "default" and sp["active"] for sp in agents["specialists"])
        assert all(f["lines"] > 0 for f in agents["files"])

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


def test_ammo_reserve_card_redirects_from_conservation():
    cards = serve._metric_cards({"ammo_reserve": 0.0}, None, None, "default", [])
    card = next((c for c in cards if c.get("id") == "metric:ammo_reserve"), None)
    assert card is not None
    assert "N-028" in (card.get("hypothesis") or "")


def test_threat_card_closed():
    # MWS 軸は agent 非制御のため閉鎖済み（O-083）。カードは生成されない。
    traj = {"warn_frames": {"1": 300, "2": 30, "3": 10, "4": 5}}
    cards = serve._metric_cards(traj, None, None, "default", [])
    assert next((c for c in cards if c.get("id") == "metric:threat_frames"), None) is None


def test_scope_compare_rows_prefers_target_and_baseline():
    rows = [
        {"name": "def_fr90", "file": "def_fr90.json", "metrics": {"avg_score": 0.229}},
        {"name": "default", "file": "default.json", "metrics": {"avg_score": 0.5}},
        {"name": "baseline", "file": "baseline.json", "metrics": {"avg_score": 0.5}},
    ]
    scoped = serve._scope_compare_rows(rows, "default")
    assert [r["name"] for r in scoped] == ["default", "baseline"]
    assert serve._scope_compare_rows(rows, "missing") == []
    assert serve._scope_compare_rows([rows[0]], "default") == []


def test_min_dist_and_launch_count_cards_redirect():
    cards = serve._metric_cards({"min_dist": {"1": 31.0}, "launch_count": 8}, None, None, "default", [])
    dist = next((c for c in cards if c.get("id") == "metric:min_dist_km"), None)
    assert dist is not None
    assert "N-017" in (dist.get("hypothesis") or "")
    launches = next((c for c in cards if c.get("id") == "metric:launch_count"), None)
    assert launches is not None
    assert "N-018" in (launches.get("hypothesis") or "")


def test_fire_orders_card_redirects_from_volume():
    stats = {"agents": [{"fire_orders": 634}]}
    cards = serve._metric_cards({}, stats, None, "default", [])
    orders = next((c for c in cards if c.get("id") == "metric:fire_orders"), None)
    assert orders is not None
    assert "N-018" in (orders.get("hypothesis") or "")


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


def test_tested_axes_parsed_from_policy_table():
    # policy の「検証済みの変数軸」表から変数名を読めていること
    tested = serve._tested_axes()
    assert {"fireRangeKm", "maxSimulShot", "breakRangeKm",
            "beamRangeKm", "targetMode", "evadeCrankDeg"} <= tested
    # 表の見出し・区切り行を変数名として拾わない
    assert "変数" not in tested
    assert "" not in tested


def test_axis_cards_render_untested_axis(monkeypatch):
    # 閉鎖軸が無い（=全部未試験）状態で、軸カードが正しい形で出ること
    monkeypatch.setattr(serve, "_tested_axes", lambda: set())
    cards = serve._axis_cards()
    assert cards, "未試験軸があるならカードを出す"
    card = next(c for c in cards if c["id"] == "axis:marginKm")
    assert card["kind"] == "observation"
    assert card["source"] == "code"
    assert "marginKm" in card["title"]
    assert card["phrase"] and len(card["phrase"]) <= 120
    assert card["hypothesis"]
    assert card["evidence"] and all(row["value"] is not None for row in card["evidence"])


def test_axis_cards_exclude_tested_axes():
    # policy の表に載った軸は必ずカードから除外される（足せば自動で消える）
    tested = serve._tested_axes()
    cards = serve._axis_cards()
    ids = {c["id"] for c in cards}
    for card in cards:
        var = card["id"].split(":", 1)[1]
        assert var not in tested
        assert card["kind"] == "observation"
        assert card["source"] == "code"
    assert "axis:fireRangeKm" not in ids


def test_collect_directions_shape():
    # 数値ノブが全滅しても材料が残るよう、設計の方向を 1 件以上返す
    d = serve.collect_directions()
    assert isinstance(d, dict)
    items = d["items"]
    assert items, "設計の方向が 1 件も無い"
    for it in items:
        assert it["id"]
        assert it["title"]
        assert it["summary"]
        assert isinstance(it["why"], list) and it["why"]
        assert isinstance(it["steps"], list) and it["steps"]
        assert isinstance(it["records"], list)
        assert isinstance(it["paths"], list)
