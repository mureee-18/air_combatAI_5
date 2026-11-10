"""Judgment sub-task: target selection (判断層 — 目標選択).

Selects the escort (high-value) candidate and the primary engagement target
from the detected enemy slots.
"""

import numpy as np


def select_escort_candidate(policy, enemy, detected, own):
    """Identify the escort (high-value) target among detected enemies.

    Uses threshold-based identification:
      - escortForwardXKm > 0: enable forward-x based identification
      - escortSeekDistKm > 0: enable seek-dist based identification
    When both thresholds are positive, forward-x takes priority.
    """
    if not detected:
        return None
    eligible = detected
    if policy.escort_max_speed_kmps > 0.0:
        eligible = [i for i in detected if float(enemy[i, 5]) <= policy.escort_max_speed_kmps]
    if not eligible:
        return None

    # Forward-x based identification (threshold-gated)
    if policy.escort_forward_x_km > 0.0:
        fwd = [
            (i, own[0] + enemy[i, 2] * np.cos(np.radians(enemy[i, 1])))
            for i in eligible
        ]
        cand_i, cand_x = max(fwd, key=lambda t: t[1])
        if cand_x >= policy.escort_forward_x_km:
            return cand_i

    # Seek-dist based identification (threshold-gated)
    if policy.escort_seek_dist_km > 0.0:
        far = [i for i in eligible if enemy[i, 2] >= policy.escort_seek_dist_km]
        if far:
            return max(far, key=lambda i: enemy[i, 2])

    return None


def select_primary_target(policy, enemy, detected, name):
    """Pick the primary engagement target from detected enemies."""
    if not detected:
        return None, 0.0
    near = [i for i in detected if enemy[i, 2] <= policy.engage_range_km]
    escorted = [i for i in detected if enemy[i, 4] > 0.5]
    pool = near if near else (escorted if escorted else detected)
    pool_sorted = sorted(pool, key=lambda i: enemy[i, 2])
    if not pool_sorted:
        return None, 0.0

    mode = int(getattr(policy, "target_spread_mode", 0))
    spread = int(getattr(policy, "target_spread", 0))

    if mode == 0:
        # concentrate: always nearest
        pick_idx = 0
    elif mode == 1:
        # probabilistic spread: spread/10 chance to pick a non-nearest target
        import random
        if spread > 0 and random.random() < (spread / 10.0):
            # round-robin by slot for coordinated spread
            slot = 0
            # derive slot from name hash
            slot = hash(name or "") % max(1, len(pool_sorted))
            pick_idx = slot % len(pool_sorted)
            if pick_idx == 0 and len(pool_sorted) > 1:
                pick_idx = 1
        else:
            pick_idx = 0
    elif mode == 2:
        # always spread: round-robin by slot
        slot = hash(name or "") % max(1, len(pool_sorted))
        pick_idx = slot % len(pool_sorted)
    else:
        pick_idx = 0

    best = pool_sorted[pick_idx]
    return best, float(enemy[best, 2])