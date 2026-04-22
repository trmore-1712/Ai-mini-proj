"""
core/state.py
=============
Core data models for the Smart Adaptive Traffic Signal Controller.
Defines TrafficState, LaneState, SignalPhase, Direction, and SignalAction enums.

Viva note: The 7-tuple `as_tuple()` produces a hashable state representation
used by BFS, A*, and Beam Search as keys in closed lists / priority queues.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SignalPhase(Enum):
    """Possible signal phases at the 4-way intersection."""
    NS_GREEN  = "NS_GREEN"           # North-South green, East-West red
    EW_GREEN  = "EW_GREEN"           # East-West green, North-South red
    YELLOW    = "YELLOW"             # Brief yellow transition (visual only)
    EMERGENCY_OVERRIDE = "EMERGENCY_OVERRIDE"
    PEDESTRIAN = "PEDESTRIAN"        # Future extension


class Direction(Enum):
    """The four road directions entering the intersection."""
    NORTH = "N"
    SOUTH = "S"
    EAST  = "E"
    WEST  = "W"


class SignalAction(Enum):
    """Actions the AI engine can take to control signals."""
    EXTEND_CURRENT_GREEN  = "extend"      # +10s to current phase
    SWITCH_SIGNAL         = "switch"      # Flip NS ↔ EW green
    EMERGENCY_OVERRIDE    = "emergency"   # Immediate green for emergency lane
    PEDESTRIAN_ALLOW      = "pedestrian"  # Trigger pedestrian phase (future)
    SHORTEN_CURRENT_GREEN = "shorten"     # −5s (prevent starvation)


# ---------------------------------------------------------------------------
# Lane State
# ---------------------------------------------------------------------------

@dataclass
class LaneState:
    """
    Represents the real-time state of one lane (direction).

    Attributes:
        direction       : One of N / S / E / W
        vehicle_count   : Number of vehicles currently queued
        avg_wait_time   : Average wait time of queued vehicles (seconds)
        emergency_flag  : True when an ambulance / fire engine is queued
        blocked         : True when an accident has closed the lane
        throughput      : Vehicles cleared during the current cycle
        cycles_since_green: How many full cycles since this direction last had GREEN
    """
    direction:          Direction
    vehicle_count:      int   = 0
    avg_wait_time:      float = 0.0
    emergency_flag:     bool  = False
    blocked:            bool  = False
    throughput:         int   = 0
    cycles_since_green: int   = 0


# ---------------------------------------------------------------------------
# Traffic State (main state object passed everywhere)
# ---------------------------------------------------------------------------

@dataclass
class TrafficState:
    """
    Full intersection state at a single point in time.

    This is the *state node* used by every search algorithm.
    `as_tuple()` returns a hashable version for closed-list deduplication.
    """

    # One LaneState per direction
    lanes: Dict[Direction, LaneState] = field(
        default_factory=lambda: {
            Direction.NORTH: LaneState(Direction.NORTH),
            Direction.SOUTH: LaneState(Direction.SOUTH),
            Direction.EAST:  LaneState(Direction.EAST),
            Direction.WEST:  LaneState(Direction.WEST),
        }
    )

    current_phase:      SignalPhase = SignalPhase.NS_GREEN
    phase_timer:        float = 30.0   # seconds remaining in current phase
    yellow_timer:       float = 0.0    # > 0 while yellow transition is active
    total_elapsed:      float = 0.0    # total simulation time (seconds)
    cycle_count:        int   = 0      # full NS→EW→NS cycles completed
    is_peak_hour:       bool  = False
    algorithm_used:     str   = "A*"
    last_decision_cost: float = 0.0
    paused:             bool  = False
    current_green_time: float = 0.0    # tracked in controller to enforce min_green

    # Starvation tracking at the phase level
    cycles_since_green_NS: int = 0
    cycles_since_green_EW: int = 0

    # Stats for the HUD chart
    total_cleared:      int   = 0
    wait_history_NS:    list  = field(default_factory=list)
    wait_history_EW:    list  = field(default_factory=list)
    time_history:       list  = field(default_factory=list)

    # -----------------------------------------------------------------------
    # Convenience properties
    # -----------------------------------------------------------------------

    @property
    def vehicles_NS(self) -> int:
        return (self.lanes[Direction.NORTH].vehicle_count +
                self.lanes[Direction.SOUTH].vehicle_count)

    @property
    def vehicles_EW(self) -> int:
        return (self.lanes[Direction.EAST].vehicle_count +
                self.lanes[Direction.WEST].vehicle_count)

    @property
    def avg_wait_NS(self) -> float:
        n = self.lanes[Direction.NORTH]
        s = self.lanes[Direction.SOUTH]
        return (n.avg_wait_time + s.avg_wait_time) / 2

    @property
    def avg_wait_EW(self) -> float:
        e = self.lanes[Direction.EAST]
        w = self.lanes[Direction.WEST]
        return (e.avg_wait_time + w.avg_wait_time) / 2

    @property
    def emergency_NS(self) -> bool:
        return (self.lanes[Direction.NORTH].emergency_flag or
                self.lanes[Direction.SOUTH].emergency_flag)

    @property
    def emergency_EW(self) -> bool:
        return (self.lanes[Direction.EAST].emergency_flag or
                self.lanes[Direction.WEST].emergency_flag)

    @property
    def total_vehicles(self) -> int:
        return sum(l.vehicle_count for l in self.lanes.values())

    def as_tuple(self) -> tuple:
        """
        Hashable 7-tuple state representation.
        Used as keys in BFS visited sets and A* closed lists.

        Viva: This represents the minimal information needed to distinguish
        two states for the purpose of signal decision-making.
        """
        return (
            self.vehicles_NS,
            self.vehicles_EW,
            round(self.avg_wait_NS, 1),
            round(self.avg_wait_EW, 1),
            self.emergency_NS,
            self.emergency_EW,
            self.current_phase.value,
        )

    def clone(self) -> "TrafficState":
        """
        Return a shallow-enough copy for look-ahead simulation.
        Lane states are cloned so search algorithms don't corrupt live state.
        """
        import copy
        new = TrafficState(
            lanes={d: LaneState(
                direction=l.direction,
                vehicle_count=l.vehicle_count,
                avg_wait_time=l.avg_wait_time,
                emergency_flag=l.emergency_flag,
                blocked=l.blocked,
                throughput=l.throughput,
                cycles_since_green=l.cycles_since_green,
            ) for d, l in self.lanes.items()},
            current_phase=self.current_phase,
            phase_timer=self.phase_timer,
            yellow_timer=self.yellow_timer,
            total_elapsed=self.total_elapsed,
            cycle_count=self.cycle_count,
            is_peak_hour=self.is_peak_hour,
            algorithm_used=self.algorithm_used,
            last_decision_cost=self.last_decision_cost,
            cycles_since_green_NS=self.cycles_since_green_NS,
            cycles_since_green_EW=self.cycles_since_green_EW,
            total_cleared=self.total_cleared,
            current_green_time=self.current_green_time,
        )
        return new
