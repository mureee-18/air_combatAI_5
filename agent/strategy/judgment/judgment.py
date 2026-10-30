"""Judgment layer (判断層) entry point.

Orchestrates the sub-judgments and produces a :class:`Judgment`.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

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
            if policy.beam_hold_while_armed > 0:
                beam_allowed = False
            elif policy.beam_hold_frames > 0:
                start = policy._beam_hold_start.setdefault(name, policy._tick[name])
                beam_allowed = (policy._tick[name] - start) >= policy.beam_hold_frames
            elif policy.fire_align_deg > 0.0:
                beam_allowed = off_nose <= policy.fire_align_deg
        else:
            policy._beam_hold_start.pop(name, None)
        if (policy.escort_no_beam > 0 and escort_candidate is not None
                and best == escort_candidate and policy.beam_range_km > 0.0
                and best_dist <= policy.fire_range_km):
            beam_allowed = False

        breaking = policy.break_range_km > 0.0 and best_dist <= policy.break_range_km
        if (policy.escort_ignore_break > 0 and escort_candidate is not None
                and best == escort_candidate and best_dist <= policy.fire_range_km):
            breaking = False
        j.breaking = breaking

        # navigation heading
        if (escort_candidate is not None and not breaking
                and best_dist > policy.beam_range_km):
            flank = 0.0
            flank_enable = getattr(policy, "escort_flank_enable", 0) > 0
            if flank_enable and policy._flankDeg != 0.0 and policy.flankFullDistKm > 0.0:
                dist = float(enemy[escort_candidate, 2])
                factor = min(max(dist / policy.flankFullDistKm, 0.0), 1.0)
                flank = policy._flankDeg * factor
            j.desired_heading_deg = enemy[escort_candidate, 1] + flank
        else:
            j.desired_heading_deg = navigate(policy, own, enemy, best, best_dist,
                                            escort_candidate, breaking, beam_allowed)

        # firing decision
        threat_active = bool(threat[0] > 0.5)
        fire_slot = decide_fire(
            policy, own, enemy, best, best_dist, escort_candidate,
            breaking, name, policy._tick[name], off_nose, threat_active,
        )
        if threat_active:
            fire_slot = None
        j.fire_target_slot = fire_slot

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
    if threat_detected and evading:
        base_az = threat[1] + 180.0
        crank = policy.evade_crank_deg
        if getattr(policy, "evade_crank_threat_relative", 0) > 0:
            # Crank away from threat based on which side it is on
            rel_bearing = (threat[1] - own[4] + 180.0) % 360.0 - 180.0
            crank_sign = 1.0 if rel_bearing >= 0 else -1.0
            crank = crank_sign * abs(crank)
        if getattr(policy, "evade_crank_by_aircraft", 0) > 0:
            slot = sum(ord(c) for c in name) % 4
            crank = crank + slot * 5.0
        j.desired_heading_deg = base_az + crank
        j.fire_target_slot = None

    # --- margin adjustments ---
    margin_side, margin_front, margin_back = own[5], own[6], own[7]
    if margin_front < policy.margin_km:
        j.desired_heading_deg = (policy.margin_az_deg if own[1] < 0.0
                                 else -policy.margin_az_deg)
    elif margin_back < policy.margin_km:
        j.desired_heading_deg = 0.0
    if margin_side < policy.margin_km:
        j.desired_heading_deg = -60.0 if own[1] > 0.0 else 60.0

    return j
