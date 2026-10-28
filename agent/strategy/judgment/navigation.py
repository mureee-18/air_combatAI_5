"""Judgment sub-task: navigation (判断層 — 航法).

Computes desired heading from target/break/evasion state.
"""


def navigate(policy, own, enemy, best, best_dist, escort_candidate,
            breaking, beam_allowed):
    """Compute desired heading (degrees)."""
    if best is None and escort_candidate is None:
        return 0.0
    if best is None:
        return float(enemy[escort_candidate, 1]) if escort_candidate is not None else 0.0

    bearing = enemy[best, 1]
    if breaking:
        return bearing + 180.0
    if policy.beam_range_km > 0.0 and best_dist <= policy.beam_range_km and beam_allowed:
        return bearing + 80.0
    return bearing
