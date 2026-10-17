"""敵護衛対象機の IRST 識別（agent/strategy/agents/escort_id.py）の回帰テスト.

fixture は実シミュレータ（ASRCAISim1 v1.1.0 ユース部門、BenchMark 相手）で記録した
自機1機分の IRST 方位列（最初の約300秒）と、真値の護衛対象機位置。
"""

import importlib.util
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "irst_escort_sample.json"

_spec = importlib.util.spec_from_file_location("escort_id", ROOT / "agent" / "strategy" / "agents" / "escort_id.py")
escort_id = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(escort_id)


def _run(case, shuffle=False):
    ident = escort_id.EscortIdentifier()
    results = []
    rng = random.Random(0)
    for (t, x, y, irst), truth in zip(case["steps"], case["escort_truth_xy"]):
        irst = [tuple(r) for r in irst]
        if shuffle:
            rng.shuffle(irst)
        est = ident.update(t, x, y, irst)
        results.append((t, est, truth))
    return results


def _cases():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_identifies_escort_without_false_positive():
    for name, case in _cases().items():
        escIds = set(case["escort_irst_ids"])
        results = _run(case)
        decided = [(t, e) for t, e, _ in results if e is not None]
        assert decided, f"{name}: never identified"
        wrong = [t for t, e in decided if e["irstId"] not in escIds]
        assert not wrong, f"{name}: false positives at t={wrong[:5]}"
        first = decided[0][0]
        assert first <= 60.0, f"{name}: first identification too late ({first}s)"


def test_identification_does_not_depend_on_track_order():
    for name, case in _cases().items():
        escIds = set(case["escort_irst_ids"])
        decided = [e for _, e, _ in _run(case, shuffle=True) if e is not None]
        assert decided and all(e["irstId"] in escIds for e in decided), name


def test_position_estimate_is_accurate():
    for name, case in _cases().items():
        errs = sorted(
            math.hypot(e["x"] - tr[0], e["y"] - tr[1])
            for _, e, tr in _run(case) if e is not None and tr is not None
        )
        median = errs[len(errs) // 2]
        assert median < 1.5, f"{name}: median position error {median:.2f} km"


def test_leg_rule_picks_direction_consistent_line():
    # x=115 の辺を -y 方向に 250 m/s で飛ぶ目標を、(-100, 0) から見た方位列
    hist = []
    for t in range(30):
        ty = 50.0 - 0.25 * t
        hist.append((float(t), -100.0, 0.0, math.degrees(math.atan2(ty, 215.0))))
    fit = escort_id.best_leg_fit(hist)
    assert fit["x"] == 115.0
    assert abs(fit["vy"] + 250.0) < 5.0


def test_radar_signature_preferred_and_fighters_rejected():
    assert escort_id.radar_signature(115.0, 30.0, 0.0, -250.0)
    assert not escort_id.radar_signature(100.0, 0.0, -300.0, 0.0)   # 接近中の戦闘機
    assert not escort_id.radar_signature(60.0, 30.0, 0.0, -250.0)   # 速さは同じでも位置が違う
    ident = escort_id.EscortIdentifier()
    est = ident.update(0.0, -100.0, 0.0, [], radar=[(100.0, 0.0, -300.0, 0.0), (125.0, -40.0, 0.0, 250.0)])
    assert est["src"] == 2 and est["x"] == 125.0 and est["y"] == -40.0
    pred = ident.predicted(10.0)
    assert abs(pred["y"] - (-37.5)) < 1e-6
