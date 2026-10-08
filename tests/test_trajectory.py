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


def test_lost_event_is_emitted_only_once_per_slot(tmp_path):
    first = payload(OWN10)
    log = write_log(
        tmp_path / "0" / "log_0.json",
        [{"1": first}, {} , {}],
        [{"1": action(0)}, {}, {}],
    )
    result = traj.build_trajectory(log)
    lost = [e for e in result["events"] if e["kind"] == "lost"]
    assert len(lost) == 1
    assert lost[0]["t"] == 1  # 消えた最初のフレームだけ


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
    assert "イベント: 6 件" in text
    assert "残弾列: あり" in text
    assert "発射: 1 件" in text
    assert "探知: 1 件" in text
    assert "ロスト: 0 件" in text
    assert "敵を最初に発見" in text
    assert "空振り" in text


def test_first_detection_is_marked_once_across_slots(tmp_path):
    enemy = [[1.0, 90.0, 10.0, 10.0, 0.0]] + ENEMY_ROWS[1:]
    log = write_log(
        tmp_path / "0" / "log_0.json",
        [{"1": payload(OWN10, enemy), "2": payload(OWN10, enemy)},
         {"1": payload(OWN10, enemy), "2": payload(OWN10, enemy)}],
        [{"1": action(), "2": action()}, {"1": action(), "2": action()}],
    )
    result = traj.build_trajectory(log)
    detect = [e for e in result["events"] if e["kind"] == "detect"]
    assert len(detect) == 2  # スロットごとに初探知は出るが…
    firsts = [e for e in detect if e.get("first")]
    assert len(firsts) == 1  # …「最初の発見」は行(敵)単位で1回だけ
    assert "敵を最初に発見" in firsts[0]["text"]


def test_impact_is_hit_when_enemy_stays_near_aim_point(tmp_path):
    enemy = [[1.0, 90.0, 10.0, 10.0, 0.0]] + ENEMY_ROWS[1:]  # 自機(0,0)から見て方位90°・10km → 照準点(0,10)
    obs0 = payload([1.0, 0.0, 10.0, 300.0, 45.0, 150.0, 150.0, 150.0, 6.0, 1.0], enemy)
    rest = payload([1.0, 0.0, 10.0, 300.0, 45.0, 150.0, 150.0, 150.0, 5.0, 1.0], enemy)
    observations = [{"1": obs0}] + [{"1": rest} for _ in range(7)]  # t=0 発射、t=1..7 残弾5
    actions = [{"1": action(1)}] + [{"1": action(1)} for _ in range(7)]
    log = write_log(tmp_path / "0" / "log_0.json", observations, actions)
    result = traj.build_trajectory(log)
    launch = [e for e in result["events"] if e["kind"] == "launch"][0]
    assert launch["t"] == 1
    flight = launch["dist"] / traj.MISSILE_SPEED_KMS
    end_t = int(1 + flight)
    impacts = [e for e in result["events"] if e["kind"] in ("hit", "miss")]
    assert impacts and impacts[0]["kind"] == "hit"
    assert impacts[0]["t"] == end_t
    assert "命中推定" in impacts[0]["text"]


def test_enemy_point_returns_none_for_undetected_rows():
    assert traj.enemy_point(OWN10, ENEMY_ROWS[0]) is None
    assert traj.enemy_point(OWN10, [1.0, 45.0, 0.0, 10.0, 0.0]) is None
    point = traj.enemy_point(OWN10, [1.0, 45.0, 10.0, 10.0, 1.0])
    assert point is not None
    assert point["escort"] is True
    assert point["dist"] == 10.0


def test_aim_exposes_target_point_from_action_target(tmp_path):
    result = traj.build_trajectory(sample_custom_log(tmp_path / "custom"))
    aim = result["frames"][1]["aim"]
    assert len(aim) == 1
    assert aim[0]["slot"] == "1"
    assert aim[0]["row"] == 1
    assert aim[0]["dist"] == 10.0
    assert aim[0]["x"] == pytest.approx(1.0, abs=0.01)
    assert aim[0]["y"] == pytest.approx(10.0, abs=0.01)
    assert result["frames"][0]["aim"] == []


def test_aim_omitted_when_target_row_is_undetected(tmp_path):
    log = write_log(
        tmp_path / "0" / "log_0.json",
        [{"1": payload(OWN10)}, {"1": payload(OWN10)}],
        [{"1": action(0)}, {"1": action(1)}],
    )
    result = traj.build_trajectory(log)
    assert result["frames"][1]["aim"] == []


def test_launch_flies_from_launch_point_toward_target(tmp_path):
    result = traj.build_trajectory(sample_custom_log(tmp_path / "custom"))
    launch = [e for e in result["events"] if e["kind"] == "launch"][0]
    assert launch["t"] == 1
    assert launch["row"] == 1
    assert launch["dist"] == 10.0
    assert "標的 行1 10.0 km" in launch["text"]

    shots1 = result["frames"][1]["shots"]
    assert len(shots1) == 1
    assert shots1[0]["age"] == 0.0
    assert (shots1[0]["x"], shots1[0]["y"]) == (shots1[0]["fx"], shots1[0]["fy"])
    assert (shots1[0]["tx"], shots1[0]["ty"]) == (1.0, 10.0)
    assert shots1[0]["flight"] == pytest.approx(round(10.0 / traj.MISSILE_SPEED_KMS, 1), abs=0.01)

    shots2 = result["frames"][2]["shots"]
    assert len(shots2) == 1
    assert shots2[0]["age"] == 1.0
    assert shots2[0]["x"] == pytest.approx(1.0, abs=0.01)
    assert shots2[0]["y"] == pytest.approx(1.5, abs=0.01)


def test_shots_stop_after_estimated_flight_window(tmp_path):
    row = [[1.0, 90.0, 10.0, 10.0, 0.0]] + ENEMY_ROWS[1:]
    frames = [
        payload([1.0, 0.0, 10.0, 300.0, 45.0, 150.0, 150.0, 150.0, a, 1.0], row)
        for a in (6.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0)
    ]
    log = write_log(
        tmp_path / "0" / "log_0.json",
        [{"1": p} for p in frames],
        [{"1": action(1)} for _ in frames],
    )
    result = traj.build_trajectory(log)
    flight = int(10.0 / traj.MISSILE_SPEED_KMS)
    assert [len(f["shots"]) for f in result["frames"][:4]] == [0, 1, 1, 1]
    assert len(result["frames"][1 + flight]["shots"]) == 1
    assert result["frames"][1 + flight + 1]["shots"] == []


def test_launch_without_detected_target_reports_unknown(tmp_path):
    log = write_log(
        tmp_path / "0" / "log_0.json",
        [{"1": payload(OWN10)},
         {"1": payload([1.0, 0.0, 10.0, 300.0, 45.0, 150.0, 150.0, 150.0, 5.0, 1.0])}],
        [{"1": action(0)}, {"1": action(1)}],
    )
    result = traj.build_trajectory(log)
    launch = [e for e in result["events"] if e["kind"] == "launch"][0]
    assert launch["dist"] is None
    assert "標的未探知" in launch["text"]
    shot = result["frames"][1]["shots"][0]
    assert shot["tx"] is None
    assert (shot["x"], shot["y"]) == (shot["fx"], shot["fy"])


def test_classify_sensor_uses_distance_and_escort_flag():
    assert traj.classify_sensor(80.0, False) == "radar"
    assert traj.classify_sensor(80.1, False) == "irst"
    assert traj.classify_sensor(120.0, False) == "irst"
    assert traj.classify_sensor(130.0, True) == "rcs"
    assert traj.classify_sensor(130.0, False) == "far"
    assert traj.classify_sensor(160.0, True) == "far"
    assert set(traj.SENSOR_LABELS) == {"radar", "irst", "rcs", "far"}


def test_enemy_entries_carry_row_slot_and_sensor(tmp_path):
    result = traj.build_trajectory(sample_custom_log(tmp_path / "custom"))
    enemy = result["frames"][1]["enemy"][0]
    assert enemy["row"] == 1
    assert enemy["slot"] == "1"
    assert enemy["sensor"] == "radar"


def test_detect_then_lose_then_reacquire_events(tmp_path):
    """敵個体IDが無いので位置近傍で疑似追跡する。8フレーム連続で消えたらロスト."""
    seen = payload(OWN10, [[1.0, 90.0, 10.0, 10.0, 0.0]] + ENEMY_ROWS[1:])
    empty = payload(OWN10)
    observations = [seen] + [empty] * 9 + [seen, seen]
    log = write_log(
        tmp_path / "0" / "log_0.json",
        [{"1": p} for p in observations],
        [{"1": action(0)} for _ in observations],
    )
    result = traj.build_trajectory(log)
    kinds = [(e["t"], e["kind"]) for e in result["events"]]
    assert (0, "detect") in kinds
    assert (9, "lose") in kinds
    assert (10, "detect") in kinds
    assert sum(1 for _, kind in kinds if kind == "lose") == 1
    assert sum(1 for _, kind in kinds if kind == "detect") == 2
    texts = [e["text"] for e in result["events"] if e["kind"] == "detect"]
    assert any("再探知" in text for text in texts)
    assert any("レーダ" in text for text in texts)
    lose_texts = [e["text"] for e in result["events"] if e["kind"] == "lose"]
    assert any("ロスト" in text for text in lose_texts)


def test_detect_event_reports_sensor_and_distance(tmp_path):
    far_row = [[1.0, 90.0, 130.0, 10.0, 1.0]] + ENEMY_ROWS[1:]
    log = write_log(
        tmp_path / "0" / "log_0.json",
        [{"1": payload(OWN10, far_row)}],
        [{"1": action(0)}],
    )
    result = traj.build_trajectory(log)
    detect = [e for e in result["events"] if e["kind"] == "detect"]
    assert len(detect) == 1
    assert detect[0]["sensor"] == "rcs"
    assert detect[0]["dist"] == 130.0
    assert "130.0 km" in detect[0]["text"]
    assert "RCS" in detect[0]["text"]


def test_teams_list_own_and_fused_enemy(tmp_path):
    result = traj.build_trajectory(sample_custom_log(tmp_path / "custom"))
    teams = result["frames"][1]["teams"]
    own = [t for t in teams if t["side"] == "own"]
    enemy = [t for t in teams if t["side"] == "enemy"]
    assert [(t["id"], t["x"]) for t in own] == [("1", 1.0)]
    assert len(enemy) == 1
    assert enemy[0]["id"] == "E1"
    assert enemy[0]["x"] == pytest.approx(1.0, abs=0.01)
    assert enemy[0]["y"] == pytest.approx(10.0, abs=0.01)
    assert enemy[0]["seen_by"] == 1
    # 自軍スロット数と同数の own が入る
    assert sum(1 for t in result["frames"][0]["teams"] if t["side"] == "own") == 1


def test_teams_merge_same_enemy_seen_by_multiple_craft(tmp_path):
    own1 = payload([1.0, 0.0, 10.0, 300.0, 0.0, 150.0, 150.0, 150.0, 6.0, 1.0],
                   [[1.0, 90.0, 10.0, 10.0, 0.0]] + ENEMY_ROWS[1:])
    own2 = payload([11.0, 0.0, 10.0, 300.0, 0.0, 150.0, 150.0, 150.0, 6.0, 1.0],
                   [[1.0, 135.0, 14.142, 10.0, 0.0]] + ENEMY_ROWS[1:])
    log = write_log(
        tmp_path / "0" / "log_0.json",
        [{"1": own1, "2": own2}],
        [{"1": action(0), "2": action(0)}],
    )
    result = traj.build_trajectory(log)
    enemy = [t for t in result["frames"][0]["teams"] if t["side"] == "enemy"]
    assert len(enemy) == 1
    assert enemy[0]["seen_by"] == 2
    # 2機の観測が同じ絶対位置（1,10）に融合される
    assert enemy[0]["x"] == pytest.approx(1.0, abs=0.05)
    assert enemy[0]["y"] == pytest.approx(10.0, abs=0.01)


def test_fuse_teams_caps_enemies_at_five_and_dedups_same_point():
    frames = [
        {
            "own": {"1": {"x": 0.0, "y": 0.0, "heading": 0.0}},
            "enemy": [
                {"x": 10.0, "y": 0.0}, {"x": 10.1, "y": 0.0},
                {"x": -10.0, "y": 5.0}, {"x": -9.9, "y": 5.1},
                {"x": -10.0, "y": -5.0}, {"x": -10.1, "y": -4.9},
                {"x": 20.0, "y": 20.0}, {"x": 20.1, "y": 20.1},
                {"x": 0.0, "y": 20.0}, {"x": -0.1, "y": 20.1},
                {"x": 30.0, "y": 0.0}, {"x": 30.1, "y": 0.1},
                {"x": 0.0, "y": -20.0}, {"x": 0.1, "y": -20.1},
            ],
        }
    ]
    traj.fuse_teams_into_frames(frames)
    teams = frames[0]["teams"]
    own = [t for t in teams if t["side"] == "own"]
    enemy = [t for t in teams if t["side"] == "enemy"]
    assert len(own) == 1 and own[0]["id"] == "1"
    assert len(enemy) == traj.FUSE_MAX_CRAFT == 5
    assert all(t["seen_by"] == 2 for t in enemy)
    assert [t["id"] for t in enemy] == [f"E{i}" for i in range(1, 6)]


