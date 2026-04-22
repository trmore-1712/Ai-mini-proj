"""
tests/test_simulation.py
========================
Unit tests for the simulation engine.

Tests verify:
  - Vehicle spawning creates Vehicle objects with correct fields
  - Emergency vehicle spawn sets emergency_flag on the lane
  - Accident trigger sets blocked=True on the lane
  - Reset clears all vehicles and resets state
  - Peak hour detection triggers when vehicle count exceeds threshold
  - Lane count sync matches number of Vehicle objects per direction
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from core.state      import TrafficState, SignalPhase, Direction
from core.simulation import SimulationEngine, Vehicle


CONFIG = {
    "fps":                       60,
    "time_scale":                1.0,
    "spawn_rate_normal":         0.8,
    "spawn_rate_peak":           2.5,
    "emergency_probability":     0.003,
    "accident_probability":      0.001,
    "peak_hour_threshold":       20,
    "peak_hour_window_seconds":  15,
}


def make_engine() -> SimulationEngine:
    return SimulationEngine(CONFIG)


class TestVehicleSpawning:
    def test_manual_emergency_spawn(self):
        """Manually triggering emergency must create ambulance on correct lane."""
        eng   = make_engine()
        state = TrafficState()
        eng.trigger_emergency(Direction.NORTH, state)

        ambulances = [v for v in eng.vehicles
                      if v.is_emergency and v.direction == Direction.NORTH]
        assert len(ambulances) >= 1
        assert state.lanes[Direction.NORTH].emergency_flag is True

    def test_vehicle_has_required_fields(self):
        """Spawned vehicle must have all required dataclass fields."""
        eng   = make_engine()
        state = TrafficState()
        eng.trigger_emergency(Direction.SOUTH, state)

        v = eng.vehicles[0]
        assert hasattr(v, "id")
        assert hasattr(v, "direction")
        assert hasattr(v, "vehicle_type")
        assert hasattr(v, "wait_time")
        assert hasattr(v, "position")
        assert hasattr(v, "speed")
        assert hasattr(v, "state")

    def test_vehicle_id_unique(self):
        """Every spawned vehicle must have a unique ID."""
        eng   = make_engine()
        state = TrafficState()
        for d in Direction:
            eng.trigger_emergency(d, state)

        ids = [v.id for v in eng.vehicles]
        assert len(ids) == len(set(ids))


class TestAccidentSimulation:
    def test_trigger_accident_blocks_lane(self):
        """Triggering an accident must mark the lane as blocked."""
        eng   = make_engine()
        state = TrafficState()
        eng.trigger_accident(Direction.EAST, state)
        assert state.lanes[Direction.EAST].blocked is True

    def test_only_one_accident_at_a_time(self):
        """Second accident trigger while first is active must be ignored."""
        eng   = make_engine()
        state = TrafficState()
        eng.trigger_accident(Direction.EAST, state)
        active_before = eng._accident_lane
        eng.trigger_accident(Direction.WEST, state)   # should be ignored
        assert eng._accident_lane == active_before

    def test_accident_clears_after_duration(self):
        """Blocked lane should clear after accident duration elapses."""
        eng   = make_engine()
        state = TrafficState()
        eng.trigger_accident(Direction.NORTH, state)
        eng._accident_duration = 1.0   # force short duration for test

        # Simulate enough time
        for _ in range(100):
            eng._update_accidents(state, 0.02)

        assert state.lanes[Direction.NORTH].blocked is False


class TestReset:
    def test_reset_clears_vehicles(self):
        """After reset, vehicle list must be empty."""
        eng   = make_engine()
        state = TrafficState()
        eng.trigger_emergency(Direction.NORTH, state)
        eng.trigger_emergency(Direction.SOUTH, state)
        assert len(eng.vehicles) > 0

        eng.reset(state)
        assert len(eng.vehicles) == 0

    def test_reset_clears_lane_counts(self):
        """After reset, all lane vehicle counts must be 0."""
        eng   = make_engine()
        state = TrafficState()
        eng.trigger_emergency(Direction.NORTH, state)
        eng.reset(state)

        for lane in state.lanes.values():
            assert lane.vehicle_count == 0
            assert lane.emergency_flag is False

    def test_reset_total_cleared(self):
        """After reset, total_cleared must be 0."""
        state = TrafficState()
        state.total_cleared = 99
        eng   = make_engine()
        eng.reset(state)
        assert state.total_cleared == 0


class TestPeakHourDetection:
    def test_peak_hour_triggers_above_threshold(self):
        """is_peak_hour should become True when sustained count > threshold."""
        eng   = make_engine()
        state = TrafficState()

        # Manually set vehicle counts above threshold
        for lane in state.lanes.values():
            lane.vehicle_count = 7   # 4 lanes × 7 = 28 > threshold(20)

        # Simulate sufficient time above threshold
        for _ in range(1000):
            eng._check_peak_hour(state, 0.02)

        assert state.is_peak_hour is True

    def test_peak_hour_clears_when_below(self):
        """is_peak_hour should drop to False when count stays below threshold."""
        eng   = make_engine()
        state = TrafficState(is_peak_hour=True)
        eng.time_above = 20.0   # was above threshold

        # Now counts are 0 (below threshold)
        for _ in range(1100):
            eng._check_peak_hour(state, 0.02)

        assert state.is_peak_hour is False


class TestLaneSync:
    def test_sync_counts_match_vehicle_list(self):
        """Lane vehicle_count must match number of non-cleared vehicles in list."""
        eng   = make_engine()
        state = TrafficState()

        # Manually add vehicles
        from core.simulation import _next_id, _lane_geometry
        for d in Direction:
            start, stop, exit_ = _lane_geometry(d)
            v = Vehicle(id=_next_id(), direction=d,
                        vehicle_type="car", position=start,
                        start_pos=start, stop_pos=stop, exit_pos=exit_)
            eng.vehicles.append(v)

        eng._sync_lane_counts(state)

        for d in Direction:
            expected = sum(1 for v in eng.vehicles
                           if v.direction == d and v.state != "cleared")
            assert state.lanes[d].vehicle_count == expected
