"""1フレームを機体ごとに 観測 / 判断 / 行動 に分けて見せる解析。

ログが持つのは「観測」（own/enemy/threat）と「行動」（turn/speed/target）だけで、
エージェントの「判断」は記録されない。だから判断は観測と行動から導出する:
  - 選んだ標的行と、その距離・方位・速度
  - 照準点（照準した位置）と機首からのずれ（off_nose）
  - そのフレームで撃てたか（残弾・脅威・射程・境界距離）
行動は turn/speed の index なので、config.json の turnTable/speedTable で値に直す。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

_CACHE: dict = {}


def _load(path: Path) -> dict:
    stat = path.stat()
    key = str(path)
    hit = _CACHE.get(key)
    if hit and hit[0] == stat.st_mtime_ns:
        return hit[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    _CACHE[key] = (stat.st_mtime_ns, data)
    return data


def _tables(config: dict) -> tuple[list, list]:
    fixed = config.get("Fixed", {}) if isinstance(config, dict) else {}
    return list(fixed.get("turnTable") or []), list(fixed.get("speedTable") or [])


def _own(own: list) -> dict:
    def g(i, nd=1):
        try:
            v = float(own[i])
        except (IndexError, TypeError, ValueError):
            return None
        return round(v, nd)

    return {
        "x": g(0), "y": g(1), "alt": g(2), "speed": g(3),
        "heading": g(4), "marginSide": g(5), "marginFront": g(6), "marginBack": g(7),
        "ammo": g(8, 0), "fuel": g(9, 0),
    }


def _enemy_rows(rows: list) -> list[dict]:
    out = []
    for i, r in enumerate(rows or []):
        def g(j, nd=1):
            try:
                v = float(r[j])
            except (IndexError, TypeError, ValueError):
                return None
            return round(v, nd)

        out.append({
            "row": i + 1, "det": g(0, 0), "bearing": g(1), "dist": g(2),
            "alt": g(3), "escort": g(4, 0), "speed": g(5, 2),
        })
    return out


def _threat(threat: list) -> dict:
    flag = None
    bearing = None
    try:
        flag = round(float(threat[0]), 0)
        bearing = round(float(threat[1]), 1)
    except (IndexError, TypeError, ValueError):
        pass
    return {"flag": flag, "bearing": bearing}


def _aim_point(own: list, row: list) -> tuple[float, float] | None:
    try:
        ox, oy = float(own[0]), float(own[1])
        dist, brg = float(row[2]), float(row[1])
    except (IndexError, TypeError, ValueError):
        return None
    return (ox + dist * math.cos(math.radians(brg)),
            oy + dist * math.sin(math.radians(brg)))


def build_frame(log_path: Path, frame_idx: int, config: dict | None = None) -> dict:
    """1フレームの 観測/判断/行動 を機体ごとに返す."""
    data = _load(log_path)
    obs = data.get("observations") or []
    acts = data.get("actions") or []
    if not obs:
        return {"log": log_path.name, "frames": 0, "frame": 0, "aircraft": []}
    idx = max(0, min(int(frame_idx), len(obs) - 1))
    o_entry = obs[idx]
    a_entry = acts[idx] if idx < len(acts) else {}
    o_data = o_entry.get("data", {}) if isinstance(o_entry, dict) else {}
    a_data = a_entry.get("data", {}) if isinstance(a_entry, dict) else {}
    turn_table, speed_table = _tables(config or {})

    aircraft = []
    for slot in sorted(o_data.keys()):
        payload = o_data.get(slot)
        if not isinstance(payload, dict):
            continue
        own = payload.get("own") or []
        rows = payload.get("enemy") or []
        threat = payload.get("threat") or []
        action = a_data.get(slot) or {}
        turn_i = int(action.get("turn", 0) or 0)
        speed_i = int(action.get("speed", 0) or 0)
        target_i = int(action.get("target", 0) or 0)

        obs_view = {
            "own": _own(own),
            "enemies": _enemy_rows(rows),
            "threat": _threat(threat),
        }

        target_row = None
        aim = None
        off_nose = None
        if 0 < target_i <= len(rows):
            target_row = _enemy_rows(rows)[target_i - 1]
            aim = _aim_point(own, rows[target_i - 1])
            try:
                heading = float(own[4])
                bearing = float(rows[target_i - 1][1])
                off_nose = round(abs((heading - bearing + 180.0) % 360.0 - 180.0), 1)
            except (IndexError, TypeError, ValueError):
                off_nose = None

        dist = target_row["dist"] if target_row else None
        decision = {
            "target_row": target_i or None,
            "target": target_row,
            "aim": {"x": round(aim[0], 1), "y": round(aim[1], 1)} if aim else None,
            "off_nose": off_nose,
            "ammo": obs_view["own"]["ammo"],
            "threat": obs_view["threat"]["flag"],
            "can_fire": bool(
                obs_view["own"]["ammo"] and not obs_view["threat"]["flag"]
                and dist is not None and dist <= 50.0
            ),
            "break_zone": bool(dist is not None and dist <= 35.0),
        }

        action_view = {
            "turn_index": turn_i,
            "turn_deg": turn_table[turn_i] if 0 <= turn_i < len(turn_table) else None,
            "speed_index": speed_i,
            "speed_ms": speed_table[speed_i] if 0 <= speed_i < len(speed_table) else None,
            "target_row": target_i or None,
        }

        aircraft.append({
            "slot": slot,
            "observation": obs_view,
            "decision": decision,
            "action": action_view,
        })

    return {
        "log": log_path.name,
        "log_path": log_path.as_posix(),
        "frames": len(obs),
        "frame": idx,
        "ptime": o_entry.get("ptime") if isinstance(o_entry, dict) else None,
        "aircraft": aircraft,
    }
