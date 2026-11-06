"""Policy (orchestrator) for the default specialist.

Wires the three layers together:
  1. Observation  → produced by ObservationMixin.makeObs() (strategy/observation/)
  2. Judgment     → judge() in strategy/judgment/judgment.py
  3. Execution    → execute() in strategy/execution/execution.py

Holds policy state (args, counters, track history) and delegates step()
to the judgment + execution layers.

Parameters are grouped by purpose:
  - Firing (射撃): fire range, beam/break, alignment, launch control, tracking
  - Evasion (回避): crank, blend, margin
  - Escort (護衛): seek, approach, fire control, flank
"""

from ASRCAISim1.policy import StandalonePolicy

from ...agents.escort_hunter import EscortHunterAgent
from ...execution import execute
from ...judgment import judge
from .config import get_model_config as load_model_config


# ---------------------------------------------------------------------------
# Shared formation state (class-level across all aircraft in the same process).
# The sim runs all 4 aircraft in one Python process, so a module-level dict
# lets them observe each other's positions for formation control.
# ---------------------------------------------------------------------------
_formation_positions = {}   # name -> (x, y, tick)


def _report_formation_position(name: str, x: float, y: float, tick: int) -> None:
    _formation_positions[name] = (float(x), float(y), int(tick))
    stale = [k for k, v in _formation_positions.items() if tick - v[2] > 5]
    for k in stale:
        del _formation_positions[k]


def _formation_teammates(name: str) -> dict:
    return {k: v for k, v in _formation_positions.items() if k != name}


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
        self.track_pos_tolerance_km = float(args.get("trackPosToleranceKm", 10.0))
        self.fire_align_deg = float(args.get("fireAlignDeg", 0.0))
        self.burst_head_align_deg = float(args.get("burstHeadAlignDeg", 0.0))
        self.beam_hold_frames = int(args.get("beamHoldFrames", 0))
        self.track_confirm_frames = int(args.get("trackConfirmFrames", 0))
        self.target_spread = int(args.get("targetSpread", 0))
        self.launch_interval_frames = int(args.get("launchIntervalFrames", 0))
        self.max_simul_shot = int(args.get("maxSimulShot", 4))
        # 同一目標への発射上限（0=無効）。直近 PER_TARGET_WINDOW_FRAMES の発射履歴で近似する。
        self.max_simul_per_target = int(args.get("maxSimulPerTarget", 0))

        # --- Evasion (回避) ---
        self.evade_crank_deg = float(args.get("evadeCrankDeg", 0.0))
        self.evade_crank_blend = float(args.get("evadeCrankBlend", 0.0))
        self.evade_weave_deg = float(args.get("evadeWeaveDeg", 0.0))
        self.evade_weave_period = float(args.get("evadeWeavePeriod", 20.0))
        self.margin_km = float(args.get("marginKm", 25.0))

        # --- Escort (護衛) ---
        self.escort_seek_dist_km = float(args.get("escortSeekDistKm", 0.0))
        self.escort_forward_x_km = float(args.get("escortForwardXKm", 0.0))
        self.escort_fire_max_km = float(args.get("escortFireMaxDistKm", 0.0))
        self.escort_max_speed_kmps = float(args.get("escortMaxSpeedKmps", 0.0))
        self.escort_ammo_hold_dist_km = float(args.get("escortAmmoHoldDistKm", 0.0))
        self.escort_no_beam_dist_km = float(args.get("escortNoBeamDistKm", 0.0))
        self.escort_ignore_break_dist_km = float(args.get("escortIgnoreBreakDistKm", 0.0))
        self.escort_reserve_msls = int(args.get("escortReserveMsls", 0))
        self.escort_fire_min_km = float(args.get("escortFireMinKm", 0.0))
        self.escort_priority_fire = int(args.get("escortPriorityFire", 0))
        self._flankDeg = float(args.get("escortFlankDeg", 0.0))
        self.flankFullDistKm = float(args.get("flankFullDistKm", 150.0))
        # 護衛候補との距離保持（judgment/escort_station.py で使用。0=無効）
        self.escort_formation_km = float(args.get("escortFormationKm", 0.0))
        self.escort_trail_dist_km = float(args.get("escortTrailDistKm", 0.0))
        self.escort_lead_dist_km = float(args.get("escortLeadDistKm", 0.0))

        # --- Formation control variables (4-aircraft relative positioning) ---
        self.formationSpreadDeg = float(args.get("formationSpreadDeg", 0.0))
        self.launchStaggerFrames = int(args.get("launchStaggerFrames", 0))
        self.evadeReturnFrames = int(args.get("evadeReturnFrames", 0))
        self.formationSpacingKm = float(args.get("formationSpacingKm", 0.0))
        self.lostAllySpeedBoost = float(args.get("lostAllySpeedBoost", 0.0))
        # slot tracking: name -> 0-based slot index
        self._slot_index = {}
        self._next_slot = 0
        self._evade_return_tick = {}
        self._last_evade_heading = {}
        self._teammates = {}

        # --- Internal state ---
        self._tick = {}
        self._last_fire = {}
        self._beam_hold_start = {}
        self._threat_evade_frames = {}
        self._last_target_xy = None
        self._track_count = 0
        self._shot_hist = {}

    def step(self, observation, reward, done, info, agent_full_name, observation_space, action_space):
        own = observation["own"]
        # report position to shared formation state (same process, all 4 aircraft)
        try:
            name = agent_full_name or ""
            tick = self._tick.get(name, 0) + 1
            _report_formation_position(name, float(own[0]), float(own[1]), tick)
            self._teammates = _formation_teammates(name)
        except Exception:
            self._teammates = {}
        judgment = judge(self, observation, reward, done, info, agent_full_name,
                         observation_space, action_space)
        return execute(self, judgment, action_space)


def get_agent_class(args={}):
    return EscortHunterAgent


def get_policy(args={}):
    return DefaultPolicy(args)


def get_model_config(args={}):
    return load_model_config(args)
