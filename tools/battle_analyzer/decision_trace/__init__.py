"""1フレームを機体ごとに 観測 / 判断 / 行動 に分ける解析。

分離の単位:
- observation.py … 観測。ログが持つ値だけ（own / enemies / threat）
- decision.py   … 判断。観測と行動から導出（標的・照準点・機首ずれ・撃てるか）
- action.py     … 行動。turn / speed / target を項目ごとに
- __init__.py   … 束ねるだけ。判定は持たない

        python tools/battle_analyzer/decision_trace.py <log> [frame]
"""

from __future__ import annotations

import json
from pathlib import Path

from . import action, decision, observation

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


def _ranges(config: dict) -> tuple[float, float]:
    """射撃判定の距離（fireRangeKm / breakRangeKm）。config ではなく args から取る."""
    fire = config.get("fireRangeKm", decision.FIRE_RANGE_KM)
    brk = config.get("breakRangeKm", decision.BREAK_RANGE_KM)
    try:
        fire = float(fire)
    except (TypeError, ValueError):
        fire = decision.FIRE_RANGE_KM
    try:
        brk = float(brk)
    except (TypeError, ValueError):
        brk = decision.BREAK_RANGE_KM
    return fire, brk


def build_frame(log_path: Path, frame_idx: int, config: dict | None = None,
                args: dict | None = None) -> dict:
    """1フレームを機体ごとに 観測/判断/行動 に分けて返す.

    config: agent/config.json（turnTable / speedTable の値）
    args:   agent/args.json（fireRangeKm / breakRangeKm など。判定に使う距離）
    """
    data = _load(log_path)
    obs_log = data.get("observations") or []
    act_log = data.get("actions") or []
    if not obs_log:
        return {"log": log_path.name, "frames": 0, "frame": 0, "aircraft": []}

    idx = max(0, min(int(frame_idx), len(obs_log) - 1))
    o_entry = obs_log[idx]
    a_entry = act_log[idx] if idx < len(act_log) else {}
    o_data = o_entry.get("data", {}) if isinstance(o_entry, dict) else {}
    a_data = a_entry.get("data", {}) if isinstance(a_entry, dict) else {}
    turn_table, speed_table = _tables(config or {})
    fire_range, break_range = _ranges(args or {})

    aircraft = []
    for slot in sorted(o_data.keys()):
        payload = o_data.get(slot)
        if not isinstance(payload, dict):
            continue
        obs = observation.read(payload)
        act = action.read(a_data.get(slot) or {}, turn_table, speed_table)
        dec = decision.read(obs, act, fire_range, break_range)
        aircraft.append({
            "slot": slot,
            "observation": obs,
            "decision": dec,
            "action": act,
        })

    return {
        "log": log_path.name,
        "log_path": log_path.as_posix(),
        "frames": len(obs_log),
        "frame": idx,
        "ptime": o_entry.get("ptime") if isinstance(o_entry, dict) else None,
        "aircraft": aircraft,
    }


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="decision_trace")
    ap.add_argument("log", help="log_*.json")
    ap.add_argument("frame", nargs="?", type=int, default=0)
    args = ap.parse_args(argv)
    config = {}
    cfg_path = Path(__file__).resolve().parents[2] / "agent" / "config.json"
    if cfg_path.exists():
        config = json.loads(cfg_path.read_text(encoding="utf-8"))
    out = build_frame(Path(args.log), args.frame, config)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
