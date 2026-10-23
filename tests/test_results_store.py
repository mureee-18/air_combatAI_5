import importlib.util
import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("results_store", REPO_ROOT / "scripts" / "results_store.py")
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)

CANDIDATE = {"name": "hybrid_v6", "specialist": "hybrid", "args": {"specialist": "hybrid"},
             "args_sha256": "x", "code_sha256": "y"}
OPPONENTS = [{"name": "BenchMark", "commit": None, "args_sha256": None, "code_sha256": None}]
PROTOCOL = {"seeds": [1, 2], "colors": ["Red", "Blue"], "youth": True, "make_log": True}


def _row(seed, color="Red", opponent="BenchMark", **extra):
    row = {"opponent": opponent, "seed": seed, "color": color, "result": "win", "score": 0.7,
           "endReason": "ELIMINATION",
           "step_count": 900, "our_alive": 3.0, "enemy_alive": 0.0, "our_launched": 10, "our_hits": 4,
           "enemy_launched": 8, "enemy_hits": 1, "enemy_escort_killed": True, "our_escort_killed": False,
           "error": False}
    row.update(extra)
    return row


def _run(tmp_path, **kw):
    return rs.start_run("tester", CANDIDATE, OPPONENTS, PROTOCOL, runs_dir=tmp_path, **kw)


def test_run_ids_are_unique_and_well_formed():
    ids = {rs.new_run_id("agent 7/x", "abc1234def") for _ in range(10000)}
    assert len(ids) == 10000
    sample = next(iter(ids))
    stamp, worker, sha, rand = sample.split("-")
    assert stamp.endswith("Z") and worker == "agent_7_x" and sha == "abc1234" and len(rand) == 6


def test_write_game_is_atomic_and_leaves_no_temp_file(tmp_path, monkeypatch):
    run_dir = _run(tmp_path)
    rs.write_game(run_dir, _row(1))

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        rs.write_game(run_dir, _row(2))
    files = sorted(p.name for p in (run_dir / "games").iterdir())
    assert files == ["BenchMark_Red_1.json"]
    assert rs.validate_run(run_dir) == []


def test_finish_run_joins_games_and_marks_complete(tmp_path):
    run_dir = _run(tmp_path)
    for seed in (2, 1):
        for color in ("Red", "Blue"):
            rs.write_game(run_dir, _row(seed, color))
    manifest = rs.finish_run(run_dir)
    assert manifest["status"] == "complete" and manifest["n_games"] == 4
    lines = (run_dir / "games.jsonl").read_text(encoding="utf-8").splitlines()
    assert [(json.loads(x)["color"], json.loads(x)["seed"]) for x in lines] == [
        ("Blue", 1), ("Blue", 2), ("Red", 1), ("Red", 2)]
    assert not (run_dir / "games").exists()
    assert rs.validate(tmp_path) == []


def test_complete_run_refuses_rewrite(tmp_path):
    run_dir = _run(tmp_path)
    rs.write_game(run_dir, _row(1))
    rs.finish_run(run_dir)
    with pytest.raises(rs.CompleteRunError):
        rs.write_game(run_dir, _row(2))
    with pytest.raises(rs.CompleteRunError):
        rs.finish_run(run_dir)


def test_validate_flags_edit_of_complete_run(tmp_path):
    run_dir = _run(tmp_path)
    rs.write_game(run_dir, _row(1))
    rs.finish_run(run_dir)
    path = run_dir / "games.jsonl"
    path.write_text(path.read_text(encoding="utf-8").replace('"win"', '"loss"'), encoding="utf-8")
    errors = rs.validate(tmp_path)
    assert any("edited after completion" in e for e in errors)


def test_validate_names_bad_field_and_file(tmp_path):
    run_dir = _run(tmp_path)
    path = rs.write_game(run_dir, _row(1, color="Green"))
    errors = rs.validate_run(run_dir)
    assert errors and str(path) in errors[0] and "game.color" in errors[0]
    manifest = rs.read_manifest(run_dir)
    manifest["status"] = "done"
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert any("manifest.status" in e for e in rs.validate_run(run_dir))


def test_import_legacy_makes_one_run_per_pairing(tmp_path):
    pool = tmp_path / "pool"
    pair = pool / "V6_vs_O_RUSH"
    pair.mkdir(parents=True)
    for seed in range(1, 21):
        for color in ("Red", "Blue"):
            raw = _row(seed, color, module="Agents/H_V6", track={}, death_step={})
            raw.pop("opponent")
            (pair / f"{color}_{seed}.json").write_text(json.dumps(raw), encoding="utf-8")
            (pair / f"{color}_{seed}_log.json").write_text("{}", encoding="utf-8")
    runs = tmp_path / "runs"
    ids = rs.import_legacy(pool, runs, {"V6": "hybrid_v6"})
    assert len(ids) == 1
    manifest = rs.read_manifest(runs / ids[0])
    assert manifest["imported"] is True and manifest["status"] == "complete" and manifest["n_games"] == 40
    assert manifest["candidate"]["name"] == "hybrid_v6" and manifest["opponents"][0]["name"] == "O_RUSH"
    assert rs.validate(runs) == []


def test_repository_results_are_valid():
    assert rs.validate(REPO_ROOT / "results") == []
