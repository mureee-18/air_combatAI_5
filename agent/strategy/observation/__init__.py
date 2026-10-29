"""Observation layer (観測層).

Gathers sensor data, builds the structured observation, manages track history
and escort identification.  Produces the world model consumed by the judgment
layer.
"""

from .mixin import ObservationMixin
from .escort_id import EscortIdentifier, racetrack_intercept

__all__ = ["ObservationMixin", "EscortIdentifier", "racetrack_intercept"]
