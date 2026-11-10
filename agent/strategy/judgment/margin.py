"""Judgment sub-task: margin adjustments (判断層 — マージン調整).

Applies boundary-margin corrections to the desired heading.
"""


def apply_margin_adjustment(policy, own, j) -> None:
    """Adjust j.desired_heading_deg based on boundary margins (in-place)."""
    margin_side, margin_front, margin_back = own[5], own[6], own[7]
    if margin_front < policy.margin_km:
        j.desired_heading_deg = (policy.margin_az_deg if own[1] < 0.0
                                 else -policy.margin_az_deg)
    elif margin_back < policy.margin_km:
        j.desired_heading_deg = 0.0
    if margin_side < policy.margin_km:
        j.desired_heading_deg = -60.0 if own[1] > 0.0 else 60.0