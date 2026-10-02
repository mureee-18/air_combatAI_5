"""軌跡復元（tools/battle_analyzer/trajectory.py）の回帰テスト.

座標の復元式（bearing の向き・own 列の順序・敵行の解釈）とイベント検出は、
壊れたまま気づかないとログの読み方を誤ったまま分析が進む。
基準値をここで固定し、実ログではなく合成ログを渡して決定論を保つ。
"""

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAJECTORY_PATH = REPO_ROOT / "tools" / "battle_analyzer" / "trajectory.py"


def load_module():
    spec = importlib.util.spec_from_file_location("battle_trajectory", TRAJECTORY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


traj = load_module()

OWN10 = [1.0, 0.0, 10.0, 300.0, 0.0, 150.0, 150.0, 150.0, 6.0, 1.0]
ENEMY_ROWS = [
    [0.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0],
]


def payload(own, enemy_rows=None, threat=None):
    rows = [list(r) for r in (enemy_rows or ENEMY_ROWS)]
    return {"own": list(own), "enemy": rows, "threat": list(threat or [0.0, 0.0])}


def action(target=0):
    return {"turn": 0, "speed": 1, "target": target}


def write_log(path: Path, observations, actions) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "observations": [{"ptime": float(i), "data": data} for i, data in enumerate(observations)],
        "actions": [{"ptime": float(i), "data": data} for i, data in enumerate(actions)],
        "infos": [{"ptime": float(i), "data": {}} for i in range(len(observations))],
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def sample_custom_log(tmp_path: Path) -> Path:
    fired = payload([1.0, 0.0, 10.0, 300.0, 45.0, 150.0, 150.0, 150.0, 5.0, 1.0],
                    [[1.0, 90.0, 10.0, 10.0, 0.0]] + ENEMY_ROWS[1:], [1.0, 30.0])
    warned = payload([0.0, 0.0, 10.0, 300.0, 0.0, 150.0, 150.0, 150.0, 6.0, 1.0], threat=[1.0, 30.0])
    return write_log(
        tmp_path / "0" / "log_0.json",
        [{"1": warned}, {"1": fired}, {}],
        [{"1": action(0)}, {"1": action(1)}, {}],
    )


def test_own_field_maps_current_ten_columns():
    assert traj.own_field(OWN10, "x") == 1.0
    assert traj.own_field(OWN10, "y") == 0.0
    assert traj.own_field(OWN10, "ammo") == 6.0
    assert traj.own_field(OWN10, "fuel") == 1.0
    assert traj.own_field(OWN10, "forward_margin") == 150.0


def test_own_field_handles_legacy_eight_columns():
    legacy = [1.0, 2.0, 10.0, 300.0, 15.0, 150.0, 150.0, 150.0]
    assert traj.own_field(legacy, "heading") == 15.0
    assert traj.own_field(legacy, "ammo") is None
    assert traj.own_field(legacy, "fuel") is None


def test_enemy_xy_uses_team_frame_bearing_convention():
    assert traj.enemy_xy(0.0, 0.0, 0.0, 10.0) == pytest.approx((10.0, 0.0))
    assert traj.enemy_xy(0.0, 0.0, 90.0, 10.0) == pytest.approx((0.0, 10.0))
    assert traj.enemy_xy(0.0, 0.0, 180.0, 10.0) == pytest.approx((-10.0, 0.0))
    assert traj.enemy_xy(5.0, -5.0, 90.0, 10.0) == pytest.approx((5.0, 5.0))


def test_enemy_xy_round_trip_from_bearing_and_distance():
    import math

    for bearing, dist in [(0.0, 37.0), (30.0, 82.0), (-120.0, 12.5), (179.0, 140.0)]:
        x, y = traj.enemy_xy(-100.0, 20.0, bearing, dist)
        assert math.hypot(x + 100.0, y - 20.0) == pytest.approx(dist)
        assert math.degrees(math.atan2(y - 20.0, x + 100.0)) == pytest.approx(bearing)


def test_is_replayable_only_for_custom_dict_payloads(tmp_path):
    custom = sample_custom_log(tmp_path / "custom")
    assert traj.is_replayable(custom) is True

    bench = write_log(
        tmp_path / "bench" / "log_0.json",
        [{"1": 0}, {"1": 0}],
        [{"1": None}, {"1": None}],
    )
    assert traj.is_replayable(bench) is False
    assert traj.is_replayable(tmp_path / "missing.json") is False


def test_build_frames_restores_positions_and_ignores_undetected_rows(tmp_path):
    result = traj.build_trajectory(sample_custom_log(tmp_path / "custom"))
    assert result["slots"] == ["1"]
    assert result["frame_count"] == 3
    assert result["own_length"] == 10
    assert result["has_ammo"] is True

    own = result["frames"][0]["own"]["1"]
    assert (own["x"], own["y"], own["alt"]) == (0.0, 0.0, 10.0)
    assert own["heading"] == 0.0
    assert own["ammo"] == 6

    enemies = result["frames"][1]["enemy"]
    assert len(enemies) == 1
    assert enemies[0]["x"] == pytest.approx(1.0, abs=0.01)
    assert enemies[0]["y"] == pytest.approx(10.0, abs=0.01)
    assert enemies[0]["dist"] == 10.0
    assert enemies[0]["escort"] is False


def test_events_detect_lock_launch_warning_and_lost(tmp_path):
    result = traj.build_trajectory(sample_custom_log(tmp_path / "custom"))
    kinds = {}
    for event in result["events"]:
        kinds.setdefault(event["kind"], []).append(event)

    assert len(kinds["warning"]) == 1
    assert kinds["warning"][0]["t"] == 0
    assert len(kinds["lock"]) == 1
    assert kinds["lock"][0]["t"] == 1
    assert len(kinds["launch"]) == 1
    assert kinds["launch"][0]["t"] == 1
    assert "6→5" in kinds["launch"][0]["text"]
    assert len(kinds["lost"]) == 1
    assert kinds["lost"][0]["t"] == 2
    assert result["frames"][2]["own"] == {}


def test_threat_only_reported_while_warn_flag_set(tmp_path):
    log = write_log(
        tmp_path / "0" / "log_0.json",
        [{"1": payload(OWN10, threat=[1.0, 45.0])}, {"1": payload(OWN10, threat=[0.0, 45.0])}],
        [{"1": action(0)}, {"1": action(0)}],
    )
    result = traj.build_trajectory(log)
    assert len(result["frames"][0]["threat"]) == 1
    assert result["frames"][0]["threat"][0]["bearing"] == 45.0
    assert result["frames"][1]["threat"] == []
    assert len([e for e in result["events"] if e["kind"] == "warning"]) == 1


def test_escort_flag_is_exposed(tmp_path):
    rows = [[1.0, 0.0, 20.0, 10.0, 1.0]] + ENEMY_ROWS[1:]
    log = write_log(tmp_path / "0" / "log_0.json", [{"1": payload(OWN10, rows)}], [{"1": action(0)}])
    result = traj.build_trajectory(log)
    assert result["frames"][0]["enemy"][0]["escort"] is True


def test_validation_result_is_attached_when_present(tmp_path):
    log = sample_custom_log(tmp_path / "custom")
    (log.parent / "validation_results.json").write_text(
        json.dumps(
            {
                "own": "Red",
                "details": {
                    "0": {
                        "endReason": "ELIMINATION",
                        "scores": {"Red": 0.72, "Blue": 0.28},
                        "hit_rate": 0.2,
                        "time_bonus": 0.1,
                        "numAlives": {"Red": 3.0, "Blue": 2.0},
                        "step_count": 1035,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    result = traj.build_trajectory(log)["result"]
    assert result["own"] == "Red"
    assert result["endReason"] == "ELIMINATION"
    assert result["scores"]["Red"] == 0.72
    assert result["numAlives"] == {"Red": 3.0, "Blue": 2.0}


def test_payload_contract_matches_battlelog_format_doc():
    assert set(traj.SENSOR_RANGES_KM) == {"radar", "irst", "mws"}
    assert traj.SENSOR_RANGES_KM["radar"] == 80.0
    assert traj.SENSOR_RANGES_KM["irst"] == 120.0
    assert traj.BATTLE_AREA_KM == 150.0


def test_summarize_reports_frames_and_events(tmp_path):
    result = traj.build_trajectory(sample_custom_log(tmp_path / "custom"))
    text = traj.summarize(result)
    assert "フレーム: 3" in text
    assert "イベント: 4 件" in text
    assert "残弾列: あり" in text
