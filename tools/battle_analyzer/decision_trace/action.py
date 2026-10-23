"""行動（action）: ログが持つ turn・speed・target を読む。

1機体は1フレームに1つの行動を出すが、行動の中身（姿勢・速度・標的）は
別々の項目なので項目ごとに分ける。index を値に直すときの表は
config.json の turnTable / speedTable。
"""

from __future__ import annotations

TURN_TABLE = "turnTable"
SPEED_TABLE = "speedTable"


def _entry(index, table, table_name, unit):
    value = table[index] if 0 <= index < len(table) else None
    return {
        "index": index,
        "value": value,
        "unit": unit,
        "table": table_name,
    }


def read_turn(action: dict, turn_table: list) -> dict:
    return _entry(int(action.get("turn", 0) or 0), turn_table, TURN_TABLE, "°")


def read_speed(action: dict, speed_table: list) -> dict:
    return _entry(int(action.get("speed", 0) or 0), speed_table, SPEED_TABLE, "m/s")


def read_target(action: dict) -> dict:
    row = int(action.get("target", 0) or 0)
    return {"row": row or None, "index": row, "unit": "行"}


def read(action: dict, turn_table: list, speed_table: list) -> dict:
    """1機体分の行動。turn / speed / target を別々に持つ."""
    return {
        "turn": read_turn(action, turn_table),
        "speed": read_speed(action, speed_table),
        "target": read_target(action),
    }
