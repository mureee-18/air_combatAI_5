"""BATTLELOG_FORMAT.md に書いた前提が崩れていないかを検証する回帰テスト.

ログ構造を毎回調べ直さないための仕掛け。形式が変わったらここが落ちるので、
まずこのテストと BATTLELOG_FORMAT.md を更新すること。
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "log_sample.json"
FORMAT_MD = REPO_ROOT / "tools" / "battle_analyzer" / "BATTLELOG_FORMAT.md"

OWN_LEN = 10
ENEMY_ROWS = 5
ENEMY_COLS = 5
THREAT_LEN = 2
ACTION_KEYS = {"turn", "speed", "target"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_format_document_exists():
    assert FORMAT_MD.exists()


def test_top_level_keys():
    d = load(FIXTURE)
    assert set(d.keys()) == {"observations", "actions", "infos"}


def test_observation_shapes():
    d = load(FIXTURE)
    for entry in d["observations"]:
        for payload in entry["data"].values():
            assert set(payload.keys()) == {"own", "enemy", "threat"}
            assert len(payload["own"]) == OWN_LEN
            assert len(payload["enemy"]) == ENEMY_ROWS
            for row in payload["enemy"]:
                assert len(row) == ENEMY_COLS
            assert len(payload["threat"]) == THREAT_LEN


def test_action_keys():
    d = load(FIXTURE)
    for entry in d["actions"]:
        for payload in entry["data"].values():
            assert set(payload.keys()) == ACTION_KEYS


def test_observations_and_actions_are_paired():
    d = load(FIXTURE)
    assert len(d["observations"]) == len(d["actions"])
    for obs, act in zip(d["observations"], d["actions"]):
        assert obs["ptime"] == act["ptime"]


@pytest.mark.skipif(
    not list(REPO_ROOT.glob("workspace/results*/**/log_*.json")),
    reason="実ログが無い環境ではスキップ",
)
def test_real_log_matches_documented_shapes():
    logs = sorted(REPO_ROOT.glob("workspace/results*/**/log_*.json"))
    own_payloads = []
    action_dicts = []
    for log_path in logs:
        d = load(log_path)
        own_payloads.extend(
            p
            for entry in d["observations"]
            for p in entry["data"].values()
            if isinstance(p, dict) and isinstance(p.get("own"), list) and isinstance(p.get("enemy"), list)
        )
        action_dicts.extend(p for entry in d["actions"] for p in entry["data"].values() if isinstance(p, dict))
        if own_payloads:
            break

    if not own_payloads:
        pytest.skip("自作 Agent 形式のログではありません（baseline / BenchMark のログなど）")

    for payload in own_payloads:
        assert set(payload.keys()) == {"own", "enemy", "threat"}
        assert len(payload["own"]) in (8, OWN_LEN)
        assert len(payload["enemy"]) == ENEMY_ROWS
        for row in payload["enemy"]:
            assert len(row) == ENEMY_COLS
        assert len(payload["threat"]) == THREAT_LEN

    for payload in action_dicts:
        assert set(payload.keys()) == ACTION_KEYS
