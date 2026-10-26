import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARGS = ROOT / "agent" / "args.json"
BASELINE = ROOT / "analysis" / "tools" / "baseline_args.json"

DEFAULT_BASELINE = {
    "fireRangeKm": 50.0,
    "breakRangeKm": 35.0,
    "evadeCrankDeg": 0.0,
    "marginKm": 25.0,
    "trackConfirmFrames": 0,
    "targetSpread": 0,
    "escortSeekDistKm": 150,
    "escortForwardXKm": 110,
    "escortFireMode": 1,
    "escortMaxSpeedKmps": 0.3,
    "escortAmmoHold": 0,
    "escortNoBeam": 1,
    "escortIgnoreBreak": 1,
    "escortReserveMsls": 3,
    "escortFireMinKm": 35.0,
    "beamHoldWhileArmed": 0,
    "beamHoldFrames": 0,
    "fireAlignDeg": 0,
    "launchIntervalFrames": 0,
    "roleSplit": 0,
    "escortFlankDeg": 0.0,
    "threatEvadeMaxFrames": 0,
}


def load_baseline():
    if BASELINE.exists():
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    return DEFAULT_BASELINE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--lock", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    current = json.loads(ARGS.read_text(encoding="utf-8"))

    if args.lock:
        BASELINE.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"baseline locked: {BASELINE}")
        return 0

    baseline = load_baseline()
    changed = []
    for key in sorted(set(baseline) | set(current)):
        if key in ("type", "specialist"):
            continue
        if baseline.get(key) != current.get(key):
            changed.append((key, baseline.get(key), current.get(key)))

    print(f"changed variables: {len(changed)}")
    for key, old, new in changed:
        print(f"  {key}: {old} -> {new}")

    if args.strict:
        if len(changed) == 0:
            print("ERROR: no variable changed; validate is meaningless")
            return 2
        if len(changed) > 1:
            print("ERROR: more than one variable changed; isolate before validate")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
