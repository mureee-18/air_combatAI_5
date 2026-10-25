"""判断（decision）: 観測と行動から「何を選んでどう考えたか」を導出する。

ログは判断そのものを残していない。だから観測（observation）と行動（action）から
- 選んだ標的行とその距離・方位・速度
- 照準点と機首からのずれ（off_nose）
- そのフレームで撃てたか（残弾・脅威・射程・境界距離）
を組み立てる。行動（action）の一覧と判定条件はここ]].
"""

from __future__ import annotations

from . import observation

# 既定値。実際の値は agent/args.json（fireRangeKm / breakRangeKm）から渡す
FIRE_RANGE_KM = 50.0
BREAK_RANGE_KM = 35.0


def _off_nose(own: dict, target: dict):
    try:
        heading = float(own["heading"])
        bearing = float(target["bearing"])
    except (KeyError, TypeError, ValueError):
        return None
    return round(abs((heading - bearing + 180.0) % 360.0 - 180.0), 1)


def read(obs: dict, act: dict, fire_range_km: float = FIRE_RANGE_KM,
         break_range_km: float = BREAK_RANGE_KM) -> dict:
    """観測と行動から判断を組み立てる."""
    own = obs.get("own") or {}
    enemies = obs.get("enemies") or []
    threat = obs.get("threat") or {}
    target_row = act.get("target", {}).get("row")

    target = None
    aim = None
    off_nose = None
    if target_row and 0 < target_row <= len(enemies):
        target = enemies[target_row - 1]
        aim = observation.aim_point(own, target)
        off_nose = _off_nose(own, target)

    dist = target.get("dist") if target else None
    ammo = own.get("ammo")
    threat_flag = threat.get("flag")
    can_fire = bool(ammo and not threat_flag and dist is not None and dist <= fire_range_km)

    return {
        "target": target,
        "aim": {"x": round(aim[0], 1), "y": round(aim[1], 1)} if aim else None,
        "off_nose": off_nose,
        "ammo": ammo,
        "threat": threat_flag,
        "can_fire": can_fire,
        "break_zone": bool(dist is not None and dist <= break_range_km),
        "fire_range_km": fire_range_km,
        "break_range_km": break_range_km,
    }
