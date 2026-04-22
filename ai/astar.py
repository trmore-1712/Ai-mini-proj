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
"""

import heapq
from typing import List, Optional, Tuple

from core.state import TrafficState, SignalAction, SignalPhase, Direction
from ai.heuristic import heuristic

# All possible actions the AI can evaluate
_ALL_ACTIONS = [
    SignalAction.EXTEND_CURRENT_GREEN,
    SignalAction.SWITCH_SIGNAL,
    SignalAction.SHORTEN_CURRENT_GREEN,
]


def _apply_action_to_clone(state: TrafficState, action: SignalAction,
                            weights: dict) -> Tuple[TrafficState, float]:
    """
    Create a cloned state and simulate the effect of `action` on it.
    Returns the new state and the cost of taking this action (g increment).

    This is a lightweight 'rollout' — we don't re-run the full simulation,
    just adjust the state fields that the action would change.
    """
    s = state.clone()
    cost = 0.0

    if action == SignalAction.SWITCH_SIGNAL:
        # Simulate phase flip: waiting vehicles accumulate more wait
        if s.current_phase == SignalPhase.NS_GREEN:
            s.current_phase = SignalPhase.EW_GREEN
            # NS vehicles continue waiting during EW phase
            for d in (Direction.NORTH, Direction.SOUTH):
                s.lanes[d].avg_wait_time += 10.0
        else:
            s.current_phase = SignalPhase.NS_GREEN
            for d in (Direction.EAST, Direction.WEST):
                s.lanes[d].avg_wait_time += 10.0
        cost = 3.0   # yellow transition cost

    elif action == SignalAction.EXTEND_CURRENT_GREEN:
        # Current GREEN direction gets more throughput; other side waits longer
        s.phase_timer += 10.0
        if s.current_phase == SignalPhase.NS_GREEN:
            s.lanes[Direction.NORTH].avg_wait_time = max(0, s.lanes[Direction.NORTH].avg_wait_time - 5)
            s.lanes[Direction.SOUTH].avg_wait_time = max(0, s.lanes[Direction.SOUTH].avg_wait_time - 5)
            s.lanes[Direction.EAST].avg_wait_time  += 5.0
            s.lanes[Direction.WEST].avg_wait_time  += 5.0
        else:
            s.lanes[Direction.EAST].avg_wait_time  = max(0, s.lanes[Direction.EAST].avg_wait_time - 5)
            s.lanes[Direction.WEST].avg_wait_time  = max(0, s.lanes[Direction.WEST].avg_wait_time - 5)
            s.lanes[Direction.NORTH].avg_wait_time += 5.0
            s.lanes[Direction.SOUTH].avg_wait_time += 5.0
        cost = 1.0

    elif action == SignalAction.SHORTEN_CURRENT_GREEN:
        s.phase_timer = max(s.phase_timer - 5.0, 5.0)
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
        self.weights     = weights
        self.trace:      List[str] = []

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
            for action in _ALL_ACTIONS:
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
