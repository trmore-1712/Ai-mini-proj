# 🚦 Smart Adaptive Traffic Signal Controller (AI-Powered)
## Product Requirements Document (PRD)
**Version:** 1.0  
**Target Environment:** Antigravity IDE  
**Language Stack:** Python (Frontend + Backend)  
**Type:** AI Lab Mini-Project  
**Audience:** AI/CS Students + Lab Evaluators (Viva-Ready)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Goals & Success Metrics](#2-goals--success-metrics)
3. [System Architecture](#3-system-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Folder Structure](#5-folder-structure)
6. [Core Data Models](#6-core-data-models)
7. [AI Engine (Backend)](#7-ai-engine-backend)
8. [Simulation Engine](#8-simulation-engine)
9. [Frontend (PyGame UI)](#9-frontend-pygame-ui)
10. [Feature Specifications](#10-feature-specifications)
11. [Algorithm Implementations](#11-algorithm-implementations)
12. [Heuristic Function Design](#12-heuristic-function-design)
13. [API / Internal Interface Contracts](#13-api--internal-interface-contracts)
14. [UI Screens & Components](#14-ui-screens--components)
15. [Configuration & Parameters](#15-configuration--parameters)
16. [Build & Run Instructions](#16-build--run-instructions)
17. [Viva Preparation Notes](#17-viva-preparation-notes)
18. [Milestones & Delivery Plan](#18-milestones--delivery-plan)

---

## 1. Project Overview

### 1.1 Problem Statement

Traditional fixed-timer traffic signals fail under real-world variability — peak hours, emergency vehicles, accidents, and random surges. This project builds an **AI-driven adaptive traffic controller** that uses classical search and heuristic algorithms to dynamically compute optimal signal timings for a 4-way intersection.

### 1.2 What This System Does

- **Observes** real-time traffic state (vehicle count, wait time, emergency flags)
- **Searches** the signal action space using BFS, A*, Hill Climbing, and Beam Search
- **Decides** the best signal phase and duration using a heuristic cost function
- **Simulates** vehicles spawning, moving, waiting, and clearing — rendered live in PyGame
- **Handles** edge cases: ambulance priority, lane blockage, peak-hour surges, starvation prevention

### 1.3 Scope

| In Scope | Out of Scope |
|---|---|
| 4-way intersection (N, S, E, W) | Multi-intersection city network |
| 2 signal phases + emergency override | Full pedestrian phase timers |
| PyGame real-time visualization | Web-based frontend |
| All 7 algorithms (coded or explained) | Hardware/embedded deployment |
| Configurable simulation parameters | Cloud deployment |

---

## 2. Goals & Success Metrics

### 2.1 Functional Goals

- `G1` — Simulate a 4-way intersection with realistic vehicle flow
- `G2` — Implement A* for optimal signal switching with admissible heuristic
- `G3` — Implement emergency vehicle override with immediate green
- `G4` — Detect peak-hour congestion and invoke Beam Search
- `G5` — Prevent lane starvation using fairness constraint
- `G6` — Visualize entire state in real-time (signals, vehicles, wait times, algorithm trace)

### 2.2 Non-Functional Goals

- `N1` — UI must look like a real traffic simulation (top-down road view)
- `N2` — Simulation runs at 30 FPS minimum
- `N3` — Algorithm decision must complete in < 100ms per cycle
- `N4` — Codebase must be readable and well-commented (viva-friendly)

### 2.3 Success Metrics

| Metric | Target |
|---|---|
| Average wait time reduction vs fixed-timer | ≥ 30% improvement |
| Emergency clearance time | < 5 simulation seconds |
| Starvation prevention | No lane waits > 3 full cycles |
| Algorithm coverage (viva) | All 7 mapped and explainable |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAIN CONTROLLER                          │
│                     (main.py / game loop)                       │
└────────────┬────────────────────────────┬───────────────────────┘
             │                            │
             ▼                            ▼
┌────────────────────┐        ┌──────────────────────────┐
│  SIMULATION ENGINE │        │      AI DECISION ENGINE  │
│  (simulation.py)   │◄──────►│      (ai_engine.py)      │
│                    │  state │                          │
│  - Spawns vehicles │        │  - A* Search             │
│  - Moves vehicles  │        │  - Hill Climbing         │
│  - Tracks wait     │        │  - Beam Search           │
│  - Emits events    │        │  - BFS / DFS             │
│  - Accident sim    │        │  - AO* (explained)       │
└────────┬───────────┘        │  - Minimax/Alpha-Beta    │
         │                    │    (explained)           │
         ▼                    └──────────┬───────────────┘
┌────────────────────┐                   │ action
│  TRAFFIC STATE     │◄──────────────────┘
│  (state.py)        │
│                    │
│  - vehicles_NS     │
│  - vehicles_EW     │
│  - avg_wait_NS     │
│  - avg_wait_EW     │
│  - emergency_NS    │
│  - emergency_EW    │
│  - current_signal  │
│  - cycle_count     │
└────────┬───────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│                     PYGAME FRONTEND                            │
│                      (renderer.py)                             │
│                                                                │
│   ┌──────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│   │  Road & Junction │  │  HUD Dashboard  │  │  Algorithm  │ │
│   │  (top-down view) │  │  (stats panel)  │  │  Trace Log  │ │
│   └──────────────────┘  └─────────────────┘  └─────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### 3.1 Data Flow per Simulation Tick

```
Tick Start
   │
   ├─► Simulation Engine spawns/moves vehicles → updates TrafficState
   │
   ├─► Every N ticks → AI Engine reads TrafficState
   │       │
   │       ├─► Check emergency flag → Emergency Override if True
   │       ├─► Check congestion level → Select algorithm
   │       └─► Run selected algorithm → Return best Action
   │
   ├─► Apply Action → Update signal timers in TrafficState
   │
   └─► Renderer draws current frame (road, vehicles, signals, HUD)
```

---

## 4. Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| **Frontend** | `pygame` 2.x | Real-time 2D rendering, cross-platform, pure Python |
| **Backend Logic** | Pure Python 3.10+ | No external AI framework needed; all algorithms hand-coded |
| **Data Structures** | `dataclasses`, `heapq`, `collections.deque` | Priority queues for A*, BFS queues, clean state objects |
| **Charts/Stats** | `matplotlib` (embedded in pygame surface) | Live wait-time plots |
| **Config** | `json` / `dataclasses` | Easy parameter tweaking |
| **Logging** | Python `logging` module | Algorithm trace for viva display |
| **Testing** | `pytest` (optional) | Unit tests for heuristic and algorithm outputs |

### 4.1 Python Package Requirements (`requirements.txt`)

```
pygame==2.5.2
matplotlib==3.8.0
numpy==1.26.0
pytest==7.4.0
```

---

## 5. Folder Structure

```
smart_traffic_controller/
│
├── main.py                    # Entry point — game loop, init, event handler
│
├── core/
│   ├── __init__.py
│   ├── state.py               # TrafficState dataclass + enums
│   ├── simulation.py          # Vehicle spawner, mover, accident logic
│   ├── signal_controller.py   # Signal phase manager, timer logic
│   └── events.py              # Event bus (emergency_detected, accident, peak_hour)
│
├── ai/
│   ├── __init__.py
│   ├── ai_engine.py           # Main AI decision dispatcher
│   ├── heuristic.py           # h(n) function — core heuristic
│   ├── astar.py               # A* search for signal switching
│   ├── bfs_dfs.py             # BFS and DFS signal sequence explorer
│   ├── hill_climbing.py       # Local search for timing optimization
│   ├── beam_search.py         # Beam Search for peak-hour planning
│   ├── ao_star.py             # AO* explanation module (with pseudocode runner)
│   └── minimax.py             # Minimax + Alpha-Beta explanation module
│
├── renderer/
│   ├── __init__.py
│   ├── renderer.py            # Main pygame draw loop
│   ├── road.py                # Draw roads, lanes, zebra crossings
│   ├── vehicles.py            # Draw cars, buses, ambulances (sprites)
│   ├── signals.py             # Draw traffic lights (animated)
│   ├── hud.py                 # Dashboard: stats, algorithm trace, charts
│   └── assets/
│       ├── car.png
│       ├── ambulance.png
│       ├── bus.png
│       └── fonts/
│           └── mono.ttf
│
├── config/
│   ├── settings.json          # Simulation parameters (spawn rate, weights, etc.)
│   └── scenarios/
│       ├── normal.json        # Standard traffic
│       ├── peak_hour.json     # Heavy load scenario
│       ├── emergency.json     # Ambulance scenario
│       └── accident.json      # Lane blockage scenario
│
├── tests/
│   ├── test_heuristic.py
│   ├── test_astar.py
│   └── test_simulation.py
│
└── README.md
```

---

## 6. Core Data Models

### 6.1 TrafficState (`core/state.py`)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List

class SignalPhase(Enum):
    NS_GREEN = "NS_GREEN"      # North-South green, East-West red
    EW_GREEN = "EW_GREEN"      # East-West green, North-South red
    EMERGENCY_OVERRIDE = "EMERGENCY_OVERRIDE"
    PEDESTRIAN = "PEDESTRIAN"  # Optional / future

class Direction(Enum):
    NORTH = "N"
    SOUTH = "S"
    EAST  = "E"
    WEST  = "W"

@dataclass
class LaneState:
    direction: Direction
    vehicle_count: int = 0
    avg_wait_time: float = 0.0   # seconds
    emergency_flag: bool = False
    blocked: bool = False         # True during accident simulation
    throughput: int = 0           # vehicles cleared this cycle

@dataclass
class TrafficState:
    # Core state tuple (matches AI State Representation in problem statement)
    lanes: dict = field(default_factory=lambda: {
        Direction.NORTH: LaneState(Direction.NORTH),
        Direction.SOUTH: LaneState(Direction.SOUTH),
        Direction.EAST:  LaneState(Direction.EAST),
        Direction.WEST:  LaneState(Direction.WEST),
    })
    current_phase: SignalPhase = SignalPhase.NS_GREEN
    phase_timer: float = 0.0           # seconds remaining in current phase
    total_elapsed: float = 0.0
    cycle_count: int = 0
    is_peak_hour: bool = False
    algorithm_used: str = "A*"
    last_decision_cost: float = 0.0

    @property
    def vehicles_NS(self) -> int:
        return self.lanes[Direction.NORTH].vehicle_count + \
               self.lanes[Direction.SOUTH].vehicle_count

    @property
    def vehicles_EW(self) -> int:
        return self.lanes[Direction.EAST].vehicle_count + \
               self.lanes[Direction.WEST].vehicle_count

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
        return self.lanes[Direction.NORTH].emergency_flag or \
               self.lanes[Direction.SOUTH].emergency_flag

    @property
    def emergency_EW(self) -> bool:
        return self.lanes[Direction.EAST].emergency_flag or \
               self.lanes[Direction.WEST].emergency_flag

    def as_tuple(self) -> tuple:
        """Hashable state for search algorithms"""
        return (
            self.vehicles_NS, self.vehicles_EW,
            round(self.avg_wait_NS, 1), round(self.avg_wait_EW, 1),
            self.emergency_NS, self.emergency_EW,
            self.current_phase.value
        )
```

### 6.2 Signal Actions (`core/signal_controller.py`)

```python
from enum import Enum

class SignalAction(Enum):
    EXTEND_CURRENT_GREEN  = "extend"      # +10s to current phase
    SWITCH_SIGNAL         = "switch"      # Flip NS ↔ EW green
    EMERGENCY_OVERRIDE    = "emergency"   # Immediate green for emergency lane
    PEDESTRIAN_ALLOW      = "pedestrian"  # Trigger pedestrian phase (future)
    SHORTEN_CURRENT_GREEN = "shorten"     # -5s (prevent starvation)
```

### 6.3 Vehicle (`core/simulation.py`)

```python
@dataclass
class Vehicle:
    id: int
    direction: Direction
    vehicle_type: str          # "car", "bus", "ambulance", "truck"
    is_emergency: bool = False
    wait_time: float = 0.0
    position: tuple = (0, 0)   # Pixel position for renderer
    speed: float = 2.0         # Pixels per tick
    state: str = "waiting"     # "waiting", "moving", "cleared"
```

---

## 7. AI Engine (Backend)

### 7.1 AI Dispatcher (`ai/ai_engine.py`)

The dispatcher selects which algorithm to invoke based on current state conditions:

```python
class AIEngine:
    def decide(self, state: TrafficState) -> SignalAction:
        # Priority 1: Emergency override (bypasses all search)
        if state.emergency_NS or state.emergency_EW:
            return self._emergency_override(state)

        # Priority 2: Peak hour — use Beam Search (faster, parallel planning)
        if state.is_peak_hour:
            return self.beam_search.decide(state)

        # Priority 3: Normal — use A* for optimal decision
        return self.astar.decide(state)
```

**Algorithm Selection Matrix:**

| Condition | Algorithm | Reason |
|---|---|---|
| Emergency flag active | Emergency Override (direct) | Speed is critical |
| Peak hour (`vehicles > threshold`) | Beam Search | Explores top-k plans quickly |
| Accident / lane blocked | AO* style re-planning | Handles sub-goals |
| Normal traffic | A* Search | Optimal with heuristic |
| Fine-tune phase duration | Hill Climbing | Local optimization of timer |
| Exhaustive state explore (demo) | BFS / DFS | Educational coverage |

---

## 8. Simulation Engine

### 8.1 Vehicle Spawning Logic (`core/simulation.py`)

```python
class SimulationEngine:
    def __init__(self, config: dict):
        self.spawn_rate_normal  = config["spawn_rate_normal"]   # vehicles/second
        self.spawn_rate_peak    = config["spawn_rate_peak"]
        self.emergency_prob     = config["emergency_probability"]
        self.accident_prob      = config["accident_probability"]
        self.vehicles: List[Vehicle] = []
        self.tick = 0

    def update(self, state: TrafficState, dt: float):
        self._spawn_vehicles(state, dt)
        self._move_vehicles(state, dt)
        self._update_wait_times(state, dt)
        self._check_accidents(state)
        self._check_peak_hour(state)
        self._clear_passed_vehicles(state)
```

### 8.2 Vehicle Movement Rules

- Vehicles queue in their lane when signal is RED
- Vehicles move at `speed` px/tick when signal is GREEN
- Ambulance ignores RED signal after emergency override is active
- Blocked lane (accident): `blocked = True`, capacity drops to 0

### 8.3 Scenario Modes

| Scenario | What Changes |
|---|---|
| `normal.json` | Balanced spawn rates, no emergencies |
| `peak_hour.json` | 3x spawn rate for 60s burst, `is_peak_hour = True` |
| `emergency.json` | Ambulance spawns on random direction with emergency flag |
| `accident.json` | One lane marked `blocked=True` mid-simulation |

---

## 9. Frontend (PyGame UI)

### 9.1 Screen Layout (1280 × 720 px)

```
┌─────────────────────────────────────────────────────────────────┐
│  TITLE BAR: "Smart Adaptive Traffic Signal Controller v1.0"     │
├────────────────────────────┬────────────────────────────────────┤
│                            │  HUD PANEL (right)                 │
│                            │  ┌──────────────────────────────┐  │
│   SIMULATION VIEWPORT      │  │  🚦 Current Phase: NS_GREEN   │  │
│   (860 × 620 px)           │  │  ⏱  Phase Timer: 18.4s       │  │
│                            │  │  🧠 Algorithm: A*             │  │
│   [Top-down road view]     │  │  📊 Cost: 142.7               │  │
│                            │  ├──────────────────────────────┤  │
│   North lane (top)         │  │  LANE STATS                  │  │
│   South lane (bottom)      │  │  N: 8 vehicles | wait: 12s   │  │
│   East lane (right)        │  │  S: 5 vehicles | wait: 8s    │  │
│   West lane (left)         │  │  E: 3 vehicles | wait: 4s    │  │
│                            │  │  W: 11 vehicles | wait: 22s  │  │
│   [Traffic lights]         │  ├──────────────────────────────┤  │
│   [Animated vehicles]      │  │  ALGORITHM TRACE LOG         │  │
│   [Zebra crossings]        │  │  > Expanding state (8,3,...)  │  │
│   [Lane markings]          │  │  > h(n) = 142.7              │  │
│                            │  │  > Action: EXTEND_GREEN      │  │
│                            │  ├──────────────────────────────┤  │
│                            │  │  📈 WAIT TIME CHART (live)   │  │
│                            │  │  [matplotlib mini chart]     │  │
│                            │  └──────────────────────────────┘  │
├────────────────────────────┴────────────────────────────────────┤
│  BOTTOM BAR: [▶ Play] [⏸ Pause] [🔁 Reset] [📁 Scenario ▾]     │
│  [Speed: 1x ▾]  [Algorithm: A* ▾]  Total Cleared: 347 vehicles  │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Visual Design Language

**Color Palette:**

| Element | Color | Hex |
|---|---|---|
| Road surface | Dark asphalt | `#1A1A2E` |
| Lane markings | Dashed white | `#FFFFFF` |
| Green signal | Neon green | `#00FF88` |
| Red signal | Neon red | `#FF3B30` |
| Yellow signal | Amber | `#FFD60A` |
| HUD background | Dark translucent | `#0D1117` / 85% opacity |
| HUD accent | Cyan | `#00D4FF` |
| Emergency vehicle | Flashing red+blue | `#FF3B30` + `#007AFF` |
| Normal car | Various (random palette) | |
| Background | Night city gradient | `#0D1117` → `#161B22` |

**Visual Effects:**

- Traffic lights glow using Pygame `draw.circle` with gradient rings
- Emergency vehicles flash (alternating red/blue every 0.3s)
- Cars smoothly animate along lanes (lerp movement)
- Congestion shown with heat-map overlay on lanes (green→yellow→red based on count)
- Signal switch triggers a brief yellow phase animation (0.5s)
- Stats panel numbers update with smooth counter animation

### 9.3 Camera & View

- Fixed top-down orthographic view
- Intersection centered at (430, 310)
- 4 roads extend outward (each 200px long, 80px wide, 2 lanes each)
- Vehicles rendered as 20×12 px rectangles with direction-appropriate icons

---

## 10. Feature Specifications

### Feature 1: Core Signal Control

**ID:** F-001  
**Priority:** P0 (Must Have)

- System cycles between `NS_GREEN` and `EW_GREEN` phases
- Default green duration: configurable (default 30s)
- Yellow transition: 3s (visual only, no vehicle movement)
- Red all: 1s gap between phase switches
- Cycle counter increments on each full NS→EW→NS cycle

### Feature 2: Emergency Vehicle Override

**ID:** F-002  
**Priority:** P0 (Must Have)

- Ambulance/fire engine spawned with `is_emergency=True`
- AI Engine checks `emergency_NS` or `emergency_EW` flag FIRST (before any other algorithm)
- Immediate signal switch to give emergency vehicle GREEN
- Override lasts until vehicle clears junction
- Visual: siren animation, flashing lights, alert banner in HUD
- Trace log shows: `"EMERGENCY OVERRIDE: Ambulance on North lane"`

### Feature 3: Peak Hour Detection & Adaptation

**ID:** F-003  
**Priority:** P1 (Should Have)

- Peak hour triggered when: `total_vehicles > PEAK_THRESHOLD` (default: 20) for `PEAK_WINDOW` seconds (default: 15s)
- State flag `is_peak_hour = True`
- AI Engine switches from A* → Beam Search
- Beam width `k=3` explores top 3 signal plans simultaneously
- HUD shows "⚡ PEAK HOUR MODE" banner in amber
- Peak hour ends when vehicle count drops below threshold for 20s

### Feature 4: Accident Simulation

**ID:** F-004  
**Priority:** P1 (Should Have)

- Randomly triggered (configurable probability, default: 0.001/tick)
- Or manually triggered via UI button
- Affected lane: `blocked = True`, vehicle_count frozen, no clearance
- AI re-weights heuristic: blocked lane gets penalty to avoid routing there
- Visual: Flashing hazard icon on blocked lane, red X overlay
- Duration: 30–60s (random), then clears

### Feature 5: Starvation Prevention (Fairness Constraint)

**ID:** F-005  
**Priority:** P1 (Should Have)

- Track `cycles_since_green` per direction pair (NS and EW)
- If a pair hasn't had GREEN in `MAX_STARVATION_CYCLES` (default: 3), force switch
- Heuristic adds starvation penalty: `w4 * starvation_score`
- Ensures low-traffic lanes never wait indefinitely

### Feature 6: Scenario Loader

**ID:** F-006  
**Priority:** P2 (Nice to Have)

- Bottom bar dropdown lets user load JSON scenario files
- Scenarios control: spawn rates, emergency probability, accident timing, initial vehicle counts
- Live reload without restarting application

### Feature 7: Algorithm Trace Panel

**ID:** F-007  
**Priority:** P1 (Should Have)

- Right HUD panel shows scrolling log of AI decisions
- Shows: current state tuple, h(n) value, action chosen, algorithm name
- Color-coded: A* = cyan, Beam = amber, Emergency = red
- Last 10 decisions visible, older entries fade out

### Feature 8: Live Statistics Chart

**ID:** F-008  
**Priority:** P2 (Nice to Have)

- Embedded matplotlib chart rendered to pygame surface every 2s
- X-axis: simulation time (last 60s)
- Y-axis: average wait time (NS in blue, EW in orange)
- Shows improvement curve when AI is active vs hypothetical fixed timer

---

## 11. Algorithm Implementations

### 11.1 A* Search (`ai/astar.py`)

**Purpose:** Find the optimal sequence of signal actions to minimize heuristic cost.

```
State Space:
  - Node: (TrafficState, action_taken, g_cost)
  - g(n): cost so far (actual wait time accumulated)
  - h(n): heuristic estimate (see Section 12)
  - f(n) = g(n) + h(n)

Search:
  1. Start: current TrafficState
  2. Expand: generate next states for each possible action
  3. Select: node with minimum f(n) from priority queue (heapq)
  4. Depth limit: 3 steps ahead (real-time constraint)
  5. Return: first action of optimal path

Complexity: O(b^d) with b=4 actions, d=3 depth → max 64 nodes
```

**Why A\* here:** It guarantees the optimal signal action given an admissible heuristic. For a 3-step lookahead, it's fast enough for real-time use.

### 11.2 Hill Climbing (`ai/hill_climbing.py`)

**Purpose:** Fine-tune the phase timer duration (extend or shorten current green).

```
Start: current phase timer value T
Neighbors: T-5, T, T+5, T+10 seconds
Evaluate: h(n) for each neighbor
Move: to neighbor with lowest h(n)
Stop: no neighbor improves cost (local minimum)

Used for: once phase is decided (by A*), HC optimizes the duration
```

**Limitation (viva point):** Hill Climbing can get stuck in local optima. In our system we use random restarts (3 restarts) to mitigate this.

### 11.3 Beam Search (`ai/beam_search.py`)

**Purpose:** Explore top-k signal plans during peak hour for faster decision.

```
Beam width k = 3
Level 0: current state
Level 1: expand all actions → keep top-k by f(n)
Level 2: expand top-k → keep top-k again
Level 3: select best terminal node

Returns: first action of the best beam path
```

**Why Beam Search for peak hour:** Faster than A* when search space is large. Trades optimality for speed — acceptable for congested conditions where any good decision is better than delay.

### 11.4 BFS (`ai/bfs_dfs.py`)

**Purpose:** Educational — exhaustively explore all signal sequences to finite depth.

```python
def bfs_signal_sequence(initial_state, max_depth=3):
    queue = deque([(initial_state, [])])
    visited = set()
    best = None
    while queue:
        state, path = queue.popleft()
        if len(path) == max_depth:
            if best is None or heuristic(state) < heuristic(best[0]):
                best = (state, path)
            continue
        for action in ACTIONS:
            next_state = apply_action(state, action)
            key = next_state.as_tuple()
            if key not in visited:
                visited.add(key)
                queue.append((next_state, path + [action]))
    return best[1][0] if best else SignalAction.EXTEND_CURRENT_GREEN
```

**Note:** BFS used only in "educational mode" (toggled from UI). Not used for real-time decisions (too slow).

### 11.5 DFS (`ai/bfs_dfs.py`)

Similar to BFS but uses a stack. Explores deep paths first. Used alongside BFS for comparison demonstrations in the UI trace panel.

### 11.6 AO* (`ai/ao_star.py`)

**Purpose:** Model multi-objective traffic control as an AND-OR graph problem.

```
AND-OR Graph Model:
  OR node:  "Reduce total wait" → can be achieved by MULTIPLE strategies
  AND node: "Handle Emergency AND Reduce Queue" → BOTH must be achieved

Example:
  Goal: Optimal signal decision
  OR branches:
    Branch A: If emergency → Emergency Override (AND: clear ambulance AND restore normal)
    Branch B: If peak hour → Beam Search plan (AND: serve NS AND serve EW fairly)
    Branch C: Normal → A* optimal action

AO* finds minimum cost AND-OR subgraph (solution tree)
```

**Implementation Note:** Full AO* graph search is computationally heavy. This module implements a simplified AO* over 2-level AND-OR trees with cost propagation. For viva: explain the concept fully, show the AND-OR graph drawing, and run the module as a planner for accident scenarios.

### 11.7 Minimax + Alpha-Beta (`ai/minimax.py`)

**Purpose:** Model the intersection as an adversarial game between "Traffic Flow" (AI) and "Congestion" (environment/adversary).

```
Players:
  MAX player: Traffic Controller (AI) — wants to minimize wait times
  MIN player: Traffic Generator (environment) — maximizes congestion

Game Tree (depth=2):
  Level 0 (MAX): AI chooses signal action
  Level 1 (MIN): Environment spawns worst-case vehicle batch
  Level 2 (MAX): AI responds with next action

Alpha-Beta pruning: prune branches where α ≥ β
Speedup vs plain Minimax: ~40% fewer nodes evaluated

Limitation (viva point): Real traffic isn't truly adversarial. Minimax is an
approximation for worst-case planning. Useful for stress-testing the controller.
```

---

## 12. Heuristic Function Design

### 12.1 Core Heuristic (`ai/heuristic.py`)

```python
def heuristic(state: TrafficState, weights: dict) -> float:
    """
    h(n) = w1 * total_wait_time
         + w2 * queue_length
         + w3 * emergency_penalty
         + w4 * starvation_penalty
         - w5 * throughput_bonus

    All terms are non-negative. h(n) is admissible if:
      - emergency_penalty is bounded (capped at MAX_EMERGENCY_PENALTY)
      - starvation_penalty is bounded (capped at MAX_STARVATION_PENALTY)
    """
    w1, w2, w3, w4, w5 = (
        weights["wait_time"],
        weights["queue_length"],
        weights["emergency"],
        weights["starvation"],
        weights["throughput"]
    )

    total_wait = sum(lane.avg_wait_time for lane in state.lanes.values())
    queue_len  = sum(lane.vehicle_count for lane in state.lanes.values())

    # Emergency penalty: very high cost if emergency vehicle is waiting on RED
    emergency_penalty = 0
    if state.emergency_NS and state.current_phase == SignalPhase.EW_GREEN:
        emergency_penalty = weights["max_emergency_penalty"]
    elif state.emergency_EW and state.current_phase == SignalPhase.NS_GREEN:
        emergency_penalty = weights["max_emergency_penalty"]

    # Starvation penalty: grows with how long a direction has been red
    starvation_score = max(
        state.cycles_since_green_NS,
        state.cycles_since_green_EW
    )
    starvation_penalty = min(starvation_score * 10, weights["max_starvation_penalty"])

    # Throughput bonus: reward states that have cleared more vehicles
    total_throughput = sum(lane.throughput for lane in state.lanes.values())

    h = (w1 * total_wait +
         w2 * queue_len +
         w3 * emergency_penalty +
         w4 * starvation_penalty -
         w5 * total_throughput)

    return max(0, h)   # Ensure non-negative (admissibility requirement)
```

### 12.2 Default Weight Configuration

```json
{
    "wait_time":              1.5,
    "queue_length":           1.0,
    "emergency":              50.0,
    "starvation":             2.0,
    "throughput":             0.8,
    "max_emergency_penalty":  500.0,
    "max_starvation_penalty": 100.0
}
```

### 12.3 Admissibility Proof (Viva Answer)

> The heuristic never overestimates the true cost because:
> 1. `total_wait_time` and `queue_length` are lower-bounded by 0 and represent real, observed quantities — not inflated estimates.
> 2. `emergency_penalty` is capped at `MAX_EMERGENCY_PENALTY`, which is calibrated to be ≤ actual cost of keeping an ambulance blocked.
> 3. `starvation_penalty` is capped and represents a real constraint violation, not a speculative estimate.
> Therefore h(n) ≤ h*(n) for all states, satisfying admissibility.

---

## 13. API / Internal Interface Contracts

### 13.1 AI Engine Interface

```python
class AIEngine:
    def decide(self, state: TrafficState) -> SignalAction:
        """Returns the best action for the current state."""

    def get_trace(self) -> List[str]:
        """Returns human-readable log of last decision process."""

    def set_algorithm(self, algorithm: str):
        """Force a specific algorithm: 'astar', 'beam', 'bfs', 'hillclimb'"""
```

### 13.2 Simulation Engine Interface

```python
class SimulationEngine:
    def update(self, state: TrafficState, dt: float) -> None:
        """Advance simulation by dt seconds."""

    def trigger_emergency(self, direction: Direction) -> None:
        """Manually spawn emergency vehicle."""

    def trigger_accident(self, direction: Direction) -> None:
        """Manually block a lane."""

    def reset(self) -> TrafficState:
        """Reset all vehicles and state to initial."""

    def load_scenario(self, scenario_path: str) -> None:
        """Load JSON scenario configuration."""
```

### 13.3 Renderer Interface

```python
class Renderer:
    def draw(self, state: TrafficState, vehicles: List[Vehicle],
             ai_trace: List[str], stats: dict) -> None:
        """Draw one complete frame."""

    def handle_ui_event(self, event: pygame.Event) -> Optional[UICommand]:
        """Returns UI command if user interaction detected."""
```

---

## 14. UI Screens & Components

### 14.1 Main Simulation Screen (Primary)

Described in Section 9.1. This is the only screen during normal operation.

### 14.2 Splash Screen (on launch, 2s)

- Dark background with animated traffic signal graphic
- Title: "Smart Adaptive Traffic Signal Controller"
- Subtitle: "AI Lab Project | Powered by A*, Beam Search & Hill Climbing"
- Fade to main screen

### 14.3 Pause Overlay

- Dimmed simulation viewport
- "PAUSED" text centered
- Shows current state tuple in readable format
- Resume with `[Space]` or Play button

### 14.4 Scenario Select Modal

- Triggered by "📁 Scenario" dropdown
- Lists available JSON scenarios
- Shows description, difficulty, and expected algorithm behavior
- Click to load and auto-restart simulation

### 14.5 Keyboard Shortcuts

| Key | Action |
|---|---|
| `Space` | Pause / Resume |
| `R` | Reset simulation |
| `E` | Spawn emergency vehicle (random direction) |
| `A` | Trigger accident (random lane) |
| `1` | Load normal scenario |
| `2` | Load peak hour scenario |
| `3` | Load emergency scenario |
| `4` | Load accident scenario |
| `+` / `-` | Increase / decrease simulation speed |
| `F` | Toggle fullscreen |
| `D` | Toggle debug mode (show state tuple on screen) |

---

## 15. Configuration & Parameters (`config/settings.json`)

```json
{
    "simulation": {
        "fps":                        60,
        "time_scale":                 1.0,
        "spawn_rate_normal":          0.8,
        "spawn_rate_peak":            2.5,
        "emergency_probability":      0.003,
        "accident_probability":       0.001,
        "peak_hour_threshold":        20,
        "peak_hour_window_seconds":   15
    },

    "signals": {
        "default_green_duration":     30.0,
        "yellow_duration":            3.0,
        "min_green_duration":         10.0,
        "max_green_duration":         60.0,
        "max_starvation_cycles":      3
    },

    "ai": {
        "decision_interval_ticks":    30,
        "default_algorithm":          "astar",
        "astar_depth_limit":          3,
        "beam_width":                 3,
        "hill_climb_restarts":        3
    },

    "heuristic_weights": {
        "wait_time":                  1.5,
        "queue_length":               1.0,
        "emergency":                  50.0,
        "starvation":                 2.0,
        "throughput":                 0.8,
        "max_emergency_penalty":      500.0,
        "max_starvation_penalty":     100.0
    },

    "renderer": {
        "window_width":               1280,
        "window_height":              720,
        "road_color":                 "#1A1A2E",
        "lane_marking_color":         "#FFFFFF",
        "hud_bg_color":               "#0D1117",
        "hud_accent_color":           "#00D4FF"
    }
}
```

---

## 16. Build & Run Instructions

### 16.1 Prerequisites

```bash
Python 3.10+
pip install -r requirements.txt
```

### 16.2 Run Simulation

```bash
# Default (normal scenario, A* algorithm)
python main.py

# With specific scenario
python main.py --scenario config/scenarios/peak_hour.json

# With specific algorithm
python main.py --algorithm beam_search

# Debug mode
python main.py --debug
```

### 16.3 Run Tests

```bash
pytest tests/ -v
```

### 16.4 `main.py` Entry Point Structure

```python
import pygame
import sys
from core.state import TrafficState
from core.simulation import SimulationEngine
from core.signal_controller import SignalController
from ai.ai_engine import AIEngine
from renderer.renderer import Renderer
from config.loader import load_config

def main():
    config = load_config("config/settings.json")
    pygame.init()

    state      = TrafficState()
    simulation = SimulationEngine(config["simulation"])
    controller = SignalController(config["signals"])
    ai_engine  = AIEngine(config["ai"], config["heuristic_weights"])
    renderer   = Renderer(config["renderer"])

    clock = pygame.time.Clock()
    tick  = 0

    while True:
        dt = clock.tick(config["simulation"]["fps"]) / 1000.0

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            cmd = renderer.handle_ui_event(event)
            if cmd: handle_ui_command(cmd, simulation, ai_engine, state)

        # Update simulation
        simulation.update(state, dt * config["simulation"]["time_scale"])
        controller.update(state, dt)

        # AI decision every N ticks
        if tick % config["ai"]["decision_interval_ticks"] == 0:
            action = ai_engine.decide(state)
            controller.apply_action(action, state)

        # Render frame
        renderer.draw(state, simulation.vehicles, ai_engine.get_trace(), {})

        tick += 1

if __name__ == "__main__":
    main()
```

---

## 17. Viva Preparation Notes

### 17.1 Expected Viva Questions & Model Answers

**Q: What is the state representation in your system?**
> State = `(vehicles_NS, vehicles_EW, avg_wait_NS, avg_wait_EW, emergency_NS, emergency_EW, current_signal)`. This is a 7-tuple that fully describes the intersection at any point in time. It's hashable, so we can use it in closed-lists for BFS/A*.

**Q: Why is your heuristic admissible?**
> Because every component of h(n) either reflects actual, observed costs (like avg_wait_time) or is bounded by a calibrated cap that ensures it never exceeds the true remaining cost. We guarantee h(n) ≤ h*(n).

**Q: Why A* and not just greedy best-first?**
> Greedy only looks at h(n) and can miss globally optimal decisions. A* uses f(n) = g(n) + h(n), balancing actual cost and future estimate, guaranteeing optimality when the heuristic is admissible.

**Q: When does Hill Climbing fail here?**
> It can get stuck in local optima — e.g., extending the current green slightly reduces wait on one axis but a full phase switch would be globally better. We mitigate this with 3 random restarts.

**Q: How does Beam Search differ from A*?**
> Beam Search keeps only the top-k nodes at each depth level rather than all frontier nodes. It's faster and uses less memory but sacrifices optimality. We use it during peak hour where speed of decision matters more than guaranteed optimality.

**Q: Explain AO* in your context.**
> AO* works on AND-OR graphs. In our system, the goal "handle junction optimally" is an OR goal: it can be achieved by different strategies. But in accident scenarios, the goal becomes an AND goal: we must BOTH re-route traffic AND handle any emergency — both sub-goals must be satisfied. AO* finds the minimum cost solution tree over this AND-OR structure.

**Q: What is the role of Minimax?**
> Minimax models the intersection as a 2-player game: the controller (MAX, minimizing wait times) vs. the environment (MIN, maximizing congestion by worst-case vehicle spawns). It helps stress-test our controller by assuming the worst-case scenario at every step. Alpha-Beta pruning speeds this up by skipping branches that can't affect the final decision.

### 17.2 Algorithm-to-Problem Mapping Table (for viva display)

| Algorithm | Mapped Problem | Key Property Used |
|---|---|---|
| BFS | Explore all signal sequences at shallow depth | Completeness — finds solution if exists |
| DFS | Explore deep signal plan branches | Memory efficiency |
| A* | Optimal signal switching decision | Admissible heuristic → guaranteed optimality |
| Hill Climbing | Fine-tune phase duration | Local gradient descent on heuristic |
| Beam Search | Peak hour planning (top-k plans) | Speed vs optimality tradeoff |
| AO* | Multi-goal re-planning (accident scenario) | AND-OR decomposition |
| Minimax + Alpha-Beta | Adversarial worst-case planning | Game tree search, α-β pruning |

---

## 18. Milestones & Delivery Plan

| Milestone | Deliverables | Estimated Effort |
|---|---|---|
| **M1: Core Foundation** | `state.py`, `simulation.py`, basic pygame window with static road | 1 day |
| **M2: Signal Logic** | `signal_controller.py`, phase cycling, yellow transition, HUD panel | 1 day |
| **M3: AI Engine v1** | `heuristic.py`, `astar.py`, AI dispatcher, algorithm trace log | 1.5 days |
| **M4: Full UI** | Animated vehicles, traffic lights, lane heat maps, bottom bar | 1.5 days |
| **M5: Advanced Features** | Emergency override, peak hour, accident sim, Beam Search, Hill Climbing | 1.5 days |
| **M6: All Algorithms** | `bfs_dfs.py`, `ao_star.py`, `minimax.py` + viva explanation modules | 1 day |
| **M7: Scenarios & Polish** | JSON scenarios, stats chart, starvation prevention, scenario loader UI | 0.5 days |
| **M8: Testing & Docs** | `pytest` tests, README, viva Q&A module | 0.5 days |
| **Total** | | **~9 days** |

### 18.1 Suggested Build Order for Antigravity IDE

```
1. Create folder structure exactly as in Section 5
2. Implement core/state.py → run quick unit test
3. Implement core/simulation.py → verify vehicle spawning logic
4. Set up main.py pygame loop with placeholder draw
5. Implement renderer/road.py → see intersection on screen
6. Implement renderer/vehicles.py + renderer/signals.py
7. Implement ai/heuristic.py + ai/astar.py
8. Wire AIEngine into main loop
9. Implement renderer/hud.py with live stats
10. Implement emergency, peak_hour, accident features
11. Add remaining algorithms (Hill Climbing, Beam Search, BFS/DFS)
12. Add AO* and Minimax explanation modules
13. Add scenario loader + bottom bar UI
14. Add matplotlib stats chart
15. Final polish: colors, animations, glow effects
16. Write tests + README
```

---

*Document prepared for use with Antigravity IDE. All code snippets are implementation guides — the IDE should generate complete implementations based on the specifications above. Ensure all Python files include docstrings and inline comments explaining AI concepts for viva readiness.*

---
**End of PRD — Smart Adaptive Traffic Signal Controller v1.0**