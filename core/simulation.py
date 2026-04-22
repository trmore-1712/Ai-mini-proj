"""
core/simulation.py
==================
Vehicle spawning, movement, wait-time tracking, accident simulation,
peak-hour detection, and lane management for the 4-way intersection.

Key classes:
    Vehicle          — individual vehicle data
    SimulationEngine — update loop called every game tick
"""

import random
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from core.state import TrafficState, LaneState, SignalPhase, Direction, SignalAction
from core.events import bus, EVT_EMERGENCY_DETECTED, EVT_ACCIDENT_OCCURRED
from core.events import EVT_PEAK_HOUR_START, EVT_PEAK_HOUR_END, EVT_VEHICLE_CLEARED


# ---------------------------------------------------------------------------
# Vehicle data model
# ---------------------------------------------------------------------------

_vid_counter = 0

def _next_id() -> int:
    global _vid_counter
    _vid_counter += 1
    return _vid_counter


@dataclass
class Vehicle:
    """
    One vehicle travelling toward the intersection from a given direction.

    Pixel position is used by the renderer to draw the vehicle.
    `state` tracks lifecycle: spawned → waiting → moving → cleared.
    """
    id:            int
    direction:     Direction
    vehicle_type:  str           # "car" | "bus" | "ambulance" | "truck"
    is_emergency:  bool  = False
    wait_time:     float = 0.0   # seconds spent waiting at red
    position:      tuple = (0, 0)
    speed:         float = 2.0   # pixels per tick (when GREEN)
    state:         str   = "waiting"   # "waiting" | "moving" | "cleared"
    color:         tuple = (200, 200, 200)
    flash_state:   bool  = False        # for ambulance siren animation
    flash_timer:   float = 0.0

    # Pixel path endpoints assigned by renderer layout (set externally)
    start_pos:    tuple  = (0, 0)
    stop_pos:     tuple  = (0, 0)   # where it stops at red
    exit_pos:     tuple  = (0, 0)   # where it leaves the screen
    progress:     float  = 0.0      # 0.0 = at start, 1.0 = cleared

    def is_green(self, state: TrafficState) -> bool:
        """True when this vehicle's direction has a green light."""
        if state.current_phase == SignalPhase.EMERGENCY_OVERRIDE:
            # Only the emergency direction gets to move
            return self.is_emergency
        if state.current_phase in (SignalPhase.NS_GREEN,):
            return self.direction in (Direction.NORTH, Direction.SOUTH)
        if state.current_phase in (SignalPhase.EW_GREEN,):
            return self.direction in (Direction.EAST, Direction.WEST)
        return False   # YELLOW / PEDESTRIAN — no movement


# ---------------------------------------------------------------------------
# Vehicle type palette
# ---------------------------------------------------------------------------

_VEHICLE_TYPES = ["car", "car", "car", "bus", "truck"]   # weighted by frequency

_CAR_COLORS = [
    (52,  152, 219),   # dodger blue
    (46,  204, 113),   # emerald
    (155, 89,  182),   # amethyst
    (230, 126,  34),   # carrot
    (241, 196,  15),   # sunflower
    (149, 165, 166),   # concrete
    (26,  188, 156),   # turquoise
    (231,  76,  60),   # alizarin
]

_BUS_COLOR     = (243, 156,  18)   # orange
_TRUCK_COLOR   = (127, 140, 141)   # grey
_AMBU_COLOR    = (255, 255, 255)   # white (flashing red/blue via flash_state)


# ---------------------------------------------------------------------------
# Intersection pixel layout constants (matched to renderer)
# ---------------------------------------------------------------------------

# Centre of the intersection viewport
CX, CY = 430, 310

# Half-width of road (lane group)
ROAD_HALF = 40
# How far vehicles spawn from centre
SPAWN_DIST = 240
# Distance from centre where vehicles stop at red light
STOP_DIST  = 70


