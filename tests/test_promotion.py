import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_promotion", REPO_ROOT / "scripts" / "check_promotion.py")
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)

NEW = {"specialist": "hybrid_v6", "k": 1}
CUR = {"specialist": "default"}
POOL = ["A", "B"]


def _run(run_id, args, scores, status="complete", seeds=cp.SEEDS):
    """scores: 相手 -> score（全 seed・色で同じ）か、(相手, seed, 色) -> score の上書き dict。"""
    rows = []
    for o in POOL:
        for s in seeds:
            for c in cp.COLORS:
                score = scores.get((o, s, c), scores.get(o, 0.5))
                rows.append({"opponent": o, "seed": s, "color": c, "score": score})
    manifest = {"run_id": run_id, "status": status, "finished_at": "2026-10-23T00:00:00Z",
                "candidate": {"name": run_id, "args": args}}
    return manifest, rows


def test_missing_run_fails():
    ok, lines = cp.verdict([_run("cur", CUR, {})], NEW, CUR, POOL)
    assert not ok
    assert any("FAIL new agent/args.json" in line and "none" in line for line in lines)


def test_incomplete_or_other_args_run_does_not_count():
    runs = [_run("new", NEW, {"A": 0.9, "B": 0.9}, status="running"),
            _run("other", {**NEW, "k": 2}, {"A": 0.9, "B": 0.9}), _run("cur", CUR, {})]
    ok, lines = cp.verdict(runs, NEW, CUR, POOL)
    assert not ok
    assert any(line.startswith("FAIL new agent/args.json") for line in lines)


def test_partial_coverage_fails():
    manifest, rows = _run("new", NEW, {"A": 0.9, "B": 0.9})
    ok, lines = cp.verdict([(manifest, rows[:-1]), _run("cur", CUR, {})], NEW, CUR, POOL)
    assert not ok
    assert any("miss 1 of 80 games" in line for line in lines)


def test_lower_pool_min_fails():
    runs = [_run("new", NEW, {"A": 1.0, "B": 0.4}), _run("cur", CUR, {"A": 0.5, "B": 0.5})]
    ok, lines = cp.verdict(runs, NEW, CUR, POOL)
    assert not ok
    assert any(line.startswith("FAIL pool min 0.4000 < current 0.5000") for line in lines)


def test_paired_gain_equal_to_se_fails():
    seeds = list(range(1, 5))  # 2相手 × 4 seed × 2色 = 16 組。1組だけ +0.5 なら差と SE がちょうど等しい
    runs = [_run("new", NEW, {("A", 1, "Red"): 1.0}, seeds=seeds), _run("cur", CUR, {}, seeds=seeds)]
    ok, lines = cp.verdict(runs, NEW, CUR, POOL, seeds=seeds)
    assert not ok
    assert any(line.startswith("FAIL paired pool diff +0.0312 is not larger than its SE 0.03125") for line in lines)


def test_passing_promotion():
    new_scores = {(o, s, c): 0.6 + 0.01 * (s % 3) for o in POOL for s in cp.SEEDS for c in cp.COLORS}
    runs = [_run("new", NEW, new_scores), _run("cur", CUR, {"A": 0.5, "B": 0.55})]
    ok, lines = cp.verdict(runs, NEW, CUR, POOL)
    assert ok, lines
    assert any(line.startswith("ok   paired pool diff") for line in lines)
