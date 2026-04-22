"""
ai/hill_climbing.py
===================
Hill Climbing local search for fine-tuning the signal phase timer duration.

Used AFTER the phase decision (by A*) is made.
Searches over {T-5, T, T+5, T+10} second variants and picks the duration
that minimises h(n) of the resulting state.

Limitation (viva point):
  Hill Climbing can get stuck in local optima.
  We mitigate this by running `hill_climb_restarts` random restarts
  and returning the global best found across all restarts.
"""

import random
from typing import List, Tuple

from core.state import TrafficState, SignalAction
from ai.heuristic import heuristic


# Duration deltas (seconds) to explore around current timer value
_NEIGHBOR_DELTAS = [-5, 0, +5, +10]


class HillClimbing:
    """
    Gradient-descent style search over phase timer values.

    `decide(state)` evaluates neighbouring timer values and returns
    the SignalAction that yields the lowest heuristic cost.
    """

    def __init__(self, config: dict, weights: dict):
        self.restarts = config.get("hill_climb_restarts", 3)
        self.weights  = weights
        self.trace:   List[str] = []

    def decide(self, state: TrafficState) -> SignalAction:
        """
        Run hill climbing with random restarts.
        Returns EXTEND or SHORTEN based on which timer value minimises h(n).
        """
        self.trace.clear()
        self.trace.append(f"[HillClimb] Start timer={state.phase_timer:.1f}s")

        best_action = SignalAction.EXTEND_CURRENT_GREEN
        best_h      = float("inf")

        for restart in range(self.restarts):
            # Random starting point: perturb timer ±15s
            current_timer = state.phase_timer + random.uniform(-15, 15)
            current_timer = max(10.0, min(60.0, current_timer))

            improved = True
            while improved:
                improved   = False
                neighbours = self._get_neighbours(state, current_timer)

                for action, sim_state, delta_t in neighbours:
                    h = heuristic(sim_state, self.weights)
                    if h < best_h:
                        best_h       = h
                        best_action  = action
                        current_timer = current_timer + delta_t
                        improved      = True
                        break   # steepest ascent — move immediately

            self.trace.append(
                f"[HillClimb] Restart {restart+1}: best_h={best_h:.1f} → {best_action.value}"
            )

        self.trace.append(f"[HillClimb] → Final: {best_action.value} h*={best_h:.1f}")
        return best_action

    def _get_neighbours(self, state: TrafficState,
                        current_timer: float) -> List[Tuple]:
        """
        Generate (action, cloned_state, delta_t) for each timer neighbour.
        """
        results = []
        for delta in _NEIGHBOR_DELTAS:
            new_timer = current_timer + delta
            new_timer = max(10.0, min(60.0, new_timer))

            s = state.clone()
            s.phase_timer = new_timer

            if delta > 0:
                action = SignalAction.EXTEND_CURRENT_GREEN
            elif delta < 0:
                action = SignalAction.SHORTEN_CURRENT_GREEN
            else:
                action = SignalAction.EXTEND_CURRENT_GREEN   # no-op

            results.append((action, s, delta))
        return results