def _lane_geometry(direction: Direction):
    """
    Returns (start_pos, stop_pos, exit_pos) in pixels for a given direction.
    These are the three key waypoints of a vehicle's journey.
    """
    if direction == Direction.NORTH:
        sx, sy = CX - 20, CY - SPAWN_DIST
        stop   = (CX - 20, CY - STOP_DIST)
        exit_  = (CX - 20, CY + SPAWN_DIST)
    elif direction == Direction.SOUTH:
        sx, sy = CX + 20, CY + SPAWN_DIST
        stop   = (CX + 20, CY + STOP_DIST)
        exit_  = (CX + 20, CY - SPAWN_DIST)
    elif direction == Direction.EAST:
        sx, sy = CX + SPAWN_DIST, CY - 20
        stop   = (CX + STOP_DIST, CY - 20)
        exit_  = (CX - SPAWN_DIST, CY - 20)
    else:  # WEST
        sx, sy = CX - SPAWN_DIST, CY + 20
        stop   = (CX - STOP_DIST, CY + 20)
        exit_  = (CX + SPAWN_DIST, CY + 20)
    return (sx, sy), stop, exit_


# ---------------------------------------------------------------------------
# Simulation Engine
# ---------------------------------------------------------------------------

class SimulationEngine:
    """
    Drives vehicle lifecycle each game tick.

    Steps per tick (via `update`):
      1. Spawn new vehicles probabilistically
      2. Move vehicles that have GREEN
      3. Accumulate wait time for vehicles on RED
      4. Check / resolve accidents
      5. Detect peak-hour mode
      6. Clear vehicles that have passed through
      7. Sync counts back to TrafficState.lanes
    """

    def __init__(self, config: dict):
        self.spawn_rate_normal  = config.get("spawn_rate_normal",  0.8)
        self.spawn_rate_peak    = config.get("spawn_rate_peak",    2.5)
        self.emergency_prob     = config.get("emergency_probability", 0.003)
        self.accident_prob      = config.get("accident_probability",  0.001)
        self.peak_threshold     = config.get("peak_hour_threshold",   20)
        self.peak_window        = config.get("peak_hour_window_seconds", 15)

        self.vehicles:    List[Vehicle] = []
        self.tick:        int   = 0
        self.time_above:  float = 0.0   # seconds total_vehicles > threshold
        self.time_below:  float = 0.0   # seconds below when in peak

        # Accident tracking
        self._accident_lane:     Optional[Direction] = None
        self._accident_timer:    float = 0.0
        self._accident_duration: float = 0.0

        self._scenario_overrides: dict = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, state: TrafficState, dt: float) -> None:
        """Advance simulation by dt seconds. Mutates state in-place."""
        if state.paused:
            return

        self._spawn_vehicles(state, dt)
        self._move_vehicles(state, dt)
        self._update_wait_times(state, dt)
        self._update_accidents(state, dt)
        self._check_peak_hour(state, dt)
        self._clear_passed_vehicles(state)
        self._sync_lane_counts(state)
        self._update_chart_history(state, dt)
        self.tick += 1

    def trigger_emergency(self, direction: Direction, state: TrafficState) -> None:
        """Manually spawn an ambulance on the given direction."""
        v = self._make_vehicle(direction, force_emergency=True)
        self.vehicles.append(v)
        state.lanes[direction].emergency_flag = True
        bus.publish(EVT_EMERGENCY_DETECTED, direction)

    def trigger_accident(self, direction: Direction, state: TrafficState) -> None:
        """Block a lane to simulate an accident."""
        if self._accident_lane is not None:
            return   # only one accident at a time
        self._accident_lane     = direction
        self._accident_timer    = 0.0
        self._accident_duration = random.uniform(30, 60)
        state.lanes[direction].blocked = True
        bus.publish(EVT_ACCIDENT_OCCURRED, direction)

    def reset(self, state: TrafficState) -> None:
        """Clear all vehicles and reset simulation counters."""
        self.vehicles.clear()
        self.tick          = 0
        self.time_above    = 0.0
        self.time_below    = 0.0
        self._accident_lane = None
        self._accident_timer = 0.0
        # Reset all lane states
        for lane in state.lanes.values():
            lane.vehicle_count      = 0
            lane.avg_wait_time      = 0.0
            lane.emergency_flag     = False
            lane.blocked            = False
            lane.throughput         = 0
            lane.cycles_since_green = 0
        state.is_peak_hour       = False
        state.total_cleared      = 0
        state.wait_history_NS.clear()
        state.wait_history_EW.clear()
        state.time_history.clear()

    def load_scenario(self, scenario: dict) -> None:
        """Override spawn rates etc. from a scenario JSON dict."""
        self._scenario_overrides = scenario
        sim = scenario.get("simulation", {})
        if "spawn_rate_normal"      in sim: self.spawn_rate_normal = sim["spawn_rate_normal"]
        if "spawn_rate_peak"        in sim: self.spawn_rate_peak   = sim["spawn_rate_peak"]
        if "emergency_probability"  in sim: self.emergency_prob    = sim["emergency_probability"]
        if "accident_probability"   in sim: self.accident_prob     = sim["accident_probability"]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _current_spawn_rate(self, state: TrafficState) -> float:
        rate = self.spawn_rate_peak if state.is_peak_hour else self.spawn_rate_normal
        # Allow scenario overrides
        return self._scenario_overrides.get("spawn_rate_override", rate)

    def _spawn_vehicles(self, state: TrafficState, dt: float) -> None:
        """Probabilistically spawn vehicles each tick."""
        rate = self._current_spawn_rate(state)

        for direction in Direction:
            lane = state.lanes[direction]
            if lane.blocked:
                continue
            # Base spawn probability this tick
            prob = min(rate * dt, 0.9)
            if random.random() < prob:
                # Emergency vehicle?
                is_emergency = random.random() < self.emergency_prob
                v = self._make_vehicle(direction, force_emergency=is_emergency)
                self.vehicles.append(v)
                if is_emergency:
                    lane.emergency_flag = True
                    bus.publish(EVT_EMERGENCY_DETECTED, direction)

    def _make_vehicle(self, direction: Direction,
                      force_emergency: bool = False) -> Vehicle:
        """Construct a new Vehicle with correct geometry for its direction."""
        is_emergency = force_emergency
        if is_emergency:
            vtype = "ambulance"
            color = _AMBU_COLOR
            speed = 3.5
        else:
            vtype = "car"  # Enforce uniform shape
            color = (52, 152, 219) # Uniform blue color
            speed = random.uniform(2.0, 3.0)

        start, stop, exit_ = _lane_geometry(direction)

        # Stagger spawn position within lane
        offset = random.randint(0, 20)
        if direction == Direction.NORTH:
            start = (start[0], start[1] - offset)
        elif direction == Direction.SOUTH:
            start = (start[0], start[1] + offset)
        elif direction == Direction.EAST:
            start = (start[0] + offset, start[1])
        else:
            start = (start[0] - offset, start[1])

        return Vehicle(
            id=_next_id(),
            direction=direction,
            vehicle_type=vtype,
            is_emergency=is_emergency,
            position=start,
            start_pos=start,
            stop_pos=stop,
            exit_pos=exit_,
            speed=speed,
            color=color,
        )

    def _move_vehicles(self, state: TrafficState, dt: float) -> None:
        """Move vehicles that currently have a green light."""
        for v in self.vehicles:
            if v.state == "cleared":
                continue

            green = v.is_green(state)

            if green:
                v.state = "moving"
                # Move toward exit_pos in small steps each tick
                tx, ty = v.exit_pos
                px, py = v.position
                dx, dy = tx - px, ty - py
                dist   = math.hypot(dx, dy)
                if dist < v.speed * 60 * dt + 1:
                    v.position = v.exit_pos
                    v.state    = "cleared"
                else:
                    step = v.speed * 60 * dt / dist
                    v.position = (px + dx * step, py + dy * step)
            else:
                # Move toward stop_pos if not already there
                v.state = "waiting"
                tx, ty  = v.stop_pos
                px, py  = v.position
                dx, dy  = tx - px, ty - py
                dist    = math.hypot(dx, dy)
                step_px = v.speed * 60 * dt * 0.6   # move slower while queuing
                if dist > step_px:
                    ratio  = step_px / dist
                    v.position = (px + dx * ratio, py + dy * ratio)

            # Flash ambulance siren
            if v.is_emergency:
                v.flash_timer += dt
                if v.flash_timer >= 0.3:
                    v.flash_timer = 0.0
                    v.flash_state = not v.flash_state

    def _update_wait_times(self, state: TrafficState, dt: float) -> None:
        """Accumulate wait time for vehicles stuck on RED."""
        for v in self.vehicles:
            if v.state == "waiting":
                v.wait_time += dt

    def _update_accidents(self, state: TrafficState, dt: float) -> None:
        """Count down accident timer and unblock lane when done."""
        if self._accident_lane is None:
            return
        self._accident_timer += dt
        if self._accident_timer >= self._accident_duration:
            # Clear accident
            state.lanes[self._accident_lane].blocked = False
            self._accident_lane = None
            self._accident_timer = 0.0

        # Also check for random new accident
        elif random.random() < self.accident_prob * dt:
            # Only if no current accident
            pass  # already handled above

    def _check_peak_hour(self, state: TrafficState, dt: float) -> None:
        """Toggle peak_hour mode based on sustained vehicle count."""
        total = state.total_vehicles
        if total > self.peak_threshold:
            self.time_above += dt
            self.time_below  = 0.0
            if self.time_above >= self.peak_window and not state.is_peak_hour:
                state.is_peak_hour = True
                bus.publish(EVT_PEAK_HOUR_START)
        else:
            self.time_below += dt
            if self.time_below >= 20.0 and state.is_peak_hour:
                state.is_peak_hour = False
                self.time_above    = 0.0
                bus.publish(EVT_PEAK_HOUR_END)

    def _clear_passed_vehicles(self, state: TrafficState) -> None:
        """Remove vehicles that have exited and update stats."""
        newly_cleared = [v for v in self.vehicles if v.state == "cleared"]
        for v in newly_cleared:
            # Update throughput counter for the lane
            state.lanes[v.direction].throughput += 1
            state.total_cleared += 1

            # Clear emergency flag if this was the emergency vehicle
            if v.is_emergency:
                state.lanes[v.direction].emergency_flag = False
            bus.publish(EVT_VEHICLE_CLEARED, v)

        self.vehicles = [v for v in self.vehicles if v.state != "cleared"]

    def _sync_lane_counts(self, state: TrafficState) -> None:
        """Re-compute vehicle_count and avg_wait_time in each LaneState."""
        counts:    Dict[Direction, int]   = {d: 0   for d in Direction}
        wait_sums: Dict[Direction, float] = {d: 0.0 for d in Direction}

        for v in self.vehicles:
            counts[v.direction]    += 1
            wait_sums[v.direction] += v.wait_time

        for d in Direction:
            lane = state.lanes[d]
            lane.vehicle_count = counts[d]
            lane.avg_wait_time = (wait_sums[d] / counts[d]) if counts[d] > 0 else 0.0

    def _update_chart_history(self, state: TrafficState, dt: float) -> None:
        """Append to wait-time history for the live chart (every ~1s)."""
        if self.tick % 60 == 0:   # every ~1 second at 60fps
            state.wait_history_NS.append(state.avg_wait_NS)
            state.wait_history_EW.append(state.avg_wait_EW)
            state.time_history.append(state.total_elapsed)
            # Keep only last 60 data points (60s of history)
            if len(state.time_history) > 60:
                state.wait_history_NS.pop(0)
                state.wait_history_EW.pop(0)
                state.time_history.pop(0)
