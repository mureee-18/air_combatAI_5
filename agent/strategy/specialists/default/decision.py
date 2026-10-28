"""Backward-compatible wrapper.

The judgment and execution logic has been split into ``judgment.py`` and
``execution.py``.  This module re-exports a ``decide`` function that
combines both layers, so existing callers (tests, other specialists) keep
working.
"""

from ...execution import execute
from ...judgment import judge


def decide(policy, observation, reward, done, info, agent_full_name,
           observation_space, action_space):
    judgment = judge(policy, observation, reward, done, info, agent_full_name,
                     observation_space, action_space)
    return execute(policy, judgment, action_space)
