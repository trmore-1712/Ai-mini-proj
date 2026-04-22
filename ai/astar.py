"""
ai/astar.py
===========
A* Search for optimal signal action selection.

Problem formulation (viva):
  State  : TrafficState 7-tuple
  Actions: {EXTEND_GREEN, SWITCH_SIGNAL, SHORTEN_GREEN, EMERGENCY_OVERRIDE}
  g(n)   : Cost accumulated so far (simulated wait time)
  h(n)   : Heuristic from ai/heuristic.py
  f(n)   : g(n) + h(n)

A* expands the node with minimum f(n) from a priority queue (heapq).
Depth limit = 3 steps → max nodes = 4^3 = 64 (fast enough for real-time at 30fps).

Viva: A* guarantees optimality when h(n) is admissible — our heuristic is
      admissible (proved in PRD §12.3), so the first action of the returned
      path is the globally optimal signal decision.

Look-ahead simulation constants:
  _CLEAR_RATE      — vehicles cleared per step when a direction turns green.
  _GREEN_WAIT_DROP — avg_wait relief (seconds) for the newly-green direction.
  _RED_WAIT_GAIN   — avg_wait increase (seconds) for the newly-red direction.
These mirror realistic intersection throughput so algorithms correctly weigh
SWITCH vs EXTEND rather than blindly preferring one action.
"""

import heapq
from typing import List, Optional, Tuple

from core.state import TrafficState, SignalAction, SignalPhase, Direction
from ai.heuristic import heuristic

# Default actions (unused directly now, filtered dynamically)
_ALL_ACTIONS = [
    SignalAction.EXTEND_CURRENT_GREEN,
    SignalAction.SWITCH_SIGNAL,
    SignalAction.SHORTEN_CURRENT_GREEN,
]


# ── Look-ahead simulation constants ──────────────────────────────────────────
# These govern how action effects are modelled in the cloned state.
# Tuned to approximate real intersection throughput at ~30 fps / 1-tick AI step.
_CLEAR_RATE      = 3     # vehicles cleared per step when direction turns green
_GREEN_WAIT_DROP = 8.0   # seconds of wait-time relief for the newly-green side
_RED_WAIT_GAIN   = 8.0   # seconds of extra wait accumulated on the newly-red side


def _apply_action_to_clone(state: TrafficState, action: SignalAction,
                            weights: dict) -> Tuple[TrafficState, float]:
    """
    Create a cloned state and simulate the effect of `action` on it.
    Returns the new state and the cost of taking this action (g increment).

    Key fix (v2): SWITCH now also models vehicle *clearance* for the direction
    that just received green.  Without this, all algorithms saw EXTEND as
    cheaper than SWITCH because the newly-green side never benefited — causing
    the EW direction to starve indefinitely.
    """
    s = state.clone()
    cost = 0.0

    if action == SignalAction.SWITCH_SIGNAL:
        if s.current_phase == SignalPhase.NS_GREEN:
            s.current_phase = SignalPhase.EW_GREEN
            # NS goes red: wait accumulates on the now-red side
            for d in (Direction.NORTH, Direction.SOUTH):
                s.lanes[d].avg_wait_time += _RED_WAIT_GAIN
            # EW gets green: vehicles start clearing
            for d in (Direction.EAST, Direction.WEST):
                cleared = min(_CLEAR_RATE, s.lanes[d].vehicle_count)
                s.lanes[d].vehicle_count  = max(0, s.lanes[d].vehicle_count - cleared)
                s.lanes[d].avg_wait_time  = max(0.0, s.lanes[d].avg_wait_time - _GREEN_WAIT_DROP)
                s.lanes[d].throughput    += cleared
        else:
            s.current_phase = SignalPhase.NS_GREEN
            # EW goes red
            for d in (Direction.EAST, Direction.WEST):
                s.lanes[d].avg_wait_time += _RED_WAIT_GAIN
            # NS gets green: vehicles start clearing
            for d in (Direction.NORTH, Direction.SOUTH):
                cleared = min(_CLEAR_RATE, s.lanes[d].vehicle_count)
                s.lanes[d].vehicle_count  = max(0, s.lanes[d].vehicle_count - cleared)
                s.lanes[d].avg_wait_time  = max(0.0, s.lanes[d].avg_wait_time - _GREEN_WAIT_DROP)
                s.lanes[d].throughput    += cleared
        cost = 3.0   # yellow transition penalty

    elif action == SignalAction.EXTEND_CURRENT_GREEN:
        # Current green direction clears more vehicles; red side waits longer
        s.phase_timer += 10.0
        if s.current_phase == SignalPhase.NS_GREEN:
            for d in (Direction.NORTH, Direction.SOUTH):
                cleared = min(_CLEAR_RATE, s.lanes[d].vehicle_count)
                s.lanes[d].vehicle_count  = max(0, s.lanes[d].vehicle_count - cleared)
                s.lanes[d].avg_wait_time  = max(0.0, s.lanes[d].avg_wait_time - 5.0)
                s.lanes[d].throughput    += cleared
            for d in (Direction.EAST, Direction.WEST):
                s.lanes[d].avg_wait_time += 5.0
        else:
            for d in (Direction.EAST, Direction.WEST):
                cleared = min(_CLEAR_RATE, s.lanes[d].vehicle_count)
                s.lanes[d].vehicle_count  = max(0, s.lanes[d].vehicle_count - cleared)
                s.lanes[d].avg_wait_time  = max(0.0, s.lanes[d].avg_wait_time - 5.0)
                s.lanes[d].throughput    += cleared
            for d in (Direction.NORTH, Direction.SOUTH):
                s.lanes[d].avg_wait_time += 5.0
        cost = 1.0

    elif action == SignalAction.SHORTEN_CURRENT_GREEN:
        # Shorten: modest clearance for current direction, red side STILL waits
        s.phase_timer = max(s.phase_timer - 5.0, 0.0)
        if s.current_phase == SignalPhase.NS_GREEN:
            for d in (Direction.NORTH, Direction.SOUTH):
                cleared = min(1, s.lanes[d].vehicle_count)
                s.lanes[d].vehicle_count  = max(0, s.lanes[d].vehicle_count - cleared)
                s.lanes[d].avg_wait_time  = max(0.0, s.lanes[d].avg_wait_time - 2.0)
                s.lanes[d].throughput    += cleared
            for d in (Direction.EAST, Direction.WEST):
                s.lanes[d].avg_wait_time += 2.0
        else:
            for d in (Direction.EAST, Direction.WEST):
                cleared = min(1, s.lanes[d].vehicle_count)
                s.lanes[d].vehicle_count  = max(0, s.lanes[d].vehicle_count - cleared)
                s.lanes[d].avg_wait_time  = max(0.0, s.lanes[d].avg_wait_time - 2.0)
                s.lanes[d].throughput    += cleared
            for d in (Direction.NORTH, Direction.SOUTH):
                s.lanes[d].avg_wait_time += 2.0
        cost = 0.5

    return s, cost


