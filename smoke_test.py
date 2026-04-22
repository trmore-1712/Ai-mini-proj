"""Integration smoke test — runs without pygame, verifies all AI modules."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from config.loader import load_config, load_scenario, merge_scenario
from core.state import TrafficState, Direction, SignalPhase, SignalAction
from core.simulation import SimulationEngine
from core.signal_controller import SignalController
from ai.ai_engine import AIEngine
from ai.astar import AStarSearch
from ai.beam_search import BeamSearch
from ai.hill_climbing import HillClimbing
from ai.bfs_dfs import BFSSearch, DFSSearch
from ai.ao_star import AOStar
from ai.minimax import MinimaxAB
from ai.heuristic import heuristic

config = load_config("config/settings.json")
w      = config["heuristic_weights"]
cfg    = config["ai"]

print("=" * 56)
print("  SMART TRAFFIC AI -- Integration Smoke Test")
print("=" * 56)

# ── 1. Simulate 300 ticks ────────────────────────────────────
state = TrafficState()
sim   = SimulationEngine(config["simulation"])
ctrl  = SignalController(config["signals"])
ai    = AIEngine(cfg, w)

for i in range(300):
    sim.update(state, 1/60)
    ctrl.update(state, 1/60)
    if i % 30 == 0:
        action = ai.decide(state)
        ctrl.apply_action(action, state)

print(f"[300-tick sim]  elapsed={state.total_elapsed:.1f}s | "
      f"cleared={state.total_cleared} | algo={state.algorithm_used} | "
      f"cost={state.last_decision_cost:.2f}")
assert state.total_elapsed > 0
print("  PASS: simulation tick loop OK")

# ── 2. Emergency override ────────────────────────────────────
state2 = TrafficState()
sim2   = SimulationEngine(config["simulation"])
ai2    = AIEngine(cfg, w)
sim2.trigger_emergency(Direction.NORTH, state2)
act2   = ai2.decide(state2)
print(f"[Emergency]     action={act2.value} | algo={state2.algorithm_used}")
assert act2 in (SignalAction.EMERGENCY_OVERRIDE, SignalAction.EXTEND_CURRENT_GREEN)
print("  PASS: emergency override OK")

# ── 3. Accident / AO* ────────────────────────────────────────
state3 = TrafficState()
sim3   = SimulationEngine(config["simulation"])
ai3    = AIEngine(cfg, w)
sim3.trigger_accident(Direction.EAST, state3)
act3   = ai3.decide(state3)
print(f"[Accident/AO*]  action={act3.value} | algo={state3.algorithm_used}")
assert state3.lanes[Direction.EAST].blocked
assert state3.algorithm_used == "AO*"
print("  PASS: accident + AO* OK")

# ── 4. Peak hour / Beam Search ───────────────────────────────
state4 = TrafficState(is_peak_hour=True)
ai4    = AIEngine(cfg, w)
act4   = ai4.decide(state4)
print(f"[Peak hour]     action={act4.value} | algo={state4.algorithm_used}")
assert state4.algorithm_used == "Beam Search"
print("  PASS: peak hour + Beam Search OK")

# ── 5. All 7 algorithms ──────────────────────────────────────
print("\n[All 7 algorithms]")
st = TrafficState()
algos = {
    "A*"         : AStarSearch(cfg, w).decide(st),
    "Beam Search": BeamSearch(cfg, w).decide(st),
    "Hill Climb" : HillClimbing(cfg, w).decide(st),
    "BFS"        : BFSSearch(cfg, w).decide(st),
    "DFS"        : DFSSearch(cfg, w).decide(st),
    "AO*"        : AOStar(cfg, w).decide(st),
    "Minimax+AB" : MinimaxAB(cfg, w).decide(st),
}
for name, act in algos.items():
    assert isinstance(act, SignalAction), f"{name} returned non-action"
    print(f"  {name:<14} -> {act.value}")

# ── 6. Scenario loading ──────────────────────────────────────
print("\n[Scenarios]")
for sc in ("normal", "peak_hour", "emergency", "accident"):
    s = load_scenario(sc)
    assert "simulation" in s, f"scenario {sc} missing simulation key"
    print(f"  {sc:<12} loaded OK | "
          f"spawn={s['simulation'].get('spawn_rate_normal','?')}")

# ── 7. State as_tuple / clone ────────────────────────────────
t   = state.as_tuple()
clone = state.clone()
assert len(t) == 7
assert clone.as_tuple() == state.as_tuple()
print("\n[State tuple]   length=7, clone matches PASS")

# ── 8. Heuristic admissibility check ────────────────────────
states_checked = 0
for count in range(0, 25, 5):
    for wait in range(0, 60, 15):
        s = TrafficState()
        for lane in s.lanes.values():
            lane.vehicle_count = count
            lane.avg_wait_time = float(wait)
            lane.throughput    = count * 2   # large bonus
        h = heuristic(s, w)
        assert h >= 0.0, f"h(n) negative: {h}"
        states_checked += 1
print(f"[Admissibility] h(n)>=0 for {states_checked} states PASS")

print()
print("=" * 56)
print("  ALL CHECKS PASSED -- System ready to run!")
print("  Launch with: python main.py")
print("=" * 56)
