"""
ai/minimax.py
=============
Minimax + Alpha-Beta Pruning for adversarial worst-case traffic planning.

Viva explanation:
  Players:
    MAX player → Traffic Controller (AI): wants to minimise wait times
    MIN player → Traffic Generator (env): wants to maximise congestion

  Game tree (depth=2):
    Level 0 (MAX): AI chooses a signal action
    Level 1 (MIN): Environment chooses the worst-case vehicle spawn
    Level 2 (MAX): AI picks the best response

  Alpha-Beta pruning: skip branches where α ≥ β, giving ~40% fewer evals.

  Limitation: Real traffic isn't truly adversarial. Minimax gives pessimistic
  (worst-case) estimates — useful for stress-testing the controller.
"""

from typing import List, Tuple, Optional
from core.state import TrafficState, SignalAction, Direction
from ai.heuristic import heuristic
from ai.astar import _apply_action_to_clone

_ALL_ACTIONS = [
    SignalAction.EXTEND_CURRENT_GREEN,
    SignalAction.SWITCH_SIGNAL,
    SignalAction.SHORTEN_CURRENT_GREEN,
]

# Adversary moves: inject extra vehicles into one direction
_ADVERSARY_MOVES = [
    Direction.NORTH,
    Direction.SOUTH,
    Direction.EAST,
    Direction.WEST,
]


def _adversary_apply(state: TrafficState, direction: Direction,
                     surge: int = 5) -> TrafficState:
    """
    Simulate the adversary spawning a surge of vehicles in `direction`.
    Returns a new state clone (does NOT mutate the original).
    """
    s = state.clone()
    s.lanes[direction].vehicle_count += surge
    s.lanes[direction].avg_wait_time += surge * 2.0
    return s


class MinimaxAB:
    """
    Minimax with Alpha-Beta pruning for adversarial signal planning.

    `decide(state)` returns the action that maximises the worst-case outcome
    (i.e., minimises the maximum damage the adversary can inflict).

    Note: We *minimise* heuristic cost (lower = better state), so:
      MAX player → picks action with MINIMUM heuristic (best for controller)
      MIN player → picks spawn that MAXIMISES heuristic (worst for controller)
    """

    def __init__(self, config: dict, weights: dict, depth: int = 2):
        self.depth   = depth
        self.weights = weights
        self.trace:  List[str] = []
        self._nodes  = 0

    def decide(self, state: TrafficState) -> SignalAction:
        """Run Minimax with Alpha-Beta. Return best action for the controller."""
        self.trace.clear()
        self._nodes = 0
        self.trace.append(f"[Minimax] depth={self.depth} | α-β pruning enabled")

        best_val    = float("inf")
        best_action = SignalAction.EXTEND_CURRENT_GREEN
        alpha       = float("-inf")
        beta        = float("inf")

        for action in _ALL_ACTIONS:
            next_state, _ = _apply_action_to_clone(state, action, self.weights)
            val = self._minimax(next_state, self.depth - 1,
                                is_maximising=False,   # env plays MIN at depth-1
                                alpha=alpha, beta=beta)
            self.trace.append(
                f"[Minimax] Action={action.value} → minimax_val={val:.1f}"
            )
            if val < best_val:   # controller minimises cost
                best_val    = val
                best_action = action
            alpha = min(alpha, val)   # alpha: best the MAX player has found so far

        self.trace.append(
            f"[Minimax] nodes_eval={self._nodes} | "
            f"best={best_action.value} val={best_val:.1f}"
        )
        return best_action

    def _minimax(self, state: TrafficState, depth: int,
                 is_maximising: bool,
                 alpha: float, beta: float) -> float:
        """
        Recursive Minimax with α-β pruning.

        is_maximising=False → MIN player (adversary) picks worst spawn
        is_maximising=True  → MAX player (controller) picks best action
        """
        self._nodes += 1

        if depth == 0:
            return heuristic(state, self.weights)

        if is_maximising:
            # Controller's turn: pick action minimising heuristic
            best = float("inf")
            for action in _ALL_ACTIONS:
                next_s, _ = _apply_action_to_clone(state, action, self.weights)
                val        = self._minimax(next_s, depth - 1, False, alpha, beta)
                best       = min(best, val)
                alpha      = min(alpha, best)
                if alpha <= beta:
                    break   # α-β prune
            return best
        else:
            # Adversary's turn: pick spawn maximising heuristic
            worst = float("-inf")
            for direction in _ADVERSARY_MOVES:
                adv_state = _adversary_apply(state, direction)
                val       = self._minimax(adv_state, depth - 1, True, alpha, beta)
                worst     = max(worst, val)
                beta      = max(beta, worst)
                if alpha >= beta:
                    break   # α-β prune
            return worst
