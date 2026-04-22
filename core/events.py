"""
core/events.py
==============
Lightweight event bus for simulation events.
Allows decoupled communication between simulation engine, AI engine, and renderer.

Events published: emergency_detected, accident_occurred, peak_hour_start,
                  peak_hour_end, vehicle_cleared, signal_switched
"""

from typing import Callable, Dict, List, Any


class EventBus:
    """
    Simple publish/subscribe event system.
    Modules subscribe by registering callbacks for named event types.
    The simulation engine publishes events; renderer and AI react.
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Register a callback for a given event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def publish(self, event_type: str, data: Any = None) -> None:
        """Fire all callbacks registered for this event type."""
        for cb in self._listeners.get(event_type, []):
            cb(data)

    def clear(self) -> None:
        """Remove all listeners (called on simulation reset)."""
        self._listeners.clear()


# ---------------------------------------------------------------------------
# Shared global event bus instance
# ---------------------------------------------------------------------------
bus = EventBus()

# Known event type constants (use these strings everywhere for consistency)
EVT_EMERGENCY_DETECTED = "emergency_detected"   # data: Direction
EVT_ACCIDENT_OCCURRED  = "accident_occurred"    # data: Direction
EVT_PEAK_HOUR_START    = "peak_hour_start"      # data: None
EVT_PEAK_HOUR_END      = "peak_hour_end"        # data: None
EVT_VEHICLE_CLEARED    = "vehicle_cleared"      # data: Vehicle
EVT_SIGNAL_SWITCHED    = "signal_switched"      # data: SignalPhase
EVT_SIMULATION_RESET   = "simulation_reset"     # data: None
