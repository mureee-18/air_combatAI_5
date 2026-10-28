"""Execution layer (実行層) for the default specialist.

This module converts a :class:`~judgment.Judgment` into concrete action-space
indices and coordinates missile deployment.  It does NOT make decisions —
that is the judgment layer's responsibility.
"""

from ..specialists.default.action import nearest_turn_index


def execute(policy, judgment, action_space):
    """Execution layer: convert a Judgment into an action dict.

    Returns
    -------
    dict
        ``{"turn": int, "speed": int, "target": int}`` where *turn* is a turn-table
        index, *speed* a speed-table index, and *target* a 1-based enemy slot
        (0 = no fire).
    """
    num_turn = int(action_space["turn"].n)
    turn_index = nearest_turn_index(judgment.desired_heading_deg, num_turn)
    target_index = 0
    if judgment.fire_target_slot is not None:
        target_index = int(judgment.fire_target_slot) + 1
    return {
        "turn": turn_index,
        "speed": judgment.speed_index,
        "target": target_index,
    }
