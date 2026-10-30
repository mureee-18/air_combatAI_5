"""Policy (orchestrator) for the default specialist.

Wires the three layers together:
  1. Observation  → produced by ObservationMixin.makeObs() (strategy/observation/)
  2. Judgment     → judge() in strategy/judgment/judgment.py
  3. Execution    → execute() in strategy/execution/execution.py

Holds policy state (args, counters, track history) and delegates step()
to the judgment + execution layers.

Parameters are grouped by purpose:
  - Firing (射撃): fire range, beam/break, alignment, launch control, tracking
  - Evasion (回避): crank, threat evade, margin
  - Escort (護衛): seek, approach, fire control, flank
  - Role (役割): attack role enable, attacker slot mask
"""

from ASRCAISim1.policy import StandalonePolicy

from ...agents.escort_hunter import EscortHunterAgent
from ...execution import execute
from ...judgment import judge
from .config import get_model_config as load_model_config


class DefaultPolicy(StandalonePolicy):
    def __init__(self, args={}):
        super().__init__()
        args = args if args is not None else {}

        # --- Firing (射撃) ---
        self.fire_range_km = float(args.get("fireRangeKm", 50.0))
        self.engage_range_km = float(args.get("engageRangeKm", 60.0))
        self.break_range_km = float(args.get("breakRangeKm", 35.0))
        self.beam_range_km = float(args.get("beamRangeKm", 45.0))
        self.margin_az_deg = float(args.get("marginAzDeg", 120.0))
        self.track_confirm_frames = int(args.get("trackConfirmFrames", 0))
        self.max_simul_shot = int(args.get("maxSimulShot", 4))
        self.track_pos_tolerance_km = float(args.get("trackPosToleranceKm", 10.0))
        self.target_spread = int(args.get("targetSpread", 0))
        self.launch_interval_frames = int(args.get("launchIntervalFrames", 0))
        self.fire_align_deg = float(args.get("fireAlignDeg", 0.0))
        self.burst_head_align_deg = float(args.get("burstHeadAlignDeg", 0.0))
        self.beam_hold_while_armed = int(args.get("beamHoldWhileArmed", 0))
        self.beam_hold_frames = int(args.get("beamHoldFrames", 0))

        # --- Evasion (回避) ---
        self.evade_crank_deg = float(args.get("evadeCrankDeg", 0.0))
        self.evade_crank_threat_relative = int(args.get("evadeCrankThreatRelative", 0))
        self.evade_crank_by_aircraft = int(args.get("evadeCrankByAircraft", 0))
        self.evade_crank_threat_relative = int(args.get("evadeCrankThreatRelative", 0))
        self.evade_crank_by_aircraft = int(args.get("evadeCrankByAircraft", 0))
        self.margin_km = float(args.get("marginKm", 25.0))

        # --- Escort (護衛) ---
        self.escort_seek_dist_km = float(args.get("escortSeekDistKm", 0.0))
        self.escort_forward_x_km = float(args.get("escortForwardXKm", 0.0))
        self.escort_use_forward_x = int(args.get("escortUseForwardX", 0))
        self.escort_use_seek_dist = int(args.get("escortUseSeekDist", 0))
        self.escort_fire_enable = int(args.get("escortFireEnable", 0))
        self.escort_fire_max_km = float(args.get("escortFireMaxDistKm", 0.0))
        self.escort_max_speed_kmps = float(args.get("escortMaxSpeedKmps", 0.0))
        self.escort_ammo_hold = int(args.get("escortAmmoHold", 0))
        self.escort_no_beam = int(args.get("escortNoBeam", 0))
        self.escort_ignore_break = int(args.get("escortIgnoreBreak", 0))
        self.escort_reserve_msls = int(args.get("escortReserveMsls", 0))
        self.escort_fire_min_km = float(args.get("escortFireMinKm", 0.0))
        self.escort_flank_enable = int(args.get("escortFlankEnable", 0))
        self._flankDeg = float(args.get("escortFlankDeg", 0.0))
        self.flankFullDistKm = float(args.get("flankFullDistKm", 150.0))

        # --- Role (役割) ---
        # Role assignment is emergent from other variables (escortAmmoHold, etc.).
        # No dedicated mode switch; all aircraft can fire by default.

        # --- Internal state ---
        self._tick = {}
        self._last_fire = {}
        self._beam_hold_start = {}
        self._threat_evade_frames = {}
        self._last_target_xy = None
        self._track_count = 0

    def step(self, observation, reward, done, info, agent_full_name, observation_space, action_space):
        judgment = judge(self, observation, reward, done, info, agent_full_name,
                         observation_space, action_space)
        return execute(self, judgment, action_space)

    def get_agent_class(args={}):
        return EscortHunterAgent

    def get_policy(args={}):
        return DefaultPolicy(args)

    def get_model_config(args={}):
        return load_model_config(args)


# Module-level functions (required by specialist interface)
def get_agent_class(args={}):
    return EscortHunterAgent


def get_policy(args={}):
    return DefaultPolicy(args)


def get_model_config(args={}):
    return load_model_config(args)
