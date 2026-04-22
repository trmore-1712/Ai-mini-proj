"""
ai/ai_engine.py
===============
Central AI decision dispatcher for the Smart Adaptive Traffic Signal Controller.

Algorithm selection matrix (per PRD §7.1):
  Priority 1 — Emergency flag active    → Emergency Override (immediate)
  Priority 2 — Lane blocked (accident)  → AO* re-planner
  Priority 3 — Peak hour mode           → Beam Search (speed over optimality)
  Priority 4 — Normal traffic           → A* (optimal with admissible heuristic)

  After action is decided:
    Hill Climbing fine-tunes the phase timer duration.

  Educational mode (toggled by user):
    BFS or DFS replaces A* to demonstrate exhaustive search.

Viva: The dispatcher embodies the principle of algorithm selection
      based on state conditions — a meta-level AI policy.
"""

from typing import List, Optional
from core.state import TrafficState, SignalAction, SignalPhase
from ai.heuristic import heuristic
from ai.astar import AStarSearch
from ai.beam_search import BeamSearch
from ai.hill_climbing import HillClimbing
from ai.bfs_dfs import BFSSearch, DFSSearch
from ai.ao_star import AOStar
from ai.minimax import MinimaxAB


class AIEngine:
    """
    Master AI decision engine.

    On each call to `decide(state)`:
      1. Checks for emergency / accident / peak-hour conditions
      2. Delegates to the appropriate search algorithm
      3. Optionally runs Hill Climbing for timer fine-tuning
      4. Returns a SignalAction and logs the decision trace
    """

    def __init__(self, config: dict, weights: dict):
        self.config  = config
        self.weights = weights

        # Instantiate all algorithm modules
        self.astar        = AStarSearch(config, weights)
        self.beam         = BeamSearch(config, weights)
        self.hill_climb   = HillClimbing(config, weights)
        self.bfs          = BFSSearch(config, weights)
        self.dfs          = DFSSearch(config, weights)
        self.ao_star      = AOStar(config, weights)
        self.minimax      = MinimaxAB(config, weights)

        # Current mode (can be overridden by UI)
        self._forced_algorithm: Optional[str] = None

        # Rolling trace log (last N lines shown in HUD)
        self._trace: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decide(self, state: TrafficState) -> SignalAction:
        """
        Select algorithm and compute the best SignalAction for this state.
        Updates state.algorithm_used and state.last_decision_cost.
        """
        self._trace.clear()

        # ── Priority 1: Emergency override (bypasses all search) ──────────
        if state.emergency_NS or state.emergency_EW:
            action = self._emergency_override(state)
            state.algorithm_used = "Emergency Override"
            self._trace.append("🚨 EMERGENCY OVERRIDE ACTIVATED")
            self._trace.append(f"   NS={state.emergency_NS} EW={state.emergency_EW}")
            self._trace.append(f"   → Action: {action.value}")
            state.last_decision_cost = heuristic(state, self.weights)
            return action

        # ── Priority 2: Accident / blocked lane → AO* ─────────────────────
        has_blocked = any(l.blocked for l in state.lanes.values())
        if has_blocked and self._forced_algorithm not in ("bfs", "dfs", "minimax"):
            action = self.ao_star.decide(state)
            state.algorithm_used = "AO*"
            self._trace.extend(self.ao_star.trace[-5:])
            state.last_decision_cost = heuristic(state, self.weights)
            return action

        # ── Priority 3: Forced algorithm (from UI dropdown) ───────────────
        if self._forced_algorithm == "bfs":
            action = self.bfs.decide(state)
            state.algorithm_used = "BFS"
            self._trace.extend(self.bfs.trace[-5:])
        elif self._forced_algorithm == "dfs":
            action = self.dfs.decide(state)
            state.algorithm_used = "DFS"
            self._trace.extend(self.dfs.trace[-5:])
        elif self._forced_algorithm == "minimax":
            action = self.minimax.decide(state)
            state.algorithm_used = "Minimax+αβ"
            self._trace.extend(self.minimax.trace[-5:])
        elif self._forced_algorithm == "beam":
            action = self.beam.decide(state)
            state.algorithm_used = "Beam Search"
            self._trace.extend(self.beam.trace[-5:])
        elif self._forced_algorithm == "hillclimb":
            action = self.hill_climb.decide(state)
            state.algorithm_used = "Hill Climbing"
            self._trace.extend(self.hill_climb.trace[-5:])

        # ── Priority 4: Peak hour → Beam Search ───────────────────────────
        elif state.is_peak_hour:
            action = self.beam.decide(state)
            state.algorithm_used = "Beam Search"
            self._trace.extend(self.beam.trace[-5:])

        # ── Default: Normal traffic → A* ──────────────────────────────────
        else:
            action = self.astar.decide(state)
            state.algorithm_used = "A*"
            self._trace.extend(self.astar.trace[-5:])

            # Hill Climbing post-processes the timer if A* chose to extend/stay
            if action in (SignalAction.EXTEND_CURRENT_GREEN,
                          SignalAction.SHORTEN_CURRENT_GREEN):
                hc_action = self.hill_climb.decide(state)
                if hc_action != action:
                    self._trace.append(
                        f"[HC] Refined: {action.value} → {hc_action.value}"
                    )
                    action = hc_action

        state.last_decision_cost = heuristic(state, self.weights)
        self._trace.append(
            f"▶ Cost: {state.last_decision_cost:.1f} | Mode: {state.algorithm_used}"
        )
        return action

    def get_trace(self) -> List[str]:
        """Return last decision trace for HUD display."""
        return list(self._trace)

    def set_algorithm(self, algorithm: str) -> None:
        """
        Force a specific algorithm (called from UI dropdown).
        Pass None or 'auto' to revert to automatic selection.
        """
        valid = {"astar", "beam", "bfs", "dfs", "hillclimb", "minimax", "auto", None}
        if algorithm in valid:
            self._forced_algorithm = None if algorithm == "auto" else algorithm

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emergency_override(self, state: TrafficState) -> SignalAction:
        """
        Return EMERGENCY_OVERRIDE action.
        If the current phase already serves the emergency direction, EXTEND it.
        Otherwise, SWITCH immediately.
        """
        if state.emergency_NS and state.current_phase == SignalPhase.NS_GREEN:
            return SignalAction.EXTEND_CURRENT_GREEN   # already serving — hold it
        if state.emergency_EW and state.current_phase == SignalPhase.EW_GREEN:
            return SignalAction.EXTEND_CURRENT_GREEN
        return SignalAction.EMERGENCY_OVERRIDE
