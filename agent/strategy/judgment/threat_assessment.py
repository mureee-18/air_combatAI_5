"""Judgment sub-task: threat assessment (判断層 — 脅威評価).

Missile-warning (MWS) assessment and evasion decision.
"""


def assess_threat(policy, threat, name):
    """Assess missile-warning threat and decide whether to evade.

    Returns (threat_detected: bool, evading: bool).
    """
    threat_detected = bool(threat[0] > 0.5)
    if threat_detected:
        frames = policy._threat_evade_frames.get(name, 0) + 1
        policy._threat_evade_frames[name] = frames
        evading = (policy.threat_evade_max_frames <= 0
                   or frames <= policy.threat_evade_max_frames)
    else:
        policy._threat_evade_frames[name] = 0
        evading = False
    return threat_detected, evading
