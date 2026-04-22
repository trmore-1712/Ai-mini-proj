# Smart Adaptive Traffic Signal Controller
### AI Lab Mini-Project — Python + PyGame

> An AI-powered 4-way intersection controller using A\*, Beam Search, Hill Climbing, BFS/DFS, AO\*, and Minimax with Alpha-Beta Pruning — rendered in real-time with PyGame.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run simulation (normal scenario, A* algorithm)
python main.py

# 3. Run with specific scenario
python main.py --scenario peak_hour

# 4. Force a specific algorithm
python main.py --algorithm beam_search

# 5. Debug mode (shows state tuple on screen)
python main.py --debug
```

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume |
| `R` | Reset simulation |
| `E` | Spawn emergency vehicle (random direction) |
| `A` | Trigger accident (random lane) |
| `1` | Load Normal scenario |
| `2` | Load Peak Hour scenario |
| `3` | Load Emergency scenario |
| `4` | Load Accident scenario |
| `+` / `-` | Increase / decrease simulation speed |
| `F` | Toggle fullscreen |
| `D` | Toggle debug overlay |
| `F1` | Force A* |
| `F2` | Force Beam Search |
| `F3` | Force BFS (educational) |
| `F4` | Force DFS (educational) |
| `F5` | Force Hill Climbing |
| `F6` | Force Minimax + Alpha-Beta |
| `F7` | Auto mode (default) |
| `Esc` | Quit |

---

## 🗂️ Project Structure

```
smart_traffic_controller/
├── main.py                    # Entry point — game loop
├── core/
│   ├── state.py               # TrafficState dataclass + enums
│   ├── simulation.py          # Vehicle spawner, mover, accident logic
│   ├── signal_controller.py   # Signal phase manager, timer logic
│   └── events.py              # Event bus
├── ai/
│   ├── ai_engine.py           # Main AI decision dispatcher
│   ├── heuristic.py           # h(n) function
│   ├── astar.py               # A* search
│   ├── beam_search.py         # Beam Search
│   ├── hill_climbing.py       # Hill Climbing with random restarts
│   ├── bfs_dfs.py             # BFS and DFS (educational)
│   ├── ao_star.py             # AO* AND-OR graph planner
│   └── minimax.py             # Minimax + Alpha-Beta
├── renderer/
│   ├── renderer.py            # Master draw loop
│   ├── road.py                # Roads, lane markings, heat-maps
│   ├── vehicles.py            # Vehicle sprites & ambulance siren
│   ├── signals.py             # Animated traffic lights
│   └── hud.py                 # Dashboard, stats, algorithm trace
├── config/
│   ├── settings.json          # Master configuration
│   ├── loader.py              # Config + scenario loader
│   └── scenarios/
│       ├── normal.json
│       ├── peak_hour.json
│       ├── emergency.json
│       └── accident.json
└── tests/
    ├── test_heuristic.py
    ├── test_astar.py
    └── test_simulation.py
```

---

## 🧠 AI Algorithms

| Algorithm | When Used | Key Property |
|-----------|-----------|--------------|
| **A\*** | Normal traffic | Optimal with admissible heuristic |
| **Beam Search** | Peak hour (high congestion) | Speed vs optimality trade-off |
| **Hill Climbing** | Timer fine-tuning (post-A\*) | Local gradient descent, 3 random restarts |
| **BFS** | Educational mode | Complete, shallowest solution |
| **DFS** | Educational mode | Memory efficient, depth-limited |
| **AO\*** | Accident scenarios | AND-OR multi-goal decomposition |
| **Minimax + α-β** | Worst-case stress test | Adversarial game tree, pruning |

---

## 📐 Heuristic Function

```
h(n) = w1 × total_wait_time
     + w2 × queue_length
     + w3 × emergency_penalty
     + w4 × starvation_penalty
     − w5 × throughput_bonus

Default weights: w1=1.5, w2=1.0, w3=50.0, w4=2.0, w5=0.8
```

**Admissibility:** h(n) ≤ h\*(n) because every component reflects observed real cost and emergency/starvation penalties are capped. This guarantees A\* finds the **optimal** signal action.

---

## 🎭 Scenarios

| Scenario | Description | Algorithm Triggered |
|----------|-------------|---------------------|
| `normal` | Balanced traffic, no emergencies | A\* |
| `peak_hour` | 3× spawn rate, heavy congestion | Beam Search |
| `emergency` | High ambulance probability | Emergency Override |
| `accident` | Lane blockage mid-simulation | AO\* re-planning |

---

## 🧪 Run Tests

```bash
pytest tests/ -v
```

---

## 📊 Success Metrics (from PRD)

| Metric | Target |
|--------|--------|
| Average wait time reduction vs fixed-timer | ≥ 30% |
| Emergency clearance time | < 5 simulation seconds |
| Starvation prevention | No lane waits > 3 full cycles |
| Algorithm coverage | All 7 algorithms mapped and explainable |

---

## 🎓 Viva Preparation

**Q: What is the state representation?**
> 7-tuple: `(vehicles_NS, vehicles_EW, avg_wait_NS, avg_wait_EW, emergency_NS, emergency_EW, current_phase)` — hashable, used in BFS/A\* closed lists.

**Q: Why is your heuristic admissible?**
> Every component reflects real, observed cost or is capped. Therefore h(n) ≤ h\*(n) for all states.

**Q: Why A\* over greedy best-first?**
> A\* uses f(n) = g(n) + h(n) — balancing actual accumulated cost and future estimate — guaranteeing optimality. Greedy only uses h(n) and can miss globally optimal decisions.

**Q: When does Hill Climbing fail?**
> It can get stuck in local optima. We mitigate with 3 random restarts.

**Q: Explain AO\* in this context.**
> AO\* works on AND-OR graphs. In accident scenarios, the goal becomes an AND node: re-route traffic AND handle emergency — both must be satisfied. AO\* finds the minimum-cost solution tree.

---

*Built with Python 3.10+ · PyGame 2.5 · Matplotlib 3.8 · NumPy 1.26*
