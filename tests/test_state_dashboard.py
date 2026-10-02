"""開発状況ダッシュボードの回帰テスト.

`--once` / HTTP エンドポイントが壊れていないこと、
そして収集 JSON のキー構成が変わっていないことを確認する。
"""

import importlib.util
import json
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

TABS = ["環境", "提出", "評価", "ログ", "改善セッション", "git", "コマンド", "ルール", "軌跡"]


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
    assert "enemy_xy" not in html  # 座標復元は Python 側。JS で二重実装しない


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
            "frames",
            "events",
            "result",
        }
        assert len(payload["frames"]) == payload["frame_count"]
        assert payload["slots"]
        for frame in payload["frames"]:
            assert set(frame.keys()) == {"t", "ptime", "own", "enemy", "threat", "action", "events"}
        return
    pytest.skip("自作 Agent 形式のログがありません")


def test_collect_environment_shape():
    env = serve.collect_environment()
    assert set(env.keys()) == {"host", "docker", "workspace", "deploy_drift", "repo_specialist"}
    assert set(env["workspace"].keys()) >= {"exists", "simulator_ready", "size_h", "agents"}
    assert isinstance(env["docker"]["containers"], list)


def test_collect_paired_shape():
    paired = serve.collect_paired()
    assert set(paired.keys()) == {"files", "best"}
    for entry in paired["files"]:
        assert set(entry.keys()) == {"name", "mtime", "metrics", "rows"}


def test_collect_git_shape():
    git = serve.collect_git()
    assert set(git.keys()) == {"branch", "head", "remote", "upstream", "ahead_behind", "dirty", "recent"}
    assert set(git["dirty"].keys()) == {"modified", "untracked", "other"}


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
        }

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