"""観測（observation）: ログがそのまま持つ値だけを読む。

判断（decision）や行動（action）は派生，所以このモジュールは派生しない。
- own: 自機の状態（位置・速度・姿勢・残弾・燃料・マージン）
- enemies: 敵の航跡（行ごとの距離・方位・高度・速度・護衛フラグ）
- threat: MWS の脅威（有無・方位）
"""

from __future__ import annotations

import math

OWN_FIELDS = (
    "x", "y", "alt", "speed", "heading",
    "marginSide", "marginFront", "marginBack", "ammo", "fuel",
)
ENEMY_FIELDS = ("det", "bearing", "dist", "alt", "escort", "speed")
THREAT_FIELDS = ("flag", "bearing")


def _num(values, index, digits=1):
    try:
        v = float(values[index])
    except (IndexError, TypeError, ValueError):
        return None
    return round(v, digits)


def read_own(own: list) -> dict:
    """自機の観測値."""
    out = {}
    for i, name in enumerate(OWN_FIELDS):
        digits = 0 if name in ("ammo", "fuel") else 1
        out[name] = _num(own or [], i, digits)
    return out


def read_enemies(rows: list) -> list[dict]:
    """敵の観測値（行番号順）."""
    out = []
    for i, row in enumerate(rows or []):
        out.append({
            "row": i + 1,
            "det": _num(row, 0, 0),
            "bearing": _num(row, 1),
            "dist": _num(row, 2),
            "alt": _num(row, 3),
            "escort": _num(row, 4, 0),
            "speed": _num(row, 5, 2),
        })
    return out


def read_threat(threat: list) -> dict:
    """脅威の観測値."""
    return {
        "flag": _num(threat or [], 0, 0),
        "bearing": _num(threat or [], 1),
    }


def read(payload: dict) -> dict:
    """1機体分の観測をまとめる."""
    return {
        "own": read_own(payload.get("own") or []),
        "enemies": read_enemies(payload.get("enemy") or []),
        "threat": read_threat(payload.get("threat") or []),
    }


def aim_point(own: dict, target: dict):
    """照準点（標的の現在位置）。判定（decision）側で使う補助.

    own は read_own の結果（整形済み dict）、target は read_enemies の結果。
    """
    try:
        ox, oy = float(own["x"]), float(own["y"])
        dist, brg = float(target["dist"]), float(target["bearing"])
    except (KeyError, TypeError, ValueError):
        return None
    return (ox + dist * math.cos(math.radians(brg)),
            oy + dist * math.sin(math.radians(brg)))
