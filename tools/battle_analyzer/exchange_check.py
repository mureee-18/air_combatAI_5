"""自機ログから攻防の交換比率を測り、どこで負けているかを示す.

敵の発射数はログに残らないため、MWS 警報の立ち上がり（0→1）を
「敵誘導弾の終末到達」の代理指標にする。自機の発射は残弾の減少で数える。
どちらも近似値。1機あたり・1戦あたりの表を作り、
「撃ち負け（終末到達数で劣勢）」か「かわし負け（到達弾の致死率高）」かを切り分ける。

Usage:
    python tools/battle_analyzer/exchange_check.py workspace/results/0/log_0.json
    python tools/battle_analyzer/exchange_check.py workspace/results_cur5/log_0.json --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from trajectory import build_frames, load_log  # noqa: E402


def exchange_stats(frames: list[dict]) -> dict:
    """フレーム列から交換比率を集計する（純粋関数）."""
    per_slot: dict[str, dict] = {}
    slots: dict[str, bool] = {}
    for index, frame in enumerate(frames or []):
        for slot in frame.get("own", {}):
            slots[slot] = True
        warns = {t.get("slot") for t in frame.get("threat", [])}
        for slot in list(slots):
            st = per_slot.setdefault(
                slot, {"warn_frames": 0, "onsets": 0, "_warn": False, "last_seen": -1}
            )
            if slot in frame.get("own", {}):
                st["last_seen"] = index
            if slot in warns:
                st["warn_frames"] += 1
                if not st["_warn"]:
                    st["onsets"] += 1
                st["_warn"] = True
            else:
                st["_warn"] = False
    n = len(frames or [])
    for slot, st in per_slot.items():
        st["died"] = st["last_seen"] < n - 2 if n else False
        del st["_warn"]
    launches = sum(
        1
        for f in frames or []
        for e in f.get("events", [])
        if e.get("kind") == "launch"
    )
    onsets = sum(st["onsets"] for st in per_slot.values())
    deaths = sum(1 for st in per_slot.values() if st["died"])
    return {
        "frames": n,
        "slots": sorted(slots),
        "our_launches": launches,
        "enemy_onsets": onsets,
        "our_deaths": deaths,
        "per_slot": per_slot,
        "onsets_per_launch": round(onsets / launches, 2) if launches else None,
        "deaths_per_onset": round(deaths / onsets, 3) if onsets else None,
    }


def verdict(stats: dict) -> str:
    """どこで負けているかの一文判定."""
    launches = stats["our_launches"]
    onsets = stats["enemy_onsets"]
    deaths = stats["our_deaths"]
    if not launches and not onsets:
        return "双方とも撃っていない静かなゲーム。"
    parts = []
    if onsets and launches and onsets >= launches * 2:
        parts.append(
            f"撃ち負け：敵の終末到達 {onsets} に対し自機発射 {launches}。"
            "発射機会・タイミング軸で見る。"
        )
    if onsets and deaths and deaths / onsets >= 0.1:
        parts.append(
            f"かわし負け：到達弾 {onsets} に対し撃墜 {deaths}。"
            "回避・脅威下機動軸で見る。"
        )
    if launches and not onsets:
        parts.append("敵弾の終末到達なし。自機の一方的な射撃戦。")
    if not parts:
        parts.append("交換は互角圏内。勝敗は護衛対象機の撃墜で決まる。")
    return " ".join(parts)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="攻防の交換比率を測る")
    ap.add_argument("log", help="log_{n}.json のパス")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    log_path = Path(args.log)
    if not log_path.exists():
        raise SystemExit(f"ログが見つかりません: {args.log}")
    from trajectory import is_replayable

    if not is_replayable(log_path):
        raise SystemExit("このログは解析できません（自作 Agent のログのみ対象）")
    frames, _ = build_frames(load_log(log_path))
    stats = exchange_stats(frames)
    stats["log"] = log_path.as_posix()
    stats["verdict"] = verdict(stats)
    if args.json:
        print(json.dumps(stats, ensure_ascii=False))
        return 0
    print(f"ログ: {stats['log']} / {stats['frames']} フレーム")
    print(f"自機発射: {stats['our_launches']} / 敵終末到達: {stats['enemy_onsets']} / 自機撃墜: {stats['our_deaths']}")
    for slot in stats["slots"]:
        st = stats["per_slot"][slot]
        print(
            f"  {slot}号: 警報 {st['warn_frames']} / 到達 {st['onsets']} / "
            f"{'撃墜' if st['died'] else '生存'}"
        )
    print(f"判定: {stats['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
