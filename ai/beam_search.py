"""
ai/beam_search.py
=================
Beam Search for peak-hour signal planning.

Viva: Beam Search keeps only the top-k nodes at each depth level (beam width k=3).
It's faster than A* because it prunes most of the search space, but sacrifices
guaranteed optimality — an acceptable trade-off during congestion when any
good decision is better than a delayed optimal one.

Exploration:
  Level 0 → current state
  Level 1 → expand all actions, keep top-k by f(n)
  Level 2 → expand each of top-k, keep top-k again
  Level 3 → pick best terminal node → return its first action
"""

from typing import List, Tuple, Optional
from core.state import TrafficState, SignalAction, SignalPhase, Direction
from ai.heuristic import heuristic
from ai.astar import _apply_action_to_clone   # reuse state-transition logic

_ALL_ACTIONS = [
    SignalAction.EXTEND_CURRENT_GREEN,
    SignalAction.SWITCH_SIGNAL,
    SignalAction.SHORTEN_CURRENT_GREEN,
]


class BeamSearch:
    """
    Beam Search planner for peak-hour traffic conditions.

    Maintains a beam of the best k candidate plans at each depth.
    Returns the first action of the highest-scoring terminal path.
    """

    def __init__(self, config: dict, weights: dict):
        self.beam_width  = config.get("beam_width",        3)
        self.depth_limit = config.get("astar_depth_limit", 3)
        self.weights     = weights
        self.trace:      List[str] = []

    def decide(self, state: TrafficState) -> SignalAction:
        """
        Run beam search from `state`.
        Each beam element: (f_cost, state_clone, [action_path])
        """
        self.trace.clear()
        self.trace.append(
            f"[Beam k={self.beam_width}] PEAK HOUR | vehicles={state.total_vehicles}"
        )

        # Initialise beam with the starting state
        # Element: (f, state, path_of_actions)
        beam: List[Tuple[float, TrafficState, List[SignalAction]]] = [
            (heuristic(state, self.weights), state, [])
        ]

        for depth in range(self.depth_limit):
            candidates = []

            for f, cur_state, path in beam:
                for action in _ALL_ACTIONS:
                    next_state, delta_g = _apply_action_to_clone(
                        cur_state, action, self.weights
                    )
                    new_h = heuristic(next_state, self.weights)
                    new_f = delta_g + new_h   # simplified: g is small vs h
                    candidates.append((new_f, next_state, path + [action]))

            # Keep only top-k candidates by ascending f
            candidates.sort(key=lambda x: x[0])
            beam = candidates[: self.beam_width]

            top_f = beam[0][0] if beam else 0
            self.trace.append(
                f"[Beam] Depth {depth+1}: kept {len(beam)} nodes, "
                f"best f={top_f:.1f}"
            )

        if not beam:
            return SignalAction.EXTEND_CURRENT_GREEN

        # Best terminal node → return first action in its path
        best_f, best_state, best_path = beam[0]
        action = best_path[0] if best_path else SignalAction.EXTEND_CURRENT_GREEN
        self.trace.append(f"[Beam] → Best: {action.value} | terminal f={best_f:.1f}")
        return action
