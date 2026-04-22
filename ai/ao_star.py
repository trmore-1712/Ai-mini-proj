"""
ai/ao_star.py
=============
AO* (AND-OR graph search) for multi-goal accident re-planning.

Viva explanation:
  AO* works on AND-OR graphs where:
    OR nodes  — goal can be achieved by ANY one of several sub-plans
    AND nodes — ALL sub-goals must be satisfied simultaneously

  In our traffic domain:
    OR  node: "Handle intersection optimally"
              → Branch A: Emergency override  (if emergency)
              → Branch B: Beam Search plan    (if peak hour)
              → Branch C: A* optimal action   (normal)

    AND node: In accident scenario — we must SIMULTANEOUSLY achieve:
              Sub-goal 1: Re-route traffic away from blocked lane
              Sub-goal 2: Handle any pending emergency
              Both are AND conditions — both must succeed.

  AO* finds the minimum-cost solution tree (not just a path).

This module implements a simplified 2-level AND-OR planner
that models the accident scenario as an AND decomposition.
"""

from typing import List, Dict, Optional, Tuple
from core.state import TrafficState, SignalAction, SignalPhase, Direction
from ai.heuristic import heuristic


# ---------------------------------------------------------------------------
# AND-OR Graph node types
# ---------------------------------------------------------------------------

class OrNode:
    """
    OR node — goal achievable by any one branch (minimum cost branch chosen).
    """
    def __init__(self, label: str, branches: list):
        self.label    = label
        self.branches = branches   # list of (cost, action_or_and_node)
        self.solved   = False
        self.best_cost = float("inf")
        self.best_action: Optional[SignalAction] = None


class AndNode:
    """
    AND node — all sub-goals must be achieved (costs are summed).
    """
    def __init__(self, label: str, sub_goals: list):
        self.label     = label
        self.sub_goals = sub_goals   # list of (cost, description)
        self.solved    = False
        self.total_cost = 0.0


class AOStar:
    """
    Simplified AO* planner for accident+emergency compound scenarios.

    Builds a 2-level AND-OR tree:
      Root (OR): "Handle intersection"
        Branch A — AND: [Reroute blocked lane] AND [Serve emergency if any]
        Branch B — OR : Normal A* plan (no accident complications)

    AO* propagates costs back and selects the minimum-cost solution tree.
    """

    def __init__(self, config: dict, weights: dict):
        self.weights = weights
        self.trace:  List[str] = []

    def decide(self, state: TrafficState) -> SignalAction:
        """
        Build AND-OR graph for the current state and return the optimal action.
        Used when at least one lane is blocked (accident scenario).
        """
        self.trace.clear()
        self.trace.append("[AO*] Building AND-OR graph for accident scenario")

        # Determine which lanes are blocked
        blocked_dirs = [d for d, l in state.lanes.items() if l.blocked]
        has_emergency = state.emergency_NS or state.emergency_EW

        # ── OR node: root goal ──────────────────────────────────────────────
        # Branch A: AND(reroute, serve_emergency) — for accident+emergency
        # Branch B: simple switch away from blocked lane (normal OR branch)

        branch_a_cost = self._and_branch_cost(state, blocked_dirs, has_emergency)
        branch_b_cost = self._simple_reroute_cost(state, blocked_dirs)

        self.trace.append(
            f"[AO*] OR root | Branch-A (AND) cost={branch_a_cost:.1f} | "
            f"Branch-B (simple) cost={branch_b_cost:.1f}"
        )

        if branch_a_cost <= branch_b_cost:
            self.trace.append("[AO*] → Selected Branch-A (AND node solution)")
            return self._and_branch_action(state, blocked_dirs, has_emergency)
        else:
            self.trace.append("[AO*] → Selected Branch-B (simple reroute)")
            return self._simple_reroute_action(state, blocked_dirs)

    # ------------------------------------------------------------------
    # AND branch: reroute + emergency sub-goals
    # ------------------------------------------------------------------

    def _and_branch_cost(self, state: TrafficState,
                         blocked: list, has_emergency: bool) -> float:
        """Cost of solving both sub-goals in the AND node."""
        reroute_cost   = self._reroute_cost(state, blocked)
        emergency_cost = self._emergency_subgoal_cost(state) if has_emergency else 0.0
        total          = reroute_cost + emergency_cost

        self.trace.append(
            f"[AO*] AND node | reroute={reroute_cost:.1f} + "
            f"emergency={emergency_cost:.1f} = {total:.1f}"
        )
        return total

    def _and_branch_action(self, state: TrafficState,
                           blocked: list, has_emergency: bool) -> SignalAction:
        """Return action satisfying the AND node (emergency takes priority)."""
        if has_emergency:
            return SignalAction.EMERGENCY_OVERRIDE
        # Reroute: switch away from blocked direction
        if blocked:
            if all(d in (Direction.NORTH, Direction.SOUTH) for d in blocked):
                # NS blocked → give EW green
                if state.current_phase == SignalPhase.NS_GREEN:
                    return SignalAction.SWITCH_SIGNAL
        return SignalAction.EXTEND_CURRENT_GREEN

    def _reroute_cost(self, state: TrafficState, blocked: list) -> float:
        """Estimate cost of routing traffic away from blocked lane."""
        base = heuristic(state, self.weights)
        # Penalty for each blocked lane currently getting green
        penalty = 0.0
        for d in blocked:
            if d in (Direction.NORTH, Direction.SOUTH):
                if state.current_phase == SignalPhase.NS_GREEN:
                    penalty += 50.0    # high cost — giving green to blocked lane
            else:
                if state.current_phase == SignalPhase.EW_GREEN:
                    penalty += 50.0
        return base + penalty

    def _emergency_subgoal_cost(self, state: TrafficState) -> float:
        """Cost of the emergency sub-goal (high if ambulance stuck on RED)."""
        if state.emergency_NS and state.current_phase == SignalPhase.EW_GREEN:
            return 200.0
        if state.emergency_EW and state.current_phase == SignalPhase.NS_GREEN:
            return 200.0
        return 10.0   # low cost — already serving emergency direction

    # ------------------------------------------------------------------
    # Simple OR branch
    # ------------------------------------------------------------------

    def _simple_reroute_cost(self, state: TrafficState, blocked: list) -> float:
        """Cost estimate for the simple OR branch (direct switch)."""
        return heuristic(state, self.weights) + 20.0   # slight overhead

    def _simple_reroute_action(self, state: TrafficState,
                               blocked: list) -> SignalAction:
        """Switch phase if current green serves a blocked lane."""
        for d in blocked:
            ns_blocked = d in (Direction.NORTH, Direction.SOUTH)
            ew_blocked = d in (Direction.EAST, Direction.WEST)
            if ns_blocked and state.current_phase == SignalPhase.NS_GREEN:
                return SignalAction.SWITCH_SIGNAL
            if ew_blocked and state.current_phase == SignalPhase.EW_GREEN:
                return SignalAction.SWITCH_SIGNAL
        return SignalAction.EXTEND_CURRENT_GREEN
