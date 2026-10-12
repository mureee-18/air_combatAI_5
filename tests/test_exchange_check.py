"""攻防の交換比率（exchange_check.py）のテスト."""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MOD_PATH = REPO_ROOT / "tools" / "battle_analyzer" / "exchange_check.py"


def load_mod():
    spec = importlib.util.spec_from_file_location("exchange_check", MOD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = load_mod()


def frame(own=(), threat=(), events=()):
    return {
        "own": {s: {} for s in own},
        "threat": [{"slot": s} for s in threat],
        "events": list(events),
    }


def test_onset_counts_rising_edges():
    frames = [frame(own=("1",), threat=())] + [frame(own=("1",), threat=("1",))] * 5
    frames += [frame(own=("1",), threat=())] + [frame(own=("1",), threat=("1",))] * 3
    stats = mod.exchange_stats(frames)
    assert stats["per_slot"]["1"]["onsets"] == 2
    assert stats["per_slot"]["1"]["warn_frames"] == 8


def test_death_detection():
    frames = [frame(own=("1", "2")) for _ in range(10)]
    frames += [frame(own=("1",)) for _ in range(10)]
    stats = mod.exchange_stats(frames)
    assert stats["per_slot"]["1"]["died"] is False
    assert stats["per_slot"]["2"]["died"] is True
    assert stats["our_deaths"] == 1


def test_launches_counted():
    frames = [frame(own=("1",)) for _ in range(5)]
    frames[2]["events"] = [{"kind": "launch"}, {"kind": "detect"}]
    stats = mod.exchange_stats(frames)
    assert stats["our_launches"] == 1


def test_verdict_branches():
    assert "撃ち負け" in mod.verdict({"our_launches": 5, "enemy_onsets": 12, "our_deaths": 0})
    assert "かわし負け" in mod.verdict({"our_launches": 5, "enemy_onsets": 7, "our_deaths": 3})
    assert "静か" in mod.verdict({"our_launches": 0, "enemy_onsets": 0, "our_deaths": 0})
