"""定期ヘルスチェック（tools/ops/healthcheck.py）の回帰テスト.

外部依存（docker / git / ネットワーク）に依存しない純粋関数だけを検証する。
"""

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HEALTHCHECK_PATH = REPO_ROOT / "tools" / "ops" / "healthcheck.py"
CACHE_BUMP_PATH = REPO_ROOT / "tools" / "state_dashboard" / "cache_bump.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def health():
    return load(HEALTHCHECK_PATH, "ops_healthcheck")


@pytest.fixture()
def cache_bump():
    return load(CACHE_BUMP_PATH, "state_dashboard_cache_bump")


@pytest.fixture()
def serve():
    return load(REPO_ROOT / "tools" / "state_dashboard" / "serve.py", "state_dashboard_serve_for_ops")


def test_json_state_detects_broken_and_missing(health, tmp_path, monkeypatch):
    monkeypatch.setattr(health, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(health, "WATCHED_JSON", ["good.json", "broken.json", "missing.json"])
    (tmp_path / "good.json").write_text('{"ok": true}', encoding="utf-8")
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    assert health.json_state() == "json=bad(broken.json:broken,missing.json:missing)"


def test_json_state_ok(health, tmp_path, monkeypatch):
    monkeypatch.setattr(health, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(health, "WATCHED_JSON", ["good.json"])
    (tmp_path / "good.json").write_text("[]", encoding="utf-8")
    assert health.json_state() == "json=ok"


def test_port_open_detects_closed_port(health):
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        closed = sock.getsockname()[1]
    assert health.port_open(closed) is False


def test_disk_state_reports_free_gb(health):
    state = health.disk_state()
    assert state.startswith("disk_free=")
    assert state.endswith("GB")


def test_heartbeat_line_contains_all_checks(health, monkeypatch):
    monkeypatch.setattr(health, "dashboard_state", lambda port, restart=False: "dashboard=8765:down")
    monkeypatch.setattr(health, "docker_state", lambda: "docker=?")
    monkeypatch.setattr(health, "git_state", lambda: "git=master dirty=0")
    result = health.collect(8765)
    line = health.heartbeat_line(result)
    for token in ["dashboard=8765:down", "docker=?", "git=master", "json=", "disk_free="]:
        assert token in line


def test_append_heartbeat_writes_one_line(health, tmp_path, monkeypatch):
    log = tmp_path / "ops" / "heartbeat.log"
    monkeypatch.setattr(health, "HEARTBEAT_LOG", log)
    health.append_heartbeat("line-1")
    health.append_heartbeat("line-2")
    assert log.read_text(encoding="utf-8").splitlines() == ["line-1", "line-2"]


def test_build_id_changes_with_epoch(cache_bump, tmp_path, monkeypatch):
    index = tmp_path / "index.html"
    rules = tmp_path / "rules.json"
    epoch = tmp_path / "epoch.txt"
    index.write_text("<html></html>", encoding="utf-8")
    rules.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cache_bump, "INDEX_HTML", index)
    monkeypatch.setattr(cache_bump, "RULES_JSON", rules)
    monkeypatch.setattr(cache_bump, "EPOCH_FILE", epoch)

    before = cache_bump.build_id()
    epoch.write_text("12345\n", encoding="utf-8")
    after = cache_bump.build_id()
    assert before != after
    assert len(after) == 12
    assert after == json.loads(json.dumps({"build": cache_bump.build_id()}))["build"]


def test_serve_build_id_matches_cache_bump_build_id(serve, cache_bump):
    assert serve.build_id() == cache_bump.build_id()
