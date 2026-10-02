"""対戦ログ (log_{n}.json) から自陣営エージェントの挙動指標を集計する.

Usage:
    python tools/battle_analyzer/battle_stats.py workspace/results/0/log_0.json
"""

import json
import sys
from pathlib import Path


def collect(log_path: Path):
    d = json.loads(log_path.read_text())
    obs = d["observations"]
    acts = d["actions"]

    agent_ids = sorted(obs[0]["data"].keys())
    stats = {
        a: {"enemy": 0, "threat": 0, "fire": 0, "escorted": 0, "minDist": None, "mslsMin": None, "turns": {}}
        for a in agent_ids
    }

    for o, a in zip(obs, acts):
        for ag in agent_ids:
            payload = o["data"].get(ag)
            if not isinstance(payload, dict) or "enemy" not in payload:
                continue
            own = payload["own"]
            e = payload["enemy"]
            th = payload["threat"]
            detected = [row for row in e if row[0] > 0.5]
            if detected:
                stats[ag]["enemy"] += 1
                dmin = min(row[2] for row in detected)
                if stats[ag]["minDist"] is None or dmin < stats[ag]["minDist"]:
                    stats[ag]["minDist"] = dmin
                if any(row[4] > 0.5 for row in detected):
                    stats[ag]["escorted"] += 1
            if th[0] > 0.5:
                stats[ag]["threat"] += 1
            if len(own) > 8 and own[8] is not None:
                if stats[ag]["mslsMin"] is None or own[8] < stats[ag]["mslsMin"]:
                    stats[ag]["mslsMin"] = own[8]
            act = a["data"][ag]
            if int(act["target"]) > 0:
                stats[ag]["fire"] += 1
            stats[ag]["turns"][int(act["turn"])] = stats[ag]["turns"].get(int(act["turn"]), 0) + 1

    return len(obs), stats


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    steps, stats = collect(Path(sys.argv[1]))
    print(f"steps: {steps}")
    for ag, s in sorted(stats.items()):
        top_turns = sorted(s["turns"].items(), key=lambda kv: -kv[1])[:5]
        print(
            f"agent {ag}: enemy_seen={s['enemy']} threat={s['threat']} fire_orders={s['fire']} "
            f"escorted_seen={s['escorted']} min_dist_km={s['minDist']} min_rmsls={s['mslsMin']} "
            f"top_turns={top_turns}"
        )


if __name__ == "__main__":
    main()
