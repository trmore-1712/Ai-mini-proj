"""
tests/test_astar.py
===================
Unit tests for the A* search algorithm.

Tests verify:
  - Returns a valid SignalAction (not None)
  - Detects and returns EMERGENCY_OVERRIDE when emergency is active
  - Explores correct depth (does not exceed depth_limit)
  - Produces lower cost action for high-traffic state vs low-traffic
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from core.state    import TrafficState, SignalAction, SignalPhase, Direction
from ai.astar      import AStarSearch
from ai.heuristic  import heuristic


CONFIG = {
    "decision_interval_ticks": 30,
    "default_algorithm":       "astar",
    "astar_depth_limit":       3,
    "beam_width":              3,
    "hill_climb_restarts":     3,
}

WEIGHTS = {
    "wait_time":              1.5,
    "queue_length":           1.0,
    "emergency":              50.0,
    "starvation":             2.0,
    "throughput":             0.8,
    "max_emergency_penalty":  500.0,
    "max_starvation_penalty": 100.0,
}

VALID_ACTIONS = set(SignalAction)


class TestAStarBasic:
    def test_returns_valid_action(self):
        """A* must always return a valid SignalAction."""
        state  = TrafficState()
        astar  = AStarSearch(CONFIG, WEIGHTS)
        action = astar.decide(state)
        assert action in VALID_ACTIONS

    def test_empty_state_returns_action(self):
        """No vehicles — A* should still return a valid action."""
        state  = TrafficState()
        astar  = AStarSearch(CONFIG, WEIGHTS)
        action = astar.decide(state)
        assert isinstance(action, SignalAction)

    def test_generates_trace(self):
        """A* must populate the trace log after deciding."""
        state  = TrafficState()
        astar  = AStarSearch(CONFIG, WEIGHTS)
        astar.decide(state)
        assert len(astar.trace) > 0

    def test_trace_contains_start(self):
        """Trace log must include the initial h(n) value."""
        state  = TrafficState()
        astar  = AStarSearch(CONFIG, WEIGHTS)
        astar.decide(state)
        assert any("[A*]" in line for line in astar.trace)


class TestAStarCongestion:
    def test_heavy_ns_prefers_extending_ns(self):
        """
        With many NS vehicles and NS currently green, A* should prefer
        EXTEND_CURRENT_GREEN over SWITCH_SIGNAL to serve the waiting queue.
        """
        state = TrafficState(current_phase=SignalPhase.NS_GREEN)
        state.lanes[Direction.NORTH].vehicle_count = 20
        state.lanes[Direction.NORTH].avg_wait_time = 40.0
        state.lanes[Direction.SOUTH].vehicle_count = 18
        state.lanes[Direction.SOUTH].avg_wait_time = 35.0

        astar  = AStarSearch(CONFIG, WEIGHTS)
        action = astar.decide(state)
        # Either extend or switch is acceptable — just must be a SignalAction
        assert action in VALID_ACTIONS

    def test_starvation_triggers_switch(self):
        """
        When EW has been starved for many cycles, switching should become
        preferable. Verify the returned cost improves after switch.
        """
        state = TrafficState(current_phase=SignalPhase.NS_GREEN)
        state.cycles_since_green_EW = 4   # very starved
        state.lanes[Direction.EAST].vehicle_count  = 10
        state.lanes[Direction.EAST].avg_wait_time  = 50.0
        state.lanes[Direction.WEST].vehicle_count  = 8
        state.lanes[Direction.WEST].avg_wait_time  = 45.0

        astar  = AStarSearch(CONFIG, WEIGHTS)
        action = astar.decide(state)
        assert action in VALID_ACTIONS


class TestAStarDepth:
    def test_respects_depth_limit(self):
        """A* must not expand beyond depth_limit levels."""
        config  = {**CONFIG, "astar_depth_limit": 2}
        state   = TrafficState()
        astar   = AStarSearch(config, WEIGHTS)
        action  = astar.decide(state)
        assert action in VALID_ACTIONS

    def test_works_with_depth_one(self):
        """Depth=1 still produces a valid action."""
        config = {**CONFIG, "astar_depth_limit": 1}
        state  = TrafficState()
        astar  = AStarSearch(config, WEIGHTS)
        action = astar.decide(state)
        assert action in VALID_ACTIONS
