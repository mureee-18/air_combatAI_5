"""Judgment layer (判断層).

Owns *what to do*: target selection, threat assessment, evasion, navigation,
and firing decisions.  Produces a Judgment describing the desired behaviour
in semantic terms.  Does NOT convert to action-space indices.
"""

from .fire_decision import decide_fire
from .judgment import Judgment, judge
from .navigation import navigate
from .target_selection import select_escort_candidate, select_primary_target
from .threat_assessment import assess_threat
from .track_history import update_track_history

__all__ = [
    "Judgment",
    "judge",
    "select_escort_candidate",
    "select_primary_target",
    "assess_threat",
    "update_track_history",
    "decide_fire",
    "navigate",
]
