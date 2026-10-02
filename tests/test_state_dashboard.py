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

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVE_PATH = REPO_ROOT / "tools" / "state_dashboard" / "serve.py"
INDEX_PATH = REPO_ROOT / "tools" / "state_dashboard" / "index.html"

TABS = ["環境", "提出", "評価", "ログ", "改善セッション", "git", "コマンド"]


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


def test_http_endpoints():
    server = ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(f"{base}/api/health", timeout=30) as res:
            assert json.loads(res.read()) == {"ok": True}

        with urllib.request.urlopen(base + "/", timeout=30) as res:
            assert res.status == 200
            assert "air_combatAI_5" in res.read().decode("utf-8")

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
            "commands",
        }
    finally:
        server.shutdown()
        server.server_close()