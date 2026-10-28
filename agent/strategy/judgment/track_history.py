"""Judgment sub-task: track history (判断層 — トラッキング).

Updates position-tracking counters used for track confirmation.
"""

import numpy as np


def update_track_history(policy, own, enemy, best, best_dist):
    """Update position-tracking counters for track confirmation."""
    if best is None:
        policy._last_target_xy = None
        policy._track_count = 0
        return
    bearing = enemy[best, 1]
    ex = own[0] + best_dist * np.cos(np.radians(bearing))
    ey = own[1] + best_dist * np.sin(np.radians(bearing))
    if policy._last_target_xy is not None:
        dx = ex - policy._last_target_xy[0]
        dy = ey - policy._last_target_xy[1]
        if np.hypot(dx, dy) <= policy.track_pos_tolerance_km:
            policy._track_count += 1
        else:
            policy._track_count = 1
    else:
        policy._track_count = 1
    policy._last_target_xy = (ex, ey)
