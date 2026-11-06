import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARGS = ROOT / "agent" / "args.json"
BASELINE = ROOT / "analysis" / "tools" / "baseline_args.json"
MECHANISMS = ROOT / "analysis" / "tools" / "mechanisms.json"

DEFAULT_BASELINE = {
    "type": "Fixed",
    "specialist": "default",
    "fireRangeKm": 50.0,
    "breakRangeKm": 35.0,
    "fireAlignDeg": 0.0,
    "burstHeadAlignDeg": 0.0,
    "beamHoldFrames": 0,
    "trackConfirmFrames": 0,
    "targetSpread": 0,
    "launchIntervalFrames": 0,
    "maxSimulShot": 4,
    "evadeCrankDeg": 0.0,
    "evadeCrankBlend": 0.0,
    "marginKm": 25.0,
    "escortSeekDistKm": 150,
    "escortForwardXKm": 110,
    "escortFireMaxDistKm": 0.0,
    "escortMaxSpeedKmps": 0.3,
    "escortAmmoHoldDistKm": 0.0,
    "escortNoBeamDistKm": 0.0,
    "escortIgnoreBreakDistKm": 0.0,
    "escortReserveMsls": 3,
    "escortFireMinKm": 35.0,
    "escortFlankDeg": 0.0,
}


def load_baseline():
    if BASELINE.exists():
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    return DEFAULT_BASELINE


def load_mechanisms():
    if MECHANISMS.exists():
        data = json.loads(MECHANISMS.read_text(encoding="utf-8"))
        return data.get("mechanisms", {})
    return {}


def key_to_mechanism(key, mechanisms):
    for mech, keys in mechanisms.items():
        if key in keys:
            return mech
    return key  # unregistered key = its own mechanism


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

    print(f"changed keys: {len(changed)}")
    for key, old, new in changed:
        print(f"  {key}: {old} -> {new}")

    mechanisms = load_mechanisms()
    mech_groups = {}
    for key, old, new in changed:
        mech = key_to_mechanism(key, mechanisms)
        mech_groups.setdefault(mech, []).append(key)

    print(f"changed mechanisms: {len(mech_groups)}")
    for mech, keys in mech_groups.items():
        print(f"  {mech}: {', '.join(keys)}")

    if args.strict:
        if len(changed) == 0:
            print("ERROR: no variable changed; validate is meaningless")
            return 2
        if len(mech_groups) > 1:
            print("ERROR: more than one mechanism changed; isolate before validate")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
