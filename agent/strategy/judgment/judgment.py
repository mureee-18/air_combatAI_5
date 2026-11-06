"""Judgment layer (判断層) entry point.

Orchestrates the sub-judgments and produces a :class:`Judgment`.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .escort_station import escort_station_heading
from .fire_decision import decide_fire
from .navigation import navigate
from .target_selection import select_escort_candidate, select_primary_target
from .threat_assessment import assess_threat
from .track_history import update_track_history


@dataclass
class Judgment:
    """Semantic decision produced by the judgment layer."""
    desired_heading_deg: float = 0.0
    desired_speed_kmps: float = 0.0
    speed_index: int = 0
    fire_target_slot: Optional[int] = None
    breaking: bool = False
    evading: bool = False
    escort_candidate_slot: Optional[int] = None
    primary_target_slot: Optional[int] = None
    primary_target_dist_km: float = 0.0
    detected_slots: List[int] = field(default_factory=list)
    threat_detected: bool = False


def judge(policy, observation, reward, done, info, agent_full_name,
          observation_space, action_space):
    """Judgment layer entry point."""
    own = np.asarray(observation["own"], dtype=np.float64)
    enemy = np.asarray(observation["enemy"], dtype=np.float64)
    threat = np.asarray(observation["threat"], dtype=np.float64)

    name = agent_full_name or ""
    # slot identity (0-based) for formation control. Derived from the trailing
    # digit of the agent name (e.g. "Blue_1_3" -> slot 2). Falls back to a
    # per-policy counter if no digit is found.
    if not hasattr(policy, "_slot_index"):
        policy._slot_index = {}
        policy._next_slot = 0
    if name not in policy._slot_index:
        import re
        m = re.search(r"(\d+)\s*$", name)
        if m:
            policy._slot_index[name] = (int(m.group(1)) - 1) % 4
        else:
            policy._slot_index[name] = hash(name) % 4
    policy._tick[name] = policy._tick.get(name, 0) + 1

    j = Judgment()
    j.desired_heading_deg = 0.0
    j.desired_speed_kmps = 0.0
    j.speed_index = int(action_space["speed"].n) - 1

    detected = list(np.where(enemy[:, 0] > 0.5)[0])
    j.detected_slots = detected

    # --- escort candidate ---
    escort_candidate = select_escort_candidate(policy, enemy, detected, own)
    j.escort_candidate_slot = escort_candidate

    # --- primary target ---
    if detected:
        best, best_dist = select_primary_target(policy, enemy, detected, name)
        j.primary_target_slot = best
        j.primary_target_dist_km = best_dist

        update_track_history(policy, own, enemy, best, best_dist)

        # beam / break logic
        armed = own[8] > 0.5
        off_nose = abs((own[4] - enemy[best, 1] + 180.0) % 360.0 - 180.0)
        beam_allowed = True
        if armed and policy.beam_range_km > 0.0 and best_dist <= policy.beam_range_km:
            if policy.beam_hold_frames > 0:
                start = policy._beam_hold_start.setdefault(name, policy._tick[name])
                beam_allowed = (policy._tick[name] - start) >= policy.beam_hold_frames
            elif policy.fire_align_deg > 0.0:
                beam_allowed = off_nose <= policy.fire_align_deg
        else:
            policy._beam_hold_start.pop(name, None)
        if (escort_candidate is not None
                and best == escort_candidate and policy.beam_range_km > 0.0
                and best_dist <= policy.fire_range_km
                and getattr(policy, "escort_no_beam_dist_km", 0.0) > 0.0):
            # Adaptive beam suppression: probability-based instead of binary
            dist_to_escort = float(enemy[escort_candidate, 2])
            threshold = getattr(policy, "escort_no_beam_dist_km", 0.0)
            if threshold > 0.0:
                # Sigmoid: closer = higher suppression probability
                import math
                prob_suppress = 1.0 / (1.0 + math.exp((dist_to_escort - threshold) / 5.0))
                import random
                if random.random() < prob_suppress:
                    beam_allowed = False

        breaking = policy.break_range_km > 0.0 and best_dist <= policy.break_range_km
        if (escort_candidate is not None
                and best == escort_candidate and best_dist <= policy.fire_range_km
                and getattr(policy, "escort_ignore_break_dist_km", 0.0) > 0.0):
            # Adaptive break ignore: probability-based instead of binary
            dist_to_escort = float(enemy[escort_candidate, 2])
            threshold = getattr(policy, "escort_ignore_break_dist_km", 0.0)
            if threshold > 0.0:
                import math
                prob_ignore = 1.0 / (1.0 + math.exp((dist_to_escort - threshold) / 5.0))
                import random
                if random.random() < prob_ignore:
                    breaking = False
        j.breaking = breaking

        # navigation heading
        policy._current_slot = getattr(policy, "_slot_index", {}).get(name, 0)
        if (escort_candidate is not None and not breaking
                and best_dist > policy.beam_range_km):
            flank = 0.0
            if policy._flankDeg != 0.0 and policy.flankFullDistKm > 0.0:
                dist = float(enemy[escort_candidate, 2])
                # Inverse scaling: closer escort target = larger flank
                factor = min(max(1.0 - dist / policy.flankFullDistKm, 0.0), 1.0)
                flank = policy._flankDeg * factor
            spread = getattr(policy, "formationSpreadDeg", 0.0)
            j.desired_heading_deg = enemy[escort_candidate, 1] + flank + (
                (0.0, spread, -spread, 2.0 * spread)[getattr(policy, "_current_slot", 0) % 4]
                if spread != 0.0 else 0.0
            )
        else:
            # formation spread: slot-based heading offset to create lateral separation
            spread = getattr(policy, "formationSpreadDeg", 0.0)
            slot = getattr(policy, "_slot_index", {}).get(name, 0)
            if spread != 0.0:
                # slots 0,1,2,3 -> offsets 0, +spread, -spread, +2*spread (fan)
                offsets = (0.0, spread, -spread, 2.0 * spread)
                off = offsets[slot % 4]
            else:
                off = 0.0
            j.desired_heading_deg = navigate(policy, own, enemy, best, best_dist,
                                            escort_candidate, breaking, beam_allowed) + off

        # firing decision
        threat_active = bool(threat[0] > 0.5)
        fire_slot = decide_fire(
            policy, own, enemy, best, best_dist, escort_candidate,
            breaking, name, policy._tick[name], off_nose, threat_active,
        )
        if threat_active:
            fire_slot = None
        j.fire_target_slot = fire_slot

        # escort station keeping (護衛候補との距離保持。3変数とも 0=無効)
        # 射撃解がある tick・ブレイク中・脅威対応中は上書きしない。
        if (escort_candidate is not None and not breaking and not threat_active
                and j.fire_target_slot is None):
            station_heading = escort_station_heading(
                policy, enemy, escort_candidate, policy.beam_range_km)
            if station_heading is not None:
                j.desired_heading_deg = station_heading

        j.escort_candidate_slot = escort_candidate
    else:
        j.desired_heading_deg = 0.0
        policy._last_target_xy = None
        policy._track_count = 0
        j.primary_target_slot = None
        j.primary_target_dist_km = 0.0
        j.fire_target_slot = None

    # --- threat evasion ---
    threat_detected, evading = assess_threat(policy, threat, name)
    j.threat_detected = threat_detected
    j.evading = evading
    return_frames = int(getattr(policy, "evadeReturnFrames", 0))
    if threat_detected and evading:
        base_az = threat[1] + 180.0
        threat_dist = float(threat[2]) if len(threat) > 2 else 10.0
        dist_scale = max(0.0, min(1.0, 1.0 - threat_dist / 50.0))
        crank = policy.evade_crank_deg * dist_scale
        blend = getattr(policy, "evade_crank_blend", 0.0) * dist_scale
        if blend > 0.0:
            rel_bearing = (threat[1] - own[4] + 180.0) % 360.0 - 180.0
            crank_sign = 1.0 if rel_bearing >= 0 else -1.0
            crank = (1.0 - blend) * crank + blend * (crank_sign * abs(crank))
        weave = getattr(policy, "evade_weave_deg", 0.0) * dist_scale
        if weave != 0.0:
            import math
            period = getattr(policy, "evade_weave_period", 20.0)
            if period <= 0.0:
                period = 20.0
            tick = policy._tick.get(name, 0)
            phase = 2.0 * math.pi * tick / period
            crank += weave * math.sin(phase)
        j.desired_heading_deg = base_az + crank
        j.fire_target_slot = None
        if return_frames > 0:
            policy._evade_return_tick[name] = policy._tick.get(name, 0) + return_frames
            policy._last_evade_heading[name] = j.desired_heading_deg
    elif return_frames > 0 and policy._tick.get(name, 0) < policy._evade_return_tick.get(name, 0):
        # still in return window: keep evading
        j.evading = True
        j.desired_heading_deg = policy._last_evade_heading.get(name, j.desired_heading_deg)
        j.fire_target_slot = None

    # --- formation spacing (maintain distance from nearest teammate) ---
    spacing = getattr(policy, "formationSpacingKm", 0.0)
    teammates = getattr(policy, "_teammates", {}) or {}
    if spacing > 0.0 and teammates:
        import math
        # find nearest teammate
        nearest_dist = None
        for tname, (tx, ty, _) in teammates.items():
            dx = tx - own[0]
            dy = ty - own[1]
            d = (dx * dx + dy * dy) ** 0.5
            if nearest_dist is None or d < nearest_dist:
                nearest_dist = d
        if nearest_dist is not None and nearest_dist < spacing:
            # turn away from nearest teammate
            dx = list(teammates.values())[0][0] - own[0]
            dy = list(teammates.values())[0][1] - own[1]
            away = math.degrees(math.atan2(dy, dx)) + 180.0
            j.desired_heading_deg = away

    # --- lost ally speed boost ---
    boost = getattr(policy, "lostAllySpeedBoost", 0.0)
    if boost > 0.0 and len(teammates) < 3:
        max_idx = int(action_space["speed"].n) - 1
        j.speed_index = min(max_idx, j.speed_index + int(boost))

    return j
