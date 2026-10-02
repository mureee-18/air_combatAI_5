"""開発状況ダッシュボードの回帰テスト.

`--once` / HTTP エンドポイントが壊れていないこと、
そして収集 JSON のキー構成が変わっていないことを確認する。
"""

import importlib.util
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVE_PATH = REPO_ROOT / "tools" / "state_dashboard" / "serve.py"
INDEX_PATH = REPO_ROOT / "tools" / "state_dashboard" / "index.html"

TABS = ["環境", "提出", "評価", "ログ", "改善セッション", "git", "コマンド", "ルール"]


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
    finally:
        server.shutdown()
        server.server_close()