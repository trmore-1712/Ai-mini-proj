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
  Level 1 → expand all actions, keep top-k by f(n) + diversity injection
  Level 2 → expand each of top-k, keep top-k again
  Level 3 → pick best terminal node → return its first action

Diversity injection (v2 fix):
  After pruning to top-k at depth 0, if no SWITCH path is in the beam AND
  the non-green direction has significantly more congestion, the best SWITCH
  candidate from the full list is injected.  This prevents the beam from
  converging to all-EXTEND paths and starving the waiting direction.
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
        self.min_green   = config.get("signals", {}).get("min_green_duration", 15.0) if "signals" in config else 15.0
        self.weights     = weights
        self.trace:      List[str] = []

    def _get_valid_actions(self, state: TrafficState) -> List[SignalAction]:
        actions = [SignalAction.EXTEND_CURRENT_GREEN]
        if getattr(state, "current_green_time", 0.0) >= self.min_green or getattr(state, "emergency_NS", False) or getattr(state, "emergency_EW", False):
            actions.append(SignalAction.SWITCH_SIGNAL)
            actions.append(SignalAction.SHORTEN_CURRENT_GREEN)
        return actions

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
                valid_actions = self._get_valid_actions(cur_state)
                for action in valid_actions:
                    next_state, delta_g = _apply_action_to_clone(
                        cur_state, action, self.weights
                    )
                    new_h = heuristic(next_state, self.weights)
                    new_f = delta_g + new_h   # simplified: g is small vs h
                    candidates.append((new_f, next_state, path + [action]))

            # Keep only top-k candidates by ascending f
            candidates.sort(key=lambda x: x[0])
            beam = candidates[: self.beam_width]

            # ── Diversity injection at depth 0 ──────────────────────────────
            # If every beam path starts with EXTEND (or SHORTEN) AND the
            # currently-red direction is significantly more congested,
            # inject the best SWITCH candidate to ensure it is considered.
            if depth == 0:
                beam = self._inject_switch_if_needed(state, beam, candidates)

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

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    def _inject_switch_if_needed(
            self,
            state: TrafficState,
            beam: list,
            all_candidates: list) -> list:
        """
        Diversity guarantee: if the beam contains NO path that starts with
        SWITCH_SIGNAL, and the non-green direction has at least 1.5× more
        vehicles than the currently-green direction, inject the best
        SWITCH candidate from `all_candidates` by replacing the worst
        beam member.

        This prevents the beam from collapsing to all-EXTEND paths and
        completely ignoring the starving direction.
        """
        from core.state import SignalPhase, Direction

        # Check if any beam path already starts with SWITCH
        beam_has_switch = any(
            p and p[0] == SignalAction.SWITCH_SIGNAL
            for _, _, p in beam
        )
        if beam_has_switch:
            return beam

        # Compute congestion ratio between red and green directions
        if state.current_phase == SignalPhase.NS_GREEN:
            green_count = state.vehicles_NS
            red_count   = state.vehicles_EW
            red_wait    = state.avg_wait_EW
        else:
            green_count = state.vehicles_EW
            red_count   = state.vehicles_NS
            red_wait    = state.avg_wait_NS

        # Only inject if the waiting side is significantly more congested
        # OR if it has been waiting under red for dangerously long (>= 15s avg)
        threshold = max(green_count * 1.5, 5)   # at least 5 vehicles gap
        if red_count < threshold and red_wait < 15.0:
            return beam

        # Find the best SWITCH candidate from the full list
        switch_candidates = [
            c for c in all_candidates
            if c[2] and c[2][0] == SignalAction.SWITCH_SIGNAL
        ]
        if not switch_candidates:
            return beam

        best_switch = switch_candidates[0]   # already sorted by f
        # Replace worst beam member with best SWITCH candidate
        new_beam = beam[:-1] + [best_switch]
        new_beam.sort(key=lambda x: x[0])
        self.trace.append(
            f"[Beam] Diversity: injected SWITCH candidate "
            f"(red={red_count} vs green={green_count})"
        )
        return new_beam
