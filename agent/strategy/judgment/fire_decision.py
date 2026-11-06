"""Judgment sub-task: fire decision (判断層 — 射撃判断).

Decides whether and at whom to fire.
"""

# 同一目標への発射上限を数える窓（フレーム）。ミサイルの飛翔時間の近似。
PER_TARGET_WINDOW_FRAMES = 60


def decide_fire(policy, own, enemy, best, best_dist, escort_candidate,
                breaking, name, tick, off_nose, threat_active):
    """Decide whether and whom to fire at.

    Returns the 0-based enemy slot to fire at, or None.
    """
    # launch stagger: per-slot fire delay to create temporal separation
    stagger = int(getattr(policy, "launchStaggerFrames", 0))
    if stagger > 0:
        slot = getattr(policy, "_slot_index", {}).get(name, 0)
        if policy._tick.get(name, 0) < slot * stagger:
            return None
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
    # Role assignment is now emergent from other variables (escortAmmoHold, etc.).
    # All aircraft can fire by default; role split is achieved by combining
    # per-behavior toggles rather than a dedicated mode switch.
    track_ok = (
        (policy.track_confirm_frames <= 0 and policy._track_count >= 1)
        or policy._track_count >= policy.track_confirm_frames
    )

    fire_target = best
    # Escort priority fire: when enabled, prioritize escort target within fire range
    if getattr(policy, "escort_priority_fire", 0) > 0 and escort_candidate is not None:
        if float(enemy[escort_candidate, 2]) <= policy.fire_range_km:
            fire_target = escort_candidate
    if policy.escort_fire_max_km != 0.0 and escort_candidate is not None:
        max_dist = abs(policy.escort_fire_max_km) if policy.escort_fire_max_km > 0.0 else policy.fire_range_km
        if float(enemy[escort_candidate, 2]) <= max_dist:
            fire_target = escort_candidate

    # Adaptive ammo hold: probability-based instead of binary
    # When escort candidate is the target, always allow (escort priority)
    # Otherwise, hold fire probabilistically based on distance to escort target
    if escort_candidate is not None and fire_target == escort_candidate:
        ammo_hold_ok = True
    elif policy.escort_ammo_hold_dist_km <= 0.0:
        ammo_hold_ok = True
    else:
        # Sigmoid: closer escort target = higher hold probability
        if escort_candidate is not None:
            dist_to_escort = float(enemy[escort_candidate, 2])
            threshold = policy.escort_ammo_hold_dist_km
            # Linear probability: hold if dist < threshold, with gradual transition
            hold_prob = max(0.0, min(1.0, 1.0 - dist_to_escort / (threshold + 1.0)))
            import random
            ammo_hold_ok = random.random() > hold_prob
        else:
            ammo_hold_ok = True
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

    # 同一目標への発射上限（0=無効）。
    # ミサイルごとの目標は観測できないため、「直近 PER_TARGET_WINDOW_FRAMES に
    # 同じ目標へ出した発射指示の数」で飛翔中の本数を近似する。
    max_per_target = int(getattr(policy, "max_simul_per_target", 0))
    per_target_ok = True
    if max_per_target > 0:
        hist = policy._shot_hist.setdefault(name, {}).setdefault(fire_target, [])
        hist[:] = [t for t in hist if tick - t < PER_TARGET_WINDOW_FRAMES]
        per_target_ok = len(hist) < max_per_target

    burst_head = name not in policy._last_fire or tick - policy._last_fire[name] > 4
    # Adaptive fire alignment: looser at far range, stricter at close range
    if policy.fire_align_deg <= 0.0:
        effective_align = 90.0  # default: allow up to 90 deg off-nose
    else:
        # Scale alignment threshold with distance: farther = looser
        dist_factor = 1.0 + float(enemy[fire_target, 2]) / 100.0
        effective_align = policy.fire_align_deg * dist_factor
    align_ok = off_nose <= effective_align
    if policy.burst_head_align_deg > 0.0 and burst_head:
        # Adaptive: looser at far range
        dist_factor = 1.0 + float(enemy[fire_target, 2]) / 100.0
        effective_burst_align = policy.burst_head_align_deg * dist_factor
        align_ok = align_ok and off_nose <= effective_burst_align

    if (
        not breaking
        and escort_range_ok
        and float(enemy[fire_target, 2]) <= policy.fire_range_km
        and track_ok
        and interval_ok
        and align_ok
        and ammo_hold_ok
        and per_target_ok
        ):
        policy._last_fire[name] = tick
        if max_per_target > 0:
            policy._shot_hist.setdefault(name, {}).setdefault(fire_target, []).append(tick)
        return fire_target
    return None
