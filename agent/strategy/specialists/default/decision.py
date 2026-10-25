import numpy as np

from .action import nearest_turn_index


def _nearest_turn_index(desired_az, num_turn):
    az = (desired_az + 180.0) % 360.0 - 180.0
    step = 360.0 / num_turn
    return int(round((az + 180.0) / step)) % num_turn


def decide(policy, observation, reward, done, info, agent_full_name, observation_space, action_space):
    own = np.asarray(observation["own"], dtype=np.float64)
    enemy = np.asarray(observation["enemy"], dtype=np.float64)
    threat = np.asarray(observation["threat"], dtype=np.float64)

    num_turn = int(action_space["turn"].n)
    num_speed = int(action_space["speed"].n)

    name = agent_full_name or ""
    policy._tick[name] = policy._tick.get(name, 0) + 1

    desired_az = 0.0
    speed_index = num_speed - 1
    target_index = 0

    detected = list(np.where(enemy[:, 0] > 0.5)[0])
    eligible = detected
    if policy.escort_max_speed_kmps > 0.0 and detected:
        eligible = [i for i in detected if float(enemy[i, 5]) <= policy.escort_max_speed_kmps]
    escort_candidate = None
    if policy.escort_forward_x_km > 0.0 and eligible:
        fwd = [
            (i, own[0] + enemy[i, 2] * np.cos(np.radians(enemy[i, 1])))
            for i in eligible
        ]
        cand_i, cand_x = max(fwd, key=lambda t: t[1])
        if cand_x >= policy.escort_forward_x_km:
            escort_candidate = cand_i
    elif policy.escort_seek_dist_km > 0 and eligible:
        far = [i for i in eligible if enemy[i, 2] >= policy.escort_seek_dist_km]
        if far:
            escort_candidate = max(far, key=lambda i: enemy[i, 2])

    if len(detected) > 0:
        near = [i for i in detected if enemy[i, 2] <= policy.engage_range_km]
        escorted = [i for i in detected if enemy[i, 4] > 0.5]
        pool = near if len(near) > 0 else (escorted if len(escorted) > 0 else detected)
        pool_sorted = sorted(pool, key=lambda i: enemy[i, 2])

        if policy.target_spread > 0 and agent_full_name:
            offset = sum(ord(c) for c in agent_full_name) % policy.target_spread
            pick_idx = offset % len(pool_sorted)
        else:
            pick_idx = 0
        best = pool_sorted[pick_idx]
        best_dist = float(enemy[best, 2])

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
        if (
            policy.escort_no_beam > 0
            and escort_candidate is not None
            and best == escort_candidate
            and policy.beam_range_km > 0.0
            and best_dist <= policy.fire_range_km
        ):
            beam_allowed = False
        breaking = policy.break_range_km > 0.0 and best_dist <= policy.break_range_km
        if (
            policy.escort_ignore_break > 0
            and escort_candidate is not None
            and best == escort_candidate
            and best_dist <= policy.fire_range_km
        ):
            breaking = False
        if breaking:
            desired_az = enemy[best, 1] + 180.0
        elif policy.beam_range_km > 0.0 and best_dist <= policy.beam_range_km and beam_allowed:
            desired_az = enemy[best, 1] + 80.0
        else:
            desired_az = enemy[best, 1]

        speed_index = num_speed - 1
        track_ok = policy.track_confirm_frames <= 0 or policy._track_count >= policy.track_confirm_frames
        attack_role = policy.role_split <= 0 or (sum(ord(c) for c in name) % 4 == 0)
        tick = policy._tick[name]
        interval_ok = (
            policy.launch_interval_frames <= 0
            or name not in policy._last_fire
            or tick - policy._last_fire[name] >= policy.launch_interval_frames
        )
        fire_target = best
        if policy.escort_fire_mode > 0 and escort_candidate is not None:
            if float(enemy[escort_candidate, 2]) <= policy.fire_range_km:
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
        align_ok = policy.fire_align_deg <= 0.0 or off_nose <= policy.fire_align_deg
        if policy.burst_head_align_deg > 0.0 and burst_head:
            align_ok = align_ok and off_nose <= policy.burst_head_align_deg
        if (
            not breaking
            and escort_range_ok
            and float(enemy[fire_target, 2]) <= policy.fire_range_km
            and threat[0] < 0.5
            and track_ok
            and interval_ok
            and align_ok
            and ammo_hold_ok
            and attack_role
        ):
            target_index = int(fire_target) + 1
            policy._last_fire[name] = tick

        if (
            escort_candidate is not None
            and threat[0] < 0.5
            and not breaking
            and best_dist > policy.beam_range_km
        ):
            desired_az = enemy[escort_candidate, 1]
    else:
        desired_az = 0.0
        policy._last_target_xy = None
        policy._track_count = 0

    if threat[0] > 0.5:
        desired_az = threat[1] + 180.0 + policy.evade_crank_deg
        target_index = 0

    margin_side, margin_front, margin_back = own[5], own[6], own[7]
    if margin_front < policy.margin_km:
        desired_az = policy.margin_az_deg if own[1] < 0.0 else -policy.margin_az_deg
    elif margin_back < policy.margin_km:
        desired_az = 0.0
    if margin_side < policy.margin_km:
        desired_az = -60.0 if own[1] > 0.0 else 60.0

    return {
        "turn": nearest_turn_index(desired_az, num_turn),
        "speed": speed_index,
        "target": target_index,
    }
