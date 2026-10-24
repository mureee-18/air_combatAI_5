import importlib.util
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("results_report", REPO_ROOT / "scripts" / "results_report.py")
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)


def _run(root, run_id, name, rows, status="complete", finished="2026-10-23T00:00:00Z"):
    d = root / "runs" / run_id
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"run_id": run_id, "status": status, "finished_at": finished,
                                                 "candidate": {"name": name}}), encoding="utf-8")
    (d / "games.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _row(opp, seed, color, score, result=None):
    result = result or ("win" if score > 0.5 else "loss" if score < 0.5 else "draw")
    return {"opponent": opp, "seed": seed, "color": color, "score": score, "result": result}


def test_aggregate_cell_mean_se_and_wdl(tmp_path):
    _run(tmp_path, "r1", "a", [_row("X", 1, "Red", 0.8), _row("X", 2, "Red", 0.4), _row("X", 3, "Red", 0.5)])
    report = rr.build(tmp_path, pool=["X"])
    (cand,) = report["candidates"]
    cell = cand["cells"]["X"]
    assert (cell["n"], cell["win"], cell["draw"], cell["loss"]) == (3, 1, 1, 1)
    assert math.isclose(cell["mean"], (0.8 + 0.4 + 0.5) / 3)
    assert math.isclose(cell["se"], math.sqrt(0.0433333333 / 3), rel_tol=1e-6)
    assert cand["pool_mean"] == cell["mean"] and cand["pool_complete"]


def test_paired_difference_uses_only_common_games(tmp_path):
    _run(tmp_path, "a1", "cand", [_row("X", s, "Red", 0.6 + 0.1 * (s % 2)) for s in (1, 2, 3, 4)])
    _run(tmp_path, "b1", "base", [_row("X", s, "Red", 0.5) for s in (1, 2, 3)])
    report = rr.build(tmp_path, pool=["X"], baseline="base")
    cand = next(c for c in report["candidates"] if c["name"] == "cand")
    pd = cand["paired_vs_baseline"]["pool"]
    diffs = [0.2, 0.1, 0.2]
    mean = sum(diffs) / 3
    se = math.sqrt(sum((d - mean) ** 2 for d in diffs) / 2 / 3)
    assert pd["n"] == 3 and math.isclose(pd["diff"], mean) and math.isclose(pd["se"], se)


def test_partial_runs_fill_gaps_and_are_flagged(tmp_path):
    _run(tmp_path, "full", "a", [_row("X", 1, "Red", 0.7)])
    _run(tmp_path, "part", "a", [_row("X", 1, "Red", 0.1), _row("X", 2, "Red", 0.3)], status="running",
         finished=None)
    report = rr.build(tmp_path, pool=["X"])
    cell = report["candidates"][0]["cells"]["X"]
    assert cell["n"] == 2 and math.isclose(cell["mean"], 0.5)
    assert cell["partial"] and not report["candidates"][0]["pool_complete"]
    assert rr.to_text(report).splitlines()[1].endswith("0.500 1/0/1* | 0.500 | 0.500")


def test_latest_complete_run_wins(tmp_path):
    _run(tmp_path, "old", "a", [_row("X", 1, "Red", 0.1)], finished="2026-10-20T00:00:00Z")
    _run(tmp_path, "new", "a", [_row("X", 1, "Red", 0.9)], finished="2026-10-22T00:00:00Z")
    assert rr.build(tmp_path, pool=["X"])["candidates"][0]["cells"]["X"]["mean"] == 0.9


def test_write_outputs(tmp_path):
    _run(tmp_path / "res", "r", "hybrid_v6", [_row("O_RUSH", 1, "Red", 0.6)])
    report = rr.build(tmp_path / "res", pool=["O_RUSH"])
    rr.write(report, tmp_path / "out")
    assert json.loads((tmp_path / "out" / "leaderboard.json").read_text(encoding="utf-8"))["candidates"]
    dash = json.loads((tmp_path / "out" / "dashboard.json").read_text(encoding="utf-8"))
    assert dash["rows"][0]["name"] == "hybrid_v6"
    assert "hybrid_v6" in (tmp_path / "out" / "index.html").read_text(encoding="utf-8")


def test_repository_store_reproduces_v6_vs_o_rush():
    report = rr.build(REPO_ROOT / "results")
    v6 = next(c for c in report["candidates"] if c["name"] == "hybrid_v6")
    cell = v6["cells"]["O_RUSH"]
    assert (cell["n"], cell["win"], cell["draw"], cell["loss"]) == (40, 21, 0, 19)
    assert round(cell["mean"], 3) == 0.530
