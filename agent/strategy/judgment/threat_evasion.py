"""Judgment sub-task: threat evasion heading (判断層 — 脅威回避方位).

Computes the desired heading when a threat is detected.
"""
import math


def compute_threat_evasion_heading(policy, own, threat, name) -> float:
    """Return the desired heading (degrees) under threat evasion.

    Applies crank, blend, and weave based on policy parameters.
    Returns None if no evasion is needed (caller keeps current heading).
    """
    threat_dist = float(threat[2]) if len(threat) > 2 else 10.0
    dist_scale = max(0.0, min(1.0, 1.0 - threat_dist / 50.0))
    base_az = threat[1] + 180.0

    crank = policy.evade_crank_deg * dist_scale
    blend = getattr(policy, "evade_crank_blend", 0.0) * dist_scale
    if blend > 0.0:
        rel_bearing = (threat[1] - own[4] + 180.0) % 360.0 - 180.0
        crank_sign = 1.0 if rel_bearing >= 0 else -1.0
        crank = (1.0 - blend) * crank + blend * (crank_sign * abs(crank))

    weave = getattr(policy, "evade_weave_deg", 0.0) * dist_scale
    if weave != 0.0:
        period = getattr(policy, "evade_weave_period", 20.0)
        if period <= 0.0:
            period = 20.0
        tick = policy._tick.get(name, 0)
        phase = 2.0 * math.pi * tick / period
        crank += weave * math.sin(phase)

    return base_az + crank