"""対戦ログから軌跡を復元する（ダッシュボードの「軌跡」タブ用）.

ログには自機の状態が陣営座標系で、自機の探知した敵が「方位・水平距離・高度」で
入っている。敵の座標は次の式で復元できる（実測で検証済み: 4機が独立に探知した
敵の推定位置が平均 0.07 km で一致した）:

    enemy_x = own_x + dist * cos(bearing)
    enemy_y = own_y + dist * sin(bearing)

bearing は陣営座標系で 0 = 敵陣方向(+x)、反時計回りが正。水平面のみ扱うため
高度は別管理（ユース部門は高度固定）。

対象は自作 Agent のログのみ。baseline のログは observation の payload がスカラーで
位置情報を持たないため `is_replayable()` が False を返す。

Usage:
    python tools/battle_analyzer/trajectory.py workspace/results_tel/0/log_0.json
    python tools/battle_analyzer/trajectory.py workspace/results_tel/0/log_0.json --json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# 自機観測（float32[10] / 古い世代は float32[8]）
OWN_INDEX = {
    "x": 0,
    "y": 1,
    "alt": 2,
    "speed": 3,
    "heading": 4,
    "forward_margin": 6,
    "back_margin": 7,
    "ammo": 8,
    "fuel": 9,
}
SENSOR_RANGES_KM = {"radar": 80.0, "irst": 120.0, "mws": 10.0}
BATTLE_AREA_KM = 150.0

# 誘導弾の飛翔表示（推定）。弾の座標はログに無いため、発射点→標的を直線補間する。
MISSILE_SPEED_KMS = 1.5
MISSILE_FLIGHT_MIN_SEC = 5.0
MISSILE_FLIGHT_MAX_SEC = 60.0

# 探知イベントの検出（敵の個体IDはログに無いので位置の近傍一致で疑似追跡する）
DETECT_MATCH_KM = 8.0
# 実ログの欠落ギャップ分布（同スロット・行の再出現）は 1〜3 フレームのチラつきが大半。
# それらを跟丟だと誤認すると再探知イベントが乱舞するため、8 フレーム連続で切れたら跟丟。
DETECT_MISS_FRAMES = 8
RCS_ESCORT_RANGE_KM = 150.0

SENSOR_LABELS = {
    "radar": "レーダ ≤80 km",
    "irst": "IRST ≤120 km",
    "rcs": "護衛対象機（RCS拡大）≤150 km",
    "far": "遠距離 >120 km",
}


def round_or_none(value, digits: int = 2):
    if value is None:
        return None
    return round(float(value), digits)


def own_field(own: list, name: str):
    index = OWN_INDEX.get(name)
    if index is None or index >= len(own):
        return None
    return own[index]


def enemy_xy(own_x: float, own_y: float, bearing_deg: float, dist_km: float) -> tuple[float, float]:
    rad = math.radians(bearing_deg)
    return own_x + dist_km * math.cos(rad), own_y + dist_km * math.sin(rad)


def enemy_point(own: list, row) -> dict | None:
    """`enemy` の1行を陣営座標系の点に復元する。未探知行は None。"""
    values = list(row) + [0.0] * (5 - len(row))
    flag, bearing, dist, alt, escort = values[:5]
    if float(flag) < 0.5 or float(dist) <= 0.0:
        return None
    x, y = enemy_xy(own_field(own, "x"), own_field(own, "y"), float(bearing), float(dist))
    return {
        "x": round_or_none(x),
        "y": round_or_none(y),
        "alt": round_or_none(alt),
        "bearing": round_or_none(float(bearing), 1),
        "dist": round_or_none(float(dist)),
        "escort": bool(float(escort) >= 0.5),
    }


def classify_sensor(dist_km: float, escort: bool) -> str:
    """距離と護衛対象機フラグから、どのセンサで見えたと推定されるかを返す（推定）.

    レーダ Lref=80 km / IRST=120 km、護衛対象機は rcsScale=16 でレーダ探知距離が
    約2倍（~150 km）になるという既知制約に基づく分類。実際のセンサ切替はログに無い。
    """
    if dist_km <= SENSOR_RANGES_KM["radar"]:
        return "radar"
    if dist_km <= SENSOR_RANGES_KM["irst"]:
        return "irst"
    if escort and dist_km <= RCS_ESCORT_RANGE_KM:
        return "rcs"
    return "far"


def _match_track(tracks: list[dict], point: dict, matched: set[int], alive: bool) -> int | None:
    """検出点に最も近い追跡対象を返す（既に使った番号と生死が一致するものだけ）."""
    best = None
    best_dist = DETECT_MATCH_KM
    for index, track in enumerate(tracks):
        if index in matched or track["alive"] is not alive:
            continue
        distance = math.hypot(point["x"] - track["x"], point["y"] - track["y"])
        if distance <= best_dist:
            best, best_dist = index, distance
    return best


def load_log(log_path: Path) -> dict:
    return json.loads(log_path.read_text(encoding="utf-8"))


def first_payload(log: dict):
    for frame in log.get("observations") or []:
        data = frame.get("data") or {}
        for slot_key, payload in data.items():
            if isinstance(payload, dict) and isinstance(payload.get("own"), list):
                return payload
    return None


def is_replayable(log_path: Path) -> bool:
    try:
        return first_payload(load_log(log_path)) is not None
    except (OSError, json.JSONDecodeError):
        return False


def _slot_actions(log: dict, index: int) -> dict:
    actions = log.get("actions") or []
    if index >= len(actions):
        return {}
    data = actions[index].get("data") or {}
    return {key: value for key, value in data.items() if isinstance(value, dict)}


def _validation_result(log_path: Path) -> dict:
    results = log_path.parent / "validation_results.json"
    if not results.exists():
        return {}
    try:
        payload = json.loads(results.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    details = payload.get("details") or {}
    if not details:
        return {}
    try:
        fight_index = int(log_path.stem.split("_")[-1])
    except ValueError:
        fight_index = 0
    detail = details.get(str(fight_index))
    if not isinstance(detail, dict):
        first = next(iter(details.values()))
        detail = first if isinstance(first, dict) else {}
    return {
        "own": payload.get("own", ""),
        "endReason": detail.get("endReason", ""),
        "scores": detail.get("scores", {}),
        "hit_rate": detail.get("hit_rate"),
        "time_bonus": detail.get("time_bonus"),
        "numAlives": detail.get("numAlives", {}),
        "step_count": detail.get("step_count"),
        "finishedTime": detail.get("finishedTime"),
    }


def build_frames(log: dict) -> tuple[list[dict], list[str]]:
    frames = []
    slots_seen: list[str] = []
    previous_ammo: dict[str, float | None] = {}
    previous_warn: dict[str, float] = {}
    previous_target: dict[str, int] = {}
    launches: list[dict] = []
    tracks: dict[str, list[dict]] = {}

    for index, entry in enumerate(log.get("observations") or []):
        ptime = entry.get("ptime", index)
        data = entry.get("data") or {}
        actions = _slot_actions(log, index)
        frame = {
            "t": index,
            "ptime": round_or_none(ptime, 1),
            "own": {},
            "enemy": [],
            "threat": [],
            "aim": [],
            "shots": [],
        }
        events = []
        aim_by_slot: dict[str, dict] = {}

        for slot_key in sorted(data.keys()):
            payload = data[slot_key]
            if not isinstance(payload, dict) or not isinstance(payload.get("own"), list):
                continue
            if slot_key not in slots_seen:
                slots_seen.append(slot_key)
            own = payload["own"]
            frame["own"][slot_key] = {
                "x": round_or_none(own_field(own, "x")),
                "y": round_or_none(own_field(own, "y")),
                "alt": round_or_none(own_field(own, "alt")),
                "speed": round_or_none(own_field(own, "speed"), 1),
                "heading": round_or_none(own_field(own, "heading"), 1),
                "ammo": round_or_none(own_field(own, "ammo"), 0),
                "fuel": round_or_none(own_field(own, "fuel"), 0),
            }

            action = actions.get(slot_key) or {}
            target = int(action.get("target", 0) or 0)
            rows = payload.get("enemy") or []
            if 0 < target <= len(rows):
                point = enemy_point(own, rows[target - 1])
                if point:
                    aim = {"slot": slot_key, "row": target}
                    aim.update(point)
                    frame["aim"].append(aim)
                    aim_by_slot[slot_key] = aim

            ammo = own_field(own, "ammo")
            if ammo is not None:
                before = previous_ammo.get(slot_key)
                if before is not None and ammo < before:
                    aim = aim_by_slot.get(slot_key)
                    launch = {
                        "t": index,
                        "slot": slot_key,
                        "fx": frame["own"][slot_key]["x"],
                        "fy": frame["own"][slot_key]["y"],
                    }
                    if aim:
                        launch.update({"tx": aim["x"], "ty": aim["y"], "dist": aim["dist"]})
                        launch["flight"] = max(
                            MISSILE_FLIGHT_MIN_SEC,
                            min(MISSILE_FLIGHT_MAX_SEC, float(aim["dist"] or 0.0) / MISSILE_SPEED_KMS),
                        )
                        target_text = f"標的 行{aim['row']} {aim['dist']} km"
                    else:
                        launch.update({"tx": None, "ty": None, "dist": None})
                        launch["flight"] = MISSILE_FLIGHT_MAX_SEC
                        target_text = "標的未探知"
                    launches.append(launch)
                    events.append(
                        {
                            "t": index,
                            "kind": "launch",
                            "slot": slot_key,
                            "row": (aim or {}).get("row"),
                            "dist": launch["dist"],
                            "text": f"{slot_key}号 誘導弾発射（残弾 {int(before)}→{int(ammo)} / {target_text}）",
                        }
                    )
                previous_ammo[slot_key] = ammo

            detections = []
            for row_index, row in enumerate(rows):
                point = enemy_point(own, row)
                if point is None or point["x"] is None or point["y"] is None:
                    continue
                point["slot"] = slot_key
                point["row"] = row_index + 1
                point["sensor"] = classify_sensor(float(point["dist"]), point["escort"])
                detections.append(point)
                frame["enemy"].append(point)

            slot_tracks = tracks.setdefault(slot_key, [])
            matched: set[int] = set()
            for point in detections:
                track_index = _match_track(slot_tracks, point, matched, alive=True)
                if track_index is None:
                    track_index = _match_track(slot_tracks, point, matched, alive=False)
                if track_index is None:
                    slot_tracks.append(
                        {
                            "x": point["x"],
                            "y": point["y"],
                            "dist": point["dist"],
                            "sensor": point["sensor"],
                            "miss": 0,
                            "alive": True,
                        }
                    )
                    matched.add(len(slot_tracks) - 1)
                    events.append(
                        {
                            "t": index,
                            "kind": "detect",
                            "slot": slot_key,
                            "row": point["row"],
                            "dist": point["dist"],
                            "sensor": point["sensor"],
                            "text": (
                                f"{slot_key}号 敵を探知（{point['dist']} km / "
                                f"{SENSOR_LABELS[point['sensor']]}）"
                            ),
                        }
                    )
                    continue
                track = slot_tracks[track_index]
                matched.add(track_index)
                track.update(
                    {
                        "x": point["x"],
                        "y": point["y"],
                        "dist": point["dist"],
                        "sensor": point["sensor"],
                        "miss": 0,
                    }
                )
                if not track["alive"]:
                    track["alive"] = True
                    events.append(
                        {
                            "t": index,
                            "kind": "detect",
                            "slot": slot_key,
                            "row": point["row"],
                            "dist": point["dist"],
                            "sensor": point["sensor"],
                            "text": (
                                f"{slot_key}号 敵を再探知（{point['dist']} km / "
                                f"{SENSOR_LABELS[point['sensor']]}）"
                            ),
                        }
                    )
            for track_index, track in enumerate(slot_tracks):
                if track_index in matched:
                    continue
                track["miss"] += 1
                if track["alive"] and track["miss"] > DETECT_MISS_FRAMES:
                    track["alive"] = False
                    events.append(
                        {
                            "t": index,
                            "kind": "lose",
                            "slot": slot_key,
                            "dist": track["dist"],
                            "sensor": track["sensor"],
                            "text": f"{slot_key}号 目標跟丟（{track['dist']} km先を追跡できず）",
                        }
                    )

            threat = payload.get("threat") or []
            threat_values = list(threat) + [0.0] * (2 - len(threat))
            warn, bearing = float(threat_values[0]), float(threat_values[1])
            if warn >= 0.5:
                x, y = enemy_xy(own_field(own, "x"), own_field(own, "y"), bearing, 0.0)
                frame["threat"].append({"slot": slot_key, "bearing": round_or_none(bearing, 1), "x": x, "y": y})
                if previous_warn.get(slot_key, 0.0) < 0.5:
                    events.append(
                        {
                            "t": index,
                            "kind": "warning",
                            "slot": slot_key,
                            "text": f"{slot_key}号 被弾警報（方位 {bearing:.0f}°）",
                        }
                    )
            previous_warn[slot_key] = warn

            if target and previous_target.get(slot_key, 0) == 0:
                events.append(
                    {
                        "t": index,
                        "kind": "lock",
                        "slot": slot_key,
                        "text": f"{slot_key}号 射撃指示（target={target}）",
                    }
                )
            previous_target[slot_key] = target

        for launch in launches:
            age = index - launch["t"]
            if age < 0 or age > launch["flight"]:
                continue
            progress = age / launch["flight"]
            if launch["tx"] is None:
                x, y = launch["fx"], launch["fy"]
            else:
                x = launch["fx"] + (launch["tx"] - launch["fx"]) * progress
                y = launch["fy"] + (launch["ty"] - launch["fy"]) * progress
            frame["shots"].append(
                {
                    "slot": launch["slot"],
                    "t0": launch["t"],
                    "age": round_or_none(age, 1),
                    "x": round_or_none(x),
                    "y": round_or_none(y),
                    "fx": launch["fx"],
                    "fy": launch["fy"],
                    "tx": launch["tx"],
                    "ty": launch["ty"],
                    "dist": launch["dist"],
                    "flight": round_or_none(launch["flight"], 1),
                }
            )

        for slot_key in previous_ammo:
            if slot_key not in frame["own"]:
                events.append(
                    {
                        "t": index,
                        "kind": "lost",
                        "slot": slot_key,
                        "text": f"{slot_key}号 応答が途絶えた（撃墜またはログ欠落）",
                    }
                )

        frame["action"] = {key: actions[key] for key in sorted(actions.keys())}
        frame["events"] = events
        frames.append(frame)

    return frames, slots_seen


def build_trajectory(log_path: Path) -> dict:
    log = load_log(log_path)
    frames, slots = build_frames(log)
    events = [event for frame in frames for event in frame["events"]]
    try:
        display = log_path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        display = log_path.as_posix()
    payload = first_payload(log) or {}
    return {
        "log": display,
        "slots": slots,
        "frame_count": len(frames),
        "own_length": len(payload.get("own") or []),
        "has_ammo": len(payload.get("own") or []) >= 10,
        "bounds": {"x": BATTLE_AREA_KM, "y": BATTLE_AREA_KM},
        "sensor_ranges": SENSOR_RANGES_KM,
        "missile_model": {
            "speed_kms": MISSILE_SPEED_KMS,
            "min_sec": MISSILE_FLIGHT_MIN_SEC,
            "max_sec": MISSILE_FLIGHT_MAX_SEC,
        },
        "frames": frames,
        "events": events,
        "result": _validation_result(log_path),
    }


def summarize(trajectory: dict) -> str:
    result = trajectory.get("result") or {}
    scores = result.get("scores") or {}
    alives = result.get("numAlives") or {}
    lines = [
        f"ログ: {trajectory['log']}",
        f"フレーム: {trajectory['frame_count']} / 自機スロット: {', '.join(trajectory['slots']) or '-'}",
        f"own 長さ: {trajectory['own_length']}（残弾列: {'あり' if trajectory['has_ammo'] else 'なし'}）",
        f"イベント: {len(trajectory['events'])} 件",
        f"発射: {sum(1 for e in trajectory['events'] if e['kind'] == 'launch')} 件 / "
        f"射撃指示: {sum(len(f.get('aim') or []) for f in trajectory['frames'])} フレーム / "
        f"飛翔中の弾（推定）: {sum(len(f.get('shots') or []) for f in trajectory['frames'])} フレーム",
        f"探知: {sum(1 for e in trajectory['events'] if e['kind'] == 'detect')} 件 / "
        f"跟丟: {sum(1 for e in trajectory['events'] if e['kind'] == 'lose')} 件",
    ]
    if result:
        lines.append(
            "結果: "
            + f"{result.get('endReason', '?')} / score {scores} / hit_rate {result.get('hit_rate')} / alive {alives}"
        )
    for event in trajectory["events"][:10]:
        lines.append(f"  t={event['t']:>4} {event['kind']:<7} {event['text']}")
    if len(trajectory["events"]) > 10:
        lines.append(f"  ... 他 {len(trajectory['events']) - 10} 件")
    return "\n".join(lines)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="対戦ログから軌跡を復元する")
    parser.add_argument("log", help="log_{n}.json のパス")
    parser.add_argument("--json", action="store_true", help="JSON を標準出力に吐く")
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        raise SystemExit(f"ログが見つかりません: {log_path}")
    if not is_replayable(log_path):
        raise SystemExit("このログは軌跡再現できません（自作 Agent のログのみ対象）")

    trajectory = build_trajectory(log_path)
    if args.json:
        print(json.dumps(trajectory, ensure_ascii=False))
    else:
        print(summarize(trajectory))


if __name__ == "__main__":
    main()
