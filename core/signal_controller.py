"""
core/signal_controller.py
=========================
Manages traffic signal phases, timers, and transitions.
Applies AI-decided actions to the TrafficState each tick.

Signal lifecycle:
  NS_GREEN  ──(timer expires or SWITCH action)──►  YELLOW  ──(3s)──►  EW_GREEN
  EW_GREEN  ──(timer expires or SWITCH action)──►  YELLOW  ──(3s)──►  NS_GREEN
  Any phase ──(EMERGENCY_OVERRIDE)──────────────►  EMERGENCY_OVERRIDE
"""

from core.state import TrafficState, SignalPhase, SignalAction, Direction
from core.events import bus, EVT_SIGNAL_SWITCHED


class SignalController:
    """
    Maintains the signal phase state machine.

    Called every game tick with the elapsed time delta.
    Also applies SignalActions returned by the AI engine.
    """

    def __init__(self, config: dict):
        self.default_green  = config.get("default_green_duration", 30.0)
        self.yellow_dur     = config.get("yellow_duration",         3.0)
        self.min_green      = config.get("min_green_duration",     10.0)
        self.max_green      = config.get("max_green_duration",     60.0)
        self.max_starvation = config.get("max_starvation_cycles",   3)

        # Which phase follows yellow after a switch
        self._next_phase_after_yellow: SignalPhase = SignalPhase.EW_GREEN

    # ------------------------------------------------------------------
    # Tick update
    # ------------------------------------------------------------------

    def update(self, state: TrafficState, dt: float) -> None:
        """Advance signal timers. Auto-switch when timer expires."""
        if state.paused:
            return

        state.total_elapsed += dt

        # Handle yellow transition
        if state.current_phase == SignalPhase.YELLOW:
            state.yellow_timer -= dt
            if state.yellow_timer <= 0:
                state.current_phase = self._next_phase_after_yellow
                state.phase_timer   = self.default_green
                state.yellow_timer  = 0.0
                self._on_phase_start(state)
            return

        # Emergency override: held until emergency clears (AI will call SWITCH)
        if state.current_phase == SignalPhase.EMERGENCY_OVERRIDE:
            return

        # Normal countdown
        state.phase_timer -= dt
        if state.phase_timer <= 0:
            self._begin_switch(state)

        # Fairness / starvation enforcement
        self._check_starvation(state)

    def apply_action(self, action: SignalAction, state: TrafficState) -> None:
        """
        Apply the AI engine's chosen action to the signal state.

        Actions:
            EXTEND_CURRENT_GREEN  → add 10s (capped at max_green)
            SHORTEN_CURRENT_GREEN → subtract 5s (floored at min_green)
            SWITCH_SIGNAL         → begin yellow → switch phase
            EMERGENCY_OVERRIDE    → jump directly to override phase
        """
        if action == SignalAction.SWITCH_SIGNAL:
            if state.current_phase not in (SignalPhase.YELLOW,
                                           SignalPhase.EMERGENCY_OVERRIDE):
                self._begin_switch(state)

        elif action == SignalAction.EXTEND_CURRENT_GREEN:
            state.phase_timer = min(state.phase_timer + 10.0, self.max_green)

        elif action == SignalAction.SHORTEN_CURRENT_GREEN:
            state.phase_timer = max(state.phase_timer - 5.0, self.min_green)

        elif action == SignalAction.EMERGENCY_OVERRIDE:
            # Determine which phase gives green to the emergency direction
            if state.emergency_NS:
                self._next_phase_after_yellow = SignalPhase.NS_GREEN
            else:
                self._next_phase_after_yellow = SignalPhase.EW_GREEN
            state.current_phase = SignalPhase.EMERGENCY_OVERRIDE
            # Force the correct phase so vehicles move immediately
            if state.emergency_NS:
                state.current_phase = SignalPhase.NS_GREEN
            else:
                state.current_phase = SignalPhase.EW_GREEN
            bus.publish(EVT_SIGNAL_SWITCHED, state.current_phase)

        # PEDESTRIAN_ALLOW — not implemented (future)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _begin_switch(self, state: TrafficState) -> None:
        """Start yellow transition, then flip phase."""
        if state.current_phase == SignalPhase.NS_GREEN:
            self._next_phase_after_yellow = SignalPhase.EW_GREEN
            state.cycles_since_green_NS   = 0        # NS just had its green
            state.cycles_since_green_EW  += 1
        elif state.current_phase == SignalPhase.EW_GREEN:
            self._next_phase_after_yellow = SignalPhase.NS_GREEN
            state.cycles_since_green_EW   = 0
            state.cycles_since_green_NS  += 1
            state.cycle_count            += 1        # full cycle complete

        # Reset throughput counters for the outgoing phase
        for lane in state.lanes.values():
            lane.throughput = 0

        state.current_phase = SignalPhase.YELLOW
        state.yellow_timer  = self.yellow_dur
        state.phase_timer   = 0.0
        bus.publish(EVT_SIGNAL_SWITCHED, SignalPhase.YELLOW)

    def _on_phase_start(self, state: TrafficState) -> None:
        """Called when a new green phase begins."""
        bus.publish(EVT_SIGNAL_SWITCHED, state.current_phase)

    def _check_starvation(self, state: TrafficState) -> None:
        """
        Force a phase switch if one direction has been starved of green
        for more than max_starvation_cycles consecutive cycles.
        This implements Feature 5 (Starvation Prevention).
        """
        if (state.cycles_since_green_EW >= self.max_starvation and
                state.current_phase == SignalPhase.NS_GREEN):
            self._begin_switch(state)
        elif (state.cycles_since_green_NS >= self.max_starvation and
              state.current_phase == SignalPhase.EW_GREEN):
            self._begin_switch(state)