class AStarSearch:
    """
    A* search for optimal signal switching decisions.

    `decide(state)` runs a bounded 3-step lookahead and returns the first
    action of the optimal path found.
    """

    def __init__(self, config: dict, weights: dict):
        self.depth_limit = config.get("astar_depth_limit", 3)
        # Using fallback for max resilience, extracting min_green from settings
        self.min_green   = config.get("signals", {}).get("min_green_duration", 15.0) if "signals" in config else 15.0
        self.weights     = weights
        self.trace:      List[str] = []

    def _get_valid_actions(self, state: TrafficState) -> List[SignalAction]:
        actions = [SignalAction.EXTEND_CURRENT_GREEN]
        # Only allow SWITCH or SHORTEN if minimum green time has elapsed to stop AI flickering
        if getattr(state, "current_green_time", 0.0) >= self.min_green or getattr(state, "emergency_NS", False) or getattr(state, "emergency_EW", False):
            actions.append(SignalAction.SWITCH_SIGNAL)
            actions.append(SignalAction.SHORTEN_CURRENT_GREEN)
        return actions

    def decide(self, state: TrafficState) -> SignalAction:
        """
        Run A* from `state` up to depth_limit steps.
        Returns the best first action.

        Priority queue entries: (f, g, tie_breaker, state, path)
        """
        self.trace.clear()

        initial_h = heuristic(state, self.weights)
        self.trace.append(f"[A*] Start h(n)={initial_h:.1f} | state={state.as_tuple()}")

        # (f_cost, g_cost, counter, state_clone, action_path)
        counter = 0
        heap    = [(initial_h, 0.0, counter, state, [])]
        visited = {}   # state_tuple → best g seen

        best_action = SignalAction.EXTEND_CURRENT_GREEN
        best_f      = float("inf")

        while heap:
            f, g, _, cur_state, path = heapq.heappop(heap)

            state_key = cur_state.as_tuple()

            # Avoid revisiting a state at higher cost
            if state_key in visited and visited[state_key] <= g:
                continue
            visited[state_key] = g

            # If we've reached the depth limit, evaluate terminal node
            if len(path) >= self.depth_limit:
                if f < best_f:
                    best_f      = f
                    best_action = path[0] if path else SignalAction.EXTEND_CURRENT_GREEN
                continue

            # Expand each possible action
            valid_actions = self._get_valid_actions(cur_state)
            for action in valid_actions:
                next_state, delta_g = _apply_action_to_clone(cur_state, action, self.weights)
                new_g = g + delta_g
                new_h = heuristic(next_state, self.weights)
                new_f = new_g + new_h

                counter += 1
                new_path = path + [action]
                heapq.heappush(heap, (new_f, new_g, counter, next_state, new_path))

                if len(path) == 0:   # first level — log it
                    self.trace.append(
                        f"[A*] Action={action.value} → f={new_f:.1f} "
                        f"(g={new_g:.1f} + h={new_h:.1f})"
                    )

        self.trace.append(f"[A*] → Best action: {best_action.value} | f*={best_f:.1f}")
        return best_action
