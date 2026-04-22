"""
ai/bfs_dfs.py
=============
BFS and DFS signal sequence explorers.

These are used in "educational mode" (toggled from the UI) to demonstrate
exhaustive state-space search. They are NOT used for real-time decisions
because they explore all nodes up to depth d, which is too slow at runtime.

Viva:
  BFS  — complete, finds shallowest goal, O(b^d) space
  DFS  — memory-efficient (O(d) stack), but not optimal, may not terminate
          without depth limit

Both return the first action of the best-cost path found.
"""

from collections import deque
from typing import List, Optional, Tuple

from core.state import TrafficState, SignalAction, SignalPhase, Direction
from ai.heuristic import heuristic
from ai.astar import _apply_action_to_clone

_ALL_ACTIONS = [
    SignalAction.EXTEND_CURRENT_GREEN,
    SignalAction.SWITCH_SIGNAL,
    SignalAction.SHORTEN_CURRENT_GREEN,
]


class BFSSearch:
    """
    Breadth-First Search over signal action sequences.
    Explores level by level, guaranteed to find the shallowest solution.
    """

    def __init__(self, config: dict, weights: dict):
        self.max_depth = config.get("astar_depth_limit", 3)
        self.weights   = weights
        self.trace:    List[str] = []

    def decide(self, state: TrafficState) -> SignalAction:
        """Run BFS up to max_depth. Return first action of the best path."""
        self.trace.clear()
        self.trace.append(f"[BFS] Educational mode — max_depth={self.max_depth}")

        # Queue elements: (state_clone, action_path)
        queue   = deque([(state, [])])
        visited = set()
        visited.add(state.as_tuple())

        best_action = SignalAction.EXTEND_CURRENT_GREEN
        best_h      = float("inf")
        nodes_exp   = 0

        while queue:
            cur_state, path = queue.popleft()
            nodes_exp += 1

            if len(path) == self.max_depth:
                h = heuristic(cur_state, self.weights)
                if h < best_h:
                    best_h      = h
                    best_action = path[0] if path else SignalAction.EXTEND_CURRENT_GREEN
                continue

            for action in _ALL_ACTIONS:
                next_state, _ = _apply_action_to_clone(cur_state, action, self.weights)
                key           = next_state.as_tuple()
                if key not in visited:
                    visited.add(key)
                    queue.append((next_state, path + [action]))

        self.trace.append(
            f"[BFS] Nodes expanded={nodes_exp} | best_h={best_h:.1f} "
            f"→ {best_action.value}"
        )
        return best_action


class DFSSearch:
    """
    Depth-First Search with depth limit over signal action sequences.
    Explores deep paths first — memory efficient but non-optimal.
    """

    def __init__(self, config: dict, weights: dict):
        self.max_depth = config.get("astar_depth_limit", 3)
        self.weights   = weights
        self.trace:    List[str] = []
        self._best_h:  float    = float("inf")
        self._best_action        = SignalAction.EXTEND_CURRENT_GREEN
        self._nodes:   int       = 0

    def decide(self, state: TrafficState) -> SignalAction:
        """Run iterative-deepening DFS. Return first action of best path."""
        self.trace.clear()
        self._best_h      = float("inf")
        self._best_action = SignalAction.EXTEND_CURRENT_GREEN
        self._nodes       = 0
        self.trace.append(f"[DFS] Educational mode — max_depth={self.max_depth}")

        self._dfs(state, [], 0)

        self.trace.append(
            f"[DFS] Nodes={self._nodes} | best_h={self._best_h:.1f} "
            f"→ {self._best_action.value}"
        )
        return self._best_action

    def _dfs(self, state: TrafficState, path: list, depth: int) -> None:
        """Recursive DFS helper."""
        self._nodes += 1

        if depth == self.max_depth:
            h = heuristic(state, self.weights)
            if h < self._best_h:
                self._best_h      = h
                self._best_action = path[0] if path else SignalAction.EXTEND_CURRENT_GREEN
            return

        for action in _ALL_ACTIONS:
            next_state, _ = _apply_action_to_clone(state, action, self.weights)
            self._dfs(next_state, path + [action], depth + 1)
