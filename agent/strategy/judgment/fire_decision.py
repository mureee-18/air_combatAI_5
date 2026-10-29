"""Judgment sub-task: fire decision (判断層 — 射撃判断).

Decides whether and at whom to fire.
"""


def decide_fire(policy, own, enemy, best, best_dist, escort_candidate,
                breaking, name, tick, off_nose, threat_active):
    """Decide whether and whom to fire at.

    Returns the 0-based enemy slot to fire at, or None.
    """
    if breaking:
        return None
    if threat_active:
        return None
    if best is None:
        return None

    interval_ok = (
        policy.launch_interval_frames <= 0
        or name not in policy._last_fire
        or tick - policy._last_fire[name] >= policy.launch_interval_frames
    )
    if policy.attack_role_enable <= 0:
        attack_role = True
    else:
        slot = sum(ord(c) for c in name) % 4
        attack_role = bool(policy.attacker_slot_mask & (1 << slot))
    track_ok = (policy.track_confirm_frames <= 0 and policy._track_count >= 1) or policy._track_count >= policy.track_confirm_frames

    fire_target = best
    if policy.escort_fire_enable > 0 and escort_candidate is not None:
        max_dist = policy.escort_fire_max_km if policy.escort_fire_max_km > 0.0 else policy.fire_range_km
        if float(enemy[escort_candidate, 2]) <= max_dist:
            fire_target = escort_candidate

    ammo_hold_ok = (
        policy.escort_ammo_hold <= 0
        or (escort_candidate is not None and fire_target == escort_candidate)
    )
    if policy.escort_reserve_msls > 0 and not (
        escort_candidate is not None and fire_target == escort_candidate
    ):
        ammo_hold_ok = ammo_hold_ok and float(own[8]) > policy.escort_reserve_msls

    escort_range_ok = (
        policy.escort_fire_min_km <= 0.0
        or escort_candidate is None
        or fire_target != escort_candidate
        or float(enemy[escort_candidate, 2]) <= policy.escort_fire_min_km
    )

    burst_head = name not in policy._last_fire or tick - policy._last_fire[name] > 4
    align_ok = (policy.fire_align_deg <= 0.0 and off_nose <= 90.0) or off_nose <= policy.fire_align_deg
    if policy.burst_head_align_deg > 0.0 and burst_head:
        align_ok = align_ok and off_nose <= policy.burst_head_align_deg

    if (
        not breaking
        and escort_range_ok
        and float(enemy[fire_target, 2]) <= policy.fire_range_km
        and track_ok
        and interval_ok
        and align_ok
        and ammo_hold_ok
        and attack_role
    ):
        policy._last_fire[name] = tick
        return fire_target
    return None
