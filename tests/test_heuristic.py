"""
tests/test_heuristic.py
=======================
Unit tests for the core heuristic function h(n).

Tests verify:
  - h(n) is always non-negative (admissibility requirement)
  - Emergency penalty is correctly applied when ambulance is stuck on RED
  - Starvation penalty grows with cycles_since_green
  - Throughput bonus reduces h(n)
  - Blocked lane adds penalty
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from core.state      import TrafficState, SignalPhase, Direction, LaneState
from ai.heuristic    import heuristic


DEFAULT_WEIGHTS = {
    "wait_time":              1.5,
    "queue_length":           1.0,
    "emergency":              50.0,
    "starvation":             2.0,
    "throughput":             0.8,
    "max_emergency_penalty":  500.0,
    "max_starvation_penalty": 100.0,
}


def make_state(**kwargs) -> TrafficState:
    state = TrafficState()
    for k, v in kwargs.items():
        setattr(state, k, v)
    return state


class TestHeuristicAdmissibility:
    def test_zero_state_nonneg(self):
        """h(n) must be ≥ 0 even for an empty intersection."""
        state = TrafficState()
        h = heuristic(state, DEFAULT_WEIGHTS)
        assert h >= 0.0

    def test_always_nonneg_with_high_throughput(self):
        """Throughput bonus must not make h(n) negative."""
        state = TrafficState()
        for lane in state.lanes.values():
            lane.throughput = 1000   # huge throughput
        h = heuristic(state, DEFAULT_WEIGHTS)
        assert h >= 0.0

    def test_heavy_traffic_positive(self):
        """Heavily loaded intersection must have h(n) > 0."""
        state = TrafficState()
        for lane in state.lanes.values():
            lane.vehicle_count = 15
            lane.avg_wait_time = 30.0
        h = heuristic(state, DEFAULT_WEIGHTS)
        assert h > 0


class TestEmergencyPenalty:
    def test_ambulance_stuck_on_red_ns_high_cost(self):
        """NS ambulance waiting at RED (EW_GREEN) should spike h(n)."""
        state = TrafficState(current_phase=SignalPhase.EW_GREEN)
        state.lanes[Direction.NORTH].emergency_flag = True
        h = heuristic(state, DEFAULT_WEIGHTS)
        assert h >= DEFAULT_WEIGHTS["max_emergency_penalty"] * DEFAULT_WEIGHTS["emergency"] / 100

    def test_ambulance_being_served_lower_cost(self):
        """Ambulance on NS with NS_GREEN should yield lower penalty."""
        state_red   = TrafficState(current_phase=SignalPhase.EW_GREEN)
        state_green = TrafficState(current_phase=SignalPhase.NS_GREEN)
        for s in (state_red, state_green):
            s.lanes[Direction.NORTH].emergency_flag = True
        h_red   = heuristic(state_red,   DEFAULT_WEIGHTS)
        h_green = heuristic(state_green, DEFAULT_WEIGHTS)
        assert h_red > h_green

    def test_no_emergency_no_penalty(self):
        """No emergency flags → emergency penalty = 0."""
        state = TrafficState(current_phase=SignalPhase.NS_GREEN)
        # Ensure no emergency
        for lane in state.lanes.values():
            lane.emergency_flag = False
        h = heuristic(state, DEFAULT_WEIGHTS)
        # h should only reflect wait + queue (both 0 here)
        assert h == 0.0


class TestStarvationPenalty:
    def test_starvation_increases_cost(self):
        """cycles_since_green_NS > 0 should increase h(n)."""
        s0 = TrafficState()
        s0.cycles_since_green_NS = 0
        s1 = TrafficState()
        s1.cycles_since_green_NS = 3
        assert heuristic(s1, DEFAULT_WEIGHTS) > heuristic(s0, DEFAULT_WEIGHTS)

    def test_starvation_capped(self):
        """Starvation penalty must be ≤ max_starvation_penalty."""
        state = TrafficState()
        state.cycles_since_green_NS = 9999
        h = heuristic(state, DEFAULT_WEIGHTS)
        max_s_contrib = DEFAULT_WEIGHTS["starvation"] * DEFAULT_WEIGHTS["max_starvation_penalty"]
        assert h <= max_s_contrib + 1.0   # small tolerance


class TestThroughputBonus:
    def test_high_throughput_reduces_cost(self):
        """More cleared vehicles → lower h(n)."""
        s_low = TrafficState()
        s_low.lanes[Direction.NORTH].throughput = 0

        s_high = TrafficState()
        s_high.lanes[Direction.NORTH].throughput = 10

        h_low  = heuristic(s_low,  DEFAULT_WEIGHTS)
        h_high = heuristic(s_high, DEFAULT_WEIGHTS)
        assert h_low >= h_high


class TestBlockedLanePenalty:
    def test_blocked_lane_adds_cost(self):
        """A blocked lane should increase h(n) relative to open lane."""
        s_open   = TrafficState()
        s_blocked = TrafficState()
        s_blocked.lanes[Direction.NORTH].blocked = True
        assert heuristic(s_blocked, DEFAULT_WEIGHTS) > heuristic(s_open, DEFAULT_WEIGHTS)
