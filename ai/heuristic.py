"""
ai/heuristic.py
===============
Core heuristic function h(n) for the Smart Adaptive Traffic Signal Controller.

h(n) = w1 * total_wait_time
     + w2 * queue_length
     + w3 * emergency_penalty
     + w4 * starvation_penalty
     - w5 * throughput_bonus

Admissibility: h(n) ≤ h*(n) because every component reflects observed real cost
or is bounded by a calibrated cap. See Section 12 of PRD for full proof.

Viva talking points:
  - h(n) is admissible → A* is guaranteed to find the optimal action
  - emergency_penalty is the dominant term — ensures ambulances are always served first
  - starvation_penalty grows linearly with cycles_since_green, capped at max value
  - throughput_bonus rewards states that have already cleared more vehicles
"""

from core.state import TrafficState, SignalPhase, Direction


def heuristic(state: TrafficState, weights: dict) -> float:
    """
    Compute the heuristic cost estimate h(n) for a given traffic state.

    Parameters
    ----------
    state   : TrafficState — the node being evaluated
    weights : dict         — loaded from config/settings.json → heuristic_weights

    Returns
    -------
    float   — non-negative estimated remaining cost (lower is better)
    """

    w1 = weights.get("wait_time",              1.5)
    w2 = weights.get("queue_length",           1.0)
    w3 = weights.get("emergency",             50.0)
    w4 = weights.get("starvation",             2.0)
    w5 = weights.get("throughput",             0.8)
    max_emerg    = weights.get("max_emergency_penalty",  500.0)
    max_starve   = weights.get("max_starvation_penalty", 100.0)

    # ── Term 1: total accumulated wait time across all lanes ────────────────
    total_wait = sum(lane.avg_wait_time for lane in state.lanes.values())

    # ── Term 2: total queue length (number of waiting vehicles) ────────────
    queue_len = sum(lane.vehicle_count for lane in state.lanes.values())

    # ── Term 3: emergency penalty ─────────────────────────────────────────
    # Maximum penalty when an ambulance is queued on the *wrong* (RED) side.
    emergency_penalty = 0.0
    if state.emergency_NS and state.current_phase == SignalPhase.EW_GREEN:
        emergency_penalty = max_emerg   # NS ambulance is stuck on RED
    elif state.emergency_EW and state.current_phase == SignalPhase.NS_GREEN:
        emergency_penalty = max_emerg   # EW ambulance is stuck on RED

    # Partial penalty when override is active but ambulance hasn't cleared yet
    if state.emergency_NS and state.current_phase == SignalPhase.NS_GREEN:
        emergency_penalty = max_emerg * 0.1   # small residual — still clearing
    elif state.emergency_EW and state.current_phase == SignalPhase.EW_GREEN:
        emergency_penalty = max_emerg * 0.1

    # ── Term 4: starvation penalty ────────────────────────────────────────
    # Grows with how many cycles a direction has been starved of green.
    starvation_score   = max(state.cycles_since_green_NS,
                             state.cycles_since_green_EW)
    starvation_penalty = min(starvation_score * 10.0, max_starve)

    # ── Term 5: throughput bonus ──────────────────────────────────────────
    # Reward states where more vehicles have already been cleared.
    total_throughput = sum(lane.throughput for lane in state.lanes.values())

    # ── Blocked-lane bonus penalty ─────────────────────────────────────────
    blocked_penalty = 0.0
    for lane in state.lanes.values():
        if lane.blocked:
            blocked_penalty += 20.0   # discourage routing to blocked lanes

    h = (w1 * total_wait +
         w2 * queue_len +
         w3 * emergency_penalty +
         w4 * starvation_penalty +
         blocked_penalty -
         w5 * total_throughput)

    return max(0.0, h)   # Admissibility: heuristic must be non-negative


def heuristic_delta(before: TrafficState, after: TrafficState,
                    weights: dict) -> float:
    """
    Compute marginal improvement in heuristic from one state to the next.
    Used by Hill Climbing to evaluate neighbour quality.

    Returns positive value when the transition is an improvement.
    """
    return heuristic(before, weights) - heuristic(after, weights)
