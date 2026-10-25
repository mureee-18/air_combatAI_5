import argparse
import json
import math
import os
import sys

HIT_RADIUS_KM = 10.0
MISSILE_SPEED_KMS = 1.5
MISSILE_FLIGHT_MIN_SEC = 5.0
MISSILE_FLIGHT_MAX_SEC = 60.0
DETECT_MATCH_KM = 10.0
BURST_GAP_FRAMES = 3


def round_or_none(v, ndigits=1):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    try:
        return round(float(v), ndigits)
    except Exception:
        return None


def own_field(own_arr, name):
    # own: [x,y,alt,speed,heading,marginSide,marginFront,marginBack,remMsls,fuel]
    mapping = {
        "x": 0,
        "y": 1,
        "alt": 2,
        "speed": 3,
        "heading": 4,
        "marginSide": 5,
        "marginFront": 6,
        "marginBack": 7,
        "ammo": 8,
        "remMsls": 8,
        "fuel": 9,
    }
    idx = mapping.get(name)
    if idx is None or idx >= len(own_arr):
        return None
    try:
        return float(own_arr[idx])
    except Exception:
        return None


def enemy_field(e_arr, name):
    # enemy: [det,bearing,dist,alt,escort_flag,speed_km_s]
    mapping = {
        "det": 0,
        "bearing": 1,
        "dist": 2,
        "alt": 3,
        "escort_flag": 4,
        "speed": 5,
        "speed_km_s": 5,
    }
    idx = mapping.get(name)
    if idx is None or idx >= len(e_arr):
        return None
    try:
        return float(e_arr[idx])
    except Exception:
        return None


def enemy_point(own_arr, e_arr):
    dist = enemy_field(e_arr, "dist")
    brg = enemy_field(e_arr, "bearing")
    if dist is None or brg is None:
        return None
    ox = own_field(own_arr, "x") or 0.0
    oy = own_field(own_arr, "y") or 0.0
    rad = math.radians(brg)
    ex = ox + dist * math.cos(rad)
    ey = oy + dist * math.sin(rad)
    return {"x": ex, "y": ey, "dist": dist, "bearing": brg}


