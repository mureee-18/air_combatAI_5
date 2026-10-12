"""発射ギャップ内訳（_fire_gap_stats）と設定鮮度のテスト."""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVE_PATH = REPO_ROOT / "tools" / "state_dashboard" / "serve.py"


def load_serve():
    spec = importlib.util.spec_from_file_location("state_dashboard_serve", SERVE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


serve = load_serve()


def test_gap_counts_requests_blocks_and_noammo():
    frames = [
        {"aim": [{"slot": "1"}, {"slot": "2"}], "shots": [{"slot": "1"}],
         "own": {"1": {"ammo": 6}, "2": {"ammo": 0}}},
        {"aim": [{"slot": "1"}], "shots": [], "own": {"1": {"ammo": 6}}},
    ]
    gap = serve._fire_gap_stats(frames)
    assert gap["requests"] == 3
    assert gap["flight_block"] == 1
    assert gap["no_ammo"] == 1
    assert gap["by_slot"]["1"] == {"req": 2, "flight": 1, "noammo": 0}
    assert gap["by_slot"]["2"] == {"req": 1, "flight": 0, "noammo": 1}


def test_gap_empty_frames():
    assert serve._fire_gap_stats([]) == {
        "requests": 0, "flight_block": 0, "no_ammo": 0, "by_slot": {}}
    assert serve._fire_gap_stats(None) == {
        "requests": 0, "flight_block": 0, "no_ammo": 0, "by_slot": {}}


def test_stranded_counts_only_dead_slots():
    assert serve._stranded_ammo({"1": 0.0, "2": 2.0, "3": 2.0, "4": 2.0}, {"1"}) == 6.0
    assert serve._stranded_ammo({"1": 0.0, "2": 2.0}, {"1", "2"}) == 0.0
    assert serve._stranded_ammo({}, {"1"}) is None
    assert serve._stranded_ammo({"1": 0.0}, set()) == 0.0


def test_agent_newer_than_log_returns_bool_or_none():
    assert serve._agent_newer_than_log(None) is None
    assert serve._agent_newer_than_log("no/such/log.json") is None
    result = serve._agent_newer_than_log("agent/args.json")
    assert result is True or result is False
