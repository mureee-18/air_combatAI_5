"""Judgment sub-task: beam / break decisions (判断層 — ビーム・ブレイク判断).

Computes beam_allowed and breaking flags from policy, observation, and target.
"""
from typing import Tuple


def compute_beam_break(policy, own, enemy, best, best_dist, escort_candidate,
                      name) -> Tuple[bool, bool]:
    """Return (beam_allowed, breaking).

    beam_allowed: whether beam (crank) maneuver is permitted this tick.
    breaking: whether to break (turn away) from the target.
    """
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

    # Adaptive beam suppression (escort candidate only)
    if (escort_candidate is not None
            and best == escort_candidate and policy.beam_range_km > 0.0
            and best_dist <= policy.fire_range_km
            and getattr(policy, "escort_no_beam_dist_km", 0.0) > 0.0):
        import math
        import random
        dist_to_escort = float(enemy[escort_candidate, 2])
        threshold = getattr(policy, "escort_no_beam_dist_km", 0.0)
        if threshold > 0.0:
            prob_suppress = 1.0 / (1.0 + math.exp((dist_to_escort - threshold) / 5.0))
            if random.random() < prob_suppress:
                beam_allowed = False

    breaking = policy.break_range_km > 0.0 and best_dist <= policy.break_range_km
    if (escort_candidate is not None
            and best == escort_candidate and best_dist <= policy.fire_range_km
            and getattr(policy, "escort_ignore_break_dist_km", 0.0) > 0.0):
        import math
        import random
        dist_to_escort = float(enemy[escort_candidate, 2])
        threshold = getattr(policy, "escort_ignore_break_dist_km", 0.0)
        if threshold > 0.0:
            prob_ignore = 1.0 / (1.0 + math.exp((dist_to_escort - threshold) / 5.0))
            if random.random() < prob_ignore:
                breaking = False

    return beam_allowed, breaking