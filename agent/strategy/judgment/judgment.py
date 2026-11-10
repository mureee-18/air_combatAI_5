"""Judgment layer (判断層) entry point.

Orchestrates the sub-judgments and produces a :class:`Judgment`.
"""
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .beam_break import compute_beam_break
from .escort_station import escort_station_heading
from .fire_decision import decide_fire
from .margin import apply_margin_adjustment
from .navigation import navigate
from .target_selection import select_escort_candidate, select_primary_target
from .threat_assessment import assess_threat
from .threat_evasion import compute_threat_evasion_heading
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
    # slot identity (0-based) for formation control.
    if not hasattr(policy, "_slot_index"):
        policy._slot_index = {}
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
    j.speed_index = int(action_space["speed"].n) - 1

    detected = list(np.where(enemy[:, 0] > 0.5)[0])
    j.detected_slots = detected

    # --- escort candidate ---
    escort_candidate = select_escort_candidate(policy, enemy, detected, own)
    j.escort_candidate_slot = escort_candidate

    # --- primary target + beam/break + navigation + firing ---
    if detected:
        best, best_dist = select_primary_target(policy, enemy, detected, name)
        j.primary_target_slot = best
        j.primary_target_dist_km = best_dist

        update_track_history(policy, own, enemy, best, best_dist)

        # beam / break
        beam_allowed, breaking = compute_beam_break(
            policy, own, enemy, best, best_dist, escort_candidate, name,
        )
        j.breaking = breaking

        # navigation heading
        policy._current_slot = policy._slot_index.get(name, 0)
        if (escort_candidate is not None and not breaking
                and best_dist > policy.beam_range_km):
            flank = 0.0
            if policy._flankDeg != 0.0 and policy.flankFullDistKm > 0.0:
                dist = float(enemy[escort_candidate, 2])
                factor = min(max(1.0 - dist / policy.flankFullDistKm, 0.0), 1.0)
                flank = policy._flankDeg * factor
            spread = getattr(policy, "formationSpreadDeg", 0.0)
            j.desired_heading_deg = enemy[escort_candidate, 1] + flank + (
                (0.0, spread, -spread, 2.0 * spread)[policy._current_slot % 4]
                if spread != 0.0 else 0.0
            )
        else:
            base_heading = navigate(policy, own, enemy, best, best_dist,
                                   escort_candidate, breaking, beam_allowed)
            spread = getattr(policy, "formationSpreadDeg", 0.0)
            if spread != 0.0:
                offsets = (0.0, spread, -spread, 2.0 * spread)
                base_heading = base_heading + offsets[policy._current_slot % 4]
            j.desired_heading_deg = base_heading

        # firing decision
        off_nose = abs((own[4] - enemy[best, 1] + 180.0) % 360.0 - 180.0)
        threat_active = bool(threat[0] > 0.5)
        fire_slot = decide_fire(
            policy, own, enemy, best, best_dist, escort_candidate,
            breaking, name, policy._tick[name], off_nose, threat_active,
        )
        if threat_active:
            fire_slot = None
        j.fire_target_slot = fire_slot

        # escort station keeping
        if (escort_candidate is not None and not breaking and not threat_active
                and j.fire_target_slot is None):
            station_heading = escort_station_heading(
                policy, enemy, escort_candidate, policy.beam_range_km)
            if station_heading is not None:
                j.desired_heading_deg = station_heading

        # formation spacing (maintain distance from nearest teammate)
        spacing = getattr(policy, "formationSpacingKm", 0.0)
        teammates = getattr(policy, "_teammates", {}) or {}
        if spacing > 0.0 and teammates:
            import math
            nearest_dist = None
            for tname, (tx, ty, _) in teammates.items():
                dx = tx - own[0]
                dy = ty - own[1]
                d = (dx * dx + dy * dy) ** 0.5
                if nearest_dist is None or d < nearest_dist:
                    nearest_dist = d
            if nearest_dist is not None and nearest_dist < spacing:
                vals = list(teammates.values())
                dx = vals[0][0] - own[0]
                dy = vals[0][1] - own[1]
                away = math.degrees(math.atan2(dy, dx)) + 180.0
                j.desired_heading_deg = away

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
        j.desired_heading_deg = compute_threat_evasion_heading(policy, own, threat, name)
        j.fire_target_slot = None
        if return_frames > 0:
            policy._evade_return_tick[name] = policy._tick.get(name, 0) + return_frames
            policy._last_evade_heading[name] = j.desired_heading_deg
    elif return_frames > 0 and policy._tick.get(name, 0) < policy._evade_return_tick.get(name, 0):
        j.evading = True
        j.desired_heading_deg = policy._last_evade_heading.get(name, j.desired_heading_deg)
        j.fire_target_slot = None

    # --- margin adjustments ---
    apply_margin_adjustment(policy, own, j)

    # --- lost ally speed boost ---
    boost = getattr(policy, "lostAllySpeedBoost", 0.0)
    teammates = getattr(policy, "_teammates", {}) or {}
    if boost > 0.0 and len(teammates) < 3:
        max_idx = int(action_space["speed"].n) - 1
        j.speed_index = min(max_idx, j.speed_index + int(boost))

    return j