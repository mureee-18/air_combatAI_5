"""Judgment sub-task: threat assessment (判断層 — 脅威評価).

Missile-warning (MWS) assessment and evasion decision.
"""


def assess_threat(policy, threat, name):
    """Assess missile-warning threat and decide whether to evade.

    Returns (threat_detected: bool, evading: bool).

    Evasion continues for the entire duration of the threat (hardcoded).
    threatEvadeMaxFrames has been removed; the agent always evades while
    a missile warning is active.
    """
    threat_detected = bool(threat[0] > 0.5)
    if threat_detected:
        evading = True
    else:
        evading = False
    return threat_detected, evading
