import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("eval_pool", REPO_ROOT / "scripts" / "eval_pool.py")
ep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ep)


def test_parse_seeds_ranges_and_lists():
    assert ep.parse_seeds("1-5") == [1, 2, 3, 4, 5]
    assert ep.parse_seeds("7,1-3,3") == [1, 2, 3, 7]
    with pytest.raises(ValueError):
        ep.parse_seeds(",")


def test_shards_cover_every_game_once():
    jobs = ep.plan_jobs(["BenchMark", "O_RUSH"], ep.parse_seeds("1-20"), ["Red", "Blue"])
    assert len(jobs) == 80
    for n in (2, 3, 7):
        parts = [ep.plan_jobs(["BenchMark", "O_RUSH"], ep.parse_seeds("1-20"), ["Red", "Blue"], (i, n))
                 for i in range(1, n + 1)]
        merged = [j for part in parts for j in part]
        assert sorted(merged) == sorted(jobs)
        assert all(part for part in parts)
    with pytest.raises(ValueError):
        ep.parse_shard("3/2")


def test_resume_plays_only_missing_games(tmp_path):
    jobs = ep.plan_jobs(["O_RUSH"], [1, 2], ["Red", "Blue"])
    games = tmp_path / "games"
    games.mkdir()
    (games / "O_RUSH_Red_1.json").write_text("{}", encoding="utf-8")
    (games / ".O_RUSH_Red_2.json.x.tmp").write_text("", encoding="utf-8")
    assert ep.pending_jobs(jobs, tmp_path) == [("O_RUSH", 2, "Red"), ("O_RUSH", 1, "Blue"), ("O_RUSH", 2, "Blue")]


def test_module_name_is_an_identifier():
    name = ep.module_name("20261023T013000Z-agent-7f3-acc30b6-k3f9qz")
    assert name.isidentifier() and name.startswith("r_")


def test_pool_names_known_opponents():
    pool = ep.load_pool()
    assert ep.resolve_opponents("pool", pool) == pool["pool"]
    for spec in pool["opponents"].values():
        if spec["kind"] == "repo":
            assert (REPO_ROOT / spec["args"]).exists() and len(spec["commit"]) == 40
        elif spec.get("config"):
            assert json.loads((REPO_ROOT / spec["config"]).read_text(encoding="utf-8"))
    with pytest.raises(SystemExit):
        ep.resolve_opponents("NOPE", pool)


def test_any_worker_count_is_accepted(capsys):
    assert ep.main(["--preset", "hybrid_v6", "--opponents", "O_RUSH", "--seeds", "1-20", "--workers", "1000",
                    "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "40 games, workers=1000" in out


def test_main_writes_rows_through_the_store(tmp_path, monkeypatch):
    sim = tmp_path / "sim"
    (sim / "src").mkdir(parents=True)
    (sim / "src" / "fight.py").write_text("", encoding="utf-8")
    (sim / "Agents" / "BenchMark").mkdir(parents=True)
    (sim / "Agents" / "BenchMark" / "args.json").write_text("{}", encoding="utf-8")

    def fake_run_one(sim_dir, base, job, log_dir):
        assert (sim_dir / base / "cand" / "args.json").exists()
        opponent, seed, color = job
        return {"opponent": opponent, "seed": seed, "color": color, "result": "win", "score": 0.6,
                "endReason": "ELIMINATION", "step_count": 1, "our_alive": 4.0, "enemy_alive": 0.0, "our_launched": 1,
                "our_hits": 1, "enemy_launched": 0, "enemy_hits": 0, "error": False}

    monkeypatch.setattr(ep, "run_one", fake_run_one)
    runs = tmp_path / "runs"
    code = ep.main(["--preset", "hybrid_v6", "--opponents", "BenchMark", "--seeds", "1-3", "--workers", "4",
                    "--sim-dir", str(sim), "--runs-dir", str(runs), "--worker", "test"])
    assert code == 0
    (run_dir,) = runs.iterdir()
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete" and manifest["n_games"] == 6
    assert manifest["candidate"]["name"] == "hybrid_v6" and manifest["candidate"]["specialist"] == "hybrid"
    assert list((sim / "Agents" / "_runs").iterdir()) == []