def load_log(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_escort_candidate_from_obs(escortForwardXKm, escortSeekDistKm, escortMaxSpeedKmps, own_arr, enemy_list):
    detected = []
    for i, e in enumerate(enemy_list or []):
        if enemy_field(e, "det") > 0.5:
            detected.append((i, e))
    if len(detected) == 0:
        return None
    eligible = detected
    if escortMaxSpeedKmps > 0.0:
        eligible = [
            (i, e)
            for i, e in detected
            if enemy_field(e, "speed") is not None and enemy_field(e, "speed") <= escortMaxSpeedKmps
        ]
    if len(eligible) == 0:
        eligible = detected
    if escortForwardXKm > 0.0:
        fwd_list = []
        ox = own_field(own_arr, "x") or 0.0
        for i, e in eligible:
            dist = enemy_field(e, "dist") or 0.0
            brg = enemy_field(e, "bearing") or 0.0
            cx = ox + dist * math.cos(math.radians(brg))
            fwd_list.append((i, cx))
        if len(fwd_list) == 0:
            return None
        cand_i, cand_x = max(fwd_list, key=lambda t: t[1])
        if cand_x >= escortForwardXKm:
            return cand_i
        return None
    if escortSeekDistKm > 0:
        far = [(i, e) for i, e in eligible if (enemy_field(e, "dist") or 0.0) >= escortSeekDistKm]
        if far:
            far_sorted = sorted(far, key=lambda t: enemy_field(t[1], "dist") or 0.0, reverse=True)
            return far_sorted[0][0]
    # fallback: nearest? but keep consistent with code logic? code falls through
    # prefer far if seek set, else closest in some cases not used
    return None


def extract_launches(d):
    obs_list = d.get("observations", [])
    act_list = d.get("actions", [])
    frames = []
    launches = []
    previous_ammo = {}
    aim_by_slot = {}
    for index, (o_entry, a_entry) in enumerate(zip(obs_list, act_list)):
        ptime = o_entry.get("ptime") if isinstance(o_entry, dict) else None
        if ptime is None and isinstance(o_entry, dict):
            ptime = o_entry.get("time")
        payload = o_entry.get("data", {}) if isinstance(o_entry, dict) else {}
        a_payload = a_entry.get("data", {}) if isinstance(a_entry, dict) else {}
        frame = {
            "t": index,
            "ptime": ptime,
            "own": {},
            "aim": [],
            "events": [],
        }
        for slot_key, own_arr in payload.items():
            if not isinstance(own_arr, dict):
                continue
            own_data = own_arr.get("own")
            if own_data is None:
                continue
            frame["own"][slot_key] = {
                "x": round_or_none(own_field(own_data, "x")),
                "y": round_or_none(own_field(own_data, "y")),
                "alt": round_or_none(own_field(own_data, "alt")),
                "speed": round_or_none(own_field(own_data, "speed"), 2),
                "heading": round_or_none(own_field(own_data, "heading"), 2),
                "ammo": round_or_none(own_field(own_data, "ammo"), 0),
                "fuel": round_or_none(own_field(own_data, "fuel"), 0),
            }
            action = a_payload.get(slot_key) or {}
            target = int(action.get("target", 0) or 0)
            enemy_list = own_arr.get("enemy") or []
            if 0 < target <= len(enemy_list):
                point = enemy_point(own_data, enemy_list[target - 1])
                if point:
                    aim = {"slot": slot_key, "row": target}
                    aim.update(point)
                    frame["aim"].append(aim)
                    aim_by_slot[slot_key] = aim
            ammo = own_field(own_data, "ammo")
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
                        launch.update({"tx": aim["x"], "ty": aim["y"], "dist": aim["dist"], "target_row": aim["row"]})
                        launch["flight"] = max(
                            MISSILE_FLIGHT_MIN_SEC,
                            min(MISSILE_FLIGHT_MAX_SEC, float(aim["dist"] or 0.0) / MISSILE_SPEED_KMS),
                        )
                    else:
                        launch.update({"tx": None, "ty": None, "dist": None, "target_row": None})
                        launch["flight"] = MISSILE_FLIGHT_MAX_SEC
                    launches.append(launch)
                previous_ammo[slot_key] = ammo
        frames.append(frame)
    return frames, group_bursts(launches)


def group_bursts(launches):
    """近い時刻の発射をバースト（一斉射撃）としてグループ化し、最初の弾をマークする。"""
    if not launches:
        return launches
    ordered = sorted(launches, key=lambda launch: (launch["t"], str(launch.get("slot", ""))))
    burst_id = -1
    prev_burst_start_t = None
    current_burst = []

    def flush(burst):
        nonlocal burst_id, prev_burst_start_t
        burst_id += 1
        start_t = burst[0]["t"]
        for i, launch in enumerate(burst):
            launch["burst_id"] = burst_id
            launch["burst_index"] = i
            launch["is_burst_head"] = (i == 0)
            launch["burst_size"] = len(burst)
            launch["burst_start_t"] = start_t
            launch["frames_since_prev_burst"] = None if prev_burst_start_t is None else start_t - prev_burst_start_t
        prev_burst_start_t = start_t

    for launch in ordered:
        t = launch["t"]
        if current_burst and (t - current_burst[-1]["t"]) > BURST_GAP_FRAMES:
            flush(current_burst)
            current_burst = []
        current_burst.append(launch)
    if current_burst:
        flush(current_burst)
    return launches


def attach_impact(frames, launches, d):
    if not launches:
        return launches
    for launch in launches:
        if launch.get("tx") is None:
            launch["outcome"] = "unknown"
            launch["outcome_source"] = "no_aim"
            continue
        end_t = int(launch["t"] + float(launch.get("flight") or 0))
        end_t = max(0, min(end_t, len(frames) - 1))
        frame = frames[end_t]
        tx, ty = launch["tx"], launch["ty"]
        best = None
        for side_name, team_list in (frame.get("teams") or {}).items():
            if side_name != "enemy":
                continue
            for team in team_list:
                if not team.get("alive", True):
                    continue
                dx = team["x"] - tx
                dy = team["y"] - ty
                dkm = math.hypot(dx, dy)
                if best is None or dkm < best[0]:
                    best = (dkm, team.get("id"))
        if best is None:
            # fallback scan enemies_direct? not needed
            launch["outcome"] = "miss"
            launch["outcome_source"] = "no_enemy"
            launch["dist_at_impact_est"] = None
            continue
        launch["dist_at_impact_est"] = round_or_none(best[0], 2)
        if best[0] <= HIT_RADIUS_KM:
            launch["outcome"] = "hit"
            launch["outcome_source"] = "trajectory"
            launch["hit_enemy_id"] = best[1]
        else:
            launch["outcome"] = "miss"
            launch["outcome_source"] = "trajectory"
            launch["hit_enemy_id"] = best[1]


def enrich_launches(launches, d, frames):
    obs_list = d.get("observations", [])
    for launch in launches:
        t = launch["t"]
        if t < 0 or t >= len(obs_list):
            continue
        o_entry = obs_list[t]
        payload = o_entry.get("data", {}) if isinstance(o_entry, dict) else {}
        slot = launch["slot"]
        own_arr_dict = payload.get(slot) or {}
        own_data = own_arr_dict.get("own")
        enemy_list = own_arr_dict.get("enemy") or []
        if own_data is not None:
            launch["shooter"] = slot
            launch["own_speed_kmps"] = round_or_none(own_field(own_data, "speed"), 2)
            launch["own_heading"] = round_or_none(own_field(own_data, "heading"), 2)
            launch["ammo_before"] = round_or_none(own_field(own_data, "ammo"), 0)
        target_row = launch.get("target_row")
        if target_row and 0 < target_row <= len(enemy_list):
            e_arr = enemy_list[target_row - 1]
            launch["target_id"] = get_enemy_id_at(d, frames, t, target_row, e_arr)
            launch["target_speed_kmps"] = round_or_none(enemy_field(e_arr, "speed"), 2)
            launch["target_dist_at_launch"] = round_or_none(enemy_field(e_arr, "dist"), 2)
            brg_e = enemy_field(e_arr, "bearing")
            hdg_o = own_field(own_data, "heading") if own_data is not None else None
            if brg_e is not None and hdg_o is not None:
                off = abs((hdg_o - brg_e + 180.0) % 360.0 - 180.0)
                launch["off_nose"] = round_or_none(off, 2)
        # escort candidate
        if own_data is not None:
            cand = is_escort_candidate_from_obs(
                escortForwardXKm=110,
                escortSeekDistKm=150,
                escortMaxSpeedKmps=0.3,
                own_arr=own_data,
                enemy_list=enemy_list,
            )
            launch["escort_candidate"] = (cand == (target_row - 1)) if target_row else False
            launch["escort_candidate_row"] = cand + 1 if cand is not None else None
            launch["is_escort_target"] = launch["escort_candidate"]
        else:
            launch["is_escort_target"] = False
        # threat
        threat_arr = own_arr_dict.get("threat") if isinstance(own_arr_dict, dict) else None
        if isinstance(threat_arr, list) and len(threat_arr) > 0:
            launch["threat"] = round_or_none(threat_arr[0], 2)


def get_enemy_id_at(d, frames, t, target_row, e_arr):
    try:
        frame = frames[t] if t < len(frames) else None
        if frame:
            for team in frame.get("teams") or []:
                if team.get("side") != "enemy":
                    continue
                tid = team.get("id")
                if tid:
                    return tid
    except Exception:
        pass
    return f"E{target_row}"


def build_frames_for_ids(d):
    from tools.battle_analyzer import trajectory
    frames, _ = trajectory.build_frames(d)
    return frames


def burst_summary(launches):
    bursts = {}
    for launch in launches:
        bid = launch.get("burst_id")
        if bid is None:
            continue
        bursts.setdefault(bid, []).append(launch)
    if not bursts:
        return {
            "total_bursts": 0,
            "total_launches": len(launches),
            "avg_burst_size": 0.0,
            "max_burst_size": 0,
            "burst_head_total": 0,
            "burst_head_hits": 0,
            "burst_first_hit_rate": None,
            "burst_first_avg_off_nose": None,
            "burst_first_avg_dist": None,
            "avg_gap_between_bursts": None,
        }
    sizes = [len(v) for v in bursts.values()]
    heads = [v[0] for v in sorted(bursts.values(), key=lambda b: b[0]["t"])]
    head_hits = [h for h in heads if h.get("outcome") == "hit"]
    head_off = [h.get("off_nose") for h in heads if h.get("off_nose") is not None]
    head_dist = [h.get("target_dist_at_launch") for h in heads if h.get("target_dist_at_launch") is not None]
    starts = [h.get("burst_start_t") for h in heads if h.get("burst_start_t") is not None]
    gaps = []
    for i in range(1, len(starts)):
        gaps.append(starts[i] - starts[i - 1])
    return {
        "total_bursts": len(bursts),
        "total_launches": len(launches),
        "avg_burst_size": round(sum(sizes) / len(sizes), 2),
        "max_burst_size": max(sizes),
        "burst_head_total": len(heads),
        "burst_head_hits": len(head_hits),
        "burst_first_hit_rate": round(len(head_hits) / len(heads), 3) if heads else None,
        "burst_first_avg_off_nose": round(sum(head_off) / len(head_off), 2) if head_off else None,
        "burst_first_avg_dist": round(sum(head_dist) / len(head_dist), 2) if head_dist else None,
        "avg_gap_between_bursts": round(sum(gaps) / len(gaps), 1) if gaps else None,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Launch analyzer: per-launch stats")
    ap.add_argument("log", help="Path to log_0.json")
    ap.add_argument("--out", help="JSON output path")
    ap.add_argument("--summary", action="store_true", help="バースト統計サマリーも出力")
    args = ap.parse_args()
    d = load_log(args.log)
    frames, launches = extract_launches(d)
    attach_impact(frames, launches, d)
    enrich_launches(launches, d, frames)
    # output
    res = {
        "log": os.path.abspath(args.log),
        "launches": launches,
    }
    if args.summary:
        res["summary"] = burst_summary(launches)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