def test_fuse_teams_uses_direct_enemy_positions_when_provided():
    frames = [
        {
            "own": {"1": {"x": 0.0, "y": 0.0, "heading": 0.0}},
            "enemy": [{"x": 10.0, "y": 5.0}],
        }
    ]
    direct = [[{"id": "BlueF1", "x": 60.0, "y": 20.0, "heading": None, "alive": True}]]
    traj.fuse_teams_into_frames(frames, direct)
    enemy = [t for t in frames[0]["teams"] if t["side"] == "enemy"]
    assert len(enemy) == 1
    assert enemy[0]["id"] == "BlueF1"
    assert enemy[0]["x"] == pytest.approx(60.0)
    assert enemy[0]["y"] == pytest.approx(20.0)
    assert enemy[0]["source"] == "direct"
    assert "seen_by" not in enemy[0]


def test_fuse_teams_drops_dead_direct_entries_and_falls_back_without_direct():
    direct = [
        [
            {"id": "BlueF1", "x": 60.0, "y": 20.0, "heading": 0.0, "alive": False},
            {"id": "BlueF2", "x": 70.0, "y": 21.0, "heading": 90.0, "alive": True},
        ]
    ]
    frames = [
        {"own": {"1": {"x": 0.0, "y": 0.0, "heading": 0.0}}, "enemy": []},
        {"own": {"1": {"x": 0.0, "y": 0.0, "heading": 0.0}}, "enemy": [{"x": 10.0, "y": 5.0}]},
    ]
    traj.fuse_teams_into_frames(frames, direct)
    e0 = [t for t in frames[0]["teams"] if t["side"] == "enemy"]
    assert [t["id"] for t in e0] == ["BlueF2"]
    assert e0[0]["source"] == "direct"
    e1 = [t for t in frames[1]["teams"] if t["side"] == "enemy"]
    assert e1[0]["id"] == "E1"  # direct が無いフレームはセンサ融合にフォールバック


def test_build_frames_reads_enemies_direct_from_log(tmp_path):
    observations = [
        {"ptime": 0.0, "data": {"1": payload(OWN10)}},
        {"ptime": 1.0, "data": {"1": payload(OWN10)}},
        {"ptime": 2.0, "data": {"1": payload(OWN10)}},
    ]
    actions = [{"ptime": float(i), "data": {"1": action(0)}} for i in range(3)]
    enemies_direct = [
        [{"id": "BlueF1", "x": 60.0, "y": 20.0, "heading": 0.0, "alive": True}],
        [{"id": "BlueF1", "x": 61.0, "y": 20.0, "heading": 0.0, "alive": True}],
        [{"id": "BlueF1", "x": 62.0, "y": 20.0, "heading": 0.0, "alive": False}],
    ]
    doc = {
        "observations": observations,
        "actions": actions,
        "infos": observations,
        "enemies_direct": enemies_direct,
    }
    path = tmp_path / "0" / "log_0.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    result = traj.build_trajectory(path)
    teams = [t for f in result["frames"] for t in f["teams"] if t["side"] == "enemy"]
    assert [t["id"] for t in teams] == ["BlueF1", "BlueF1"]  # 撃墜後(alive=False)は出さない
    assert all(t["source"] == "direct" for t in teams)
    assert teams[0]["x"] == pytest.approx(60.0)
    assert teams[1]["x"] == pytest.approx(61.0)


def test_enemy_team_ids_stable_across_frames_and_heading_from_motion():
    frames = []
    x = 10.0
    for _ in range(5):
        frames.append(
            {
                "own": {"1": {"x": 0.0, "y": 0.0, "heading": 0.0}},
                "enemy": [{"x": x, "y": 5.0}],
            }
        )
        x += 1.0
    traj.fuse_teams_into_frames(frames)
    ids = {t["id"] for f in frames for t in f["teams"] if t["side"] == "enemy"}
    assert ids == {"E1"}
    headings = [
        t["heading"]
        for f in frames
        for t in f["teams"]
        if t["side"] == "enemy" and t["heading"] is not None
    ]
    assert headings == [0.0] * 4
