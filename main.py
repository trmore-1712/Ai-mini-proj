"""
main.py
=======
Entry point for the Smart Adaptive Traffic Signal Controller.

Usage:
    python main.py                              # default normal scenario, A*
    python main.py --scenario peak_hour         # load peak_hour.json
    python main.py --algorithm beam_search      # force Beam Search
    python main.py --debug                      # enable debug overlay

Keyboard shortcuts (in-game):
    Space       Pause / Resume
    R           Reset simulation
    E           Spawn emergency vehicle (random direction)
    A           Trigger accident (random lane)
    1-4         Load scenario (normal / peak_hour / emergency / accident)
    + / -       Increase / decrease simulation speed
    F           Toggle fullscreen
    D           Toggle debug mode
    F1-F7       Force algorithm: A* / Beam / BFS / DFS / HillClimb / Minimax / Auto
    Esc         Quit
"""

import pygame
import sys
import argparse
import random
import os

# ── Ensure working directory is the script location ─────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from config.loader       import load_config, load_scenario, merge_scenario
from core.state          import TrafficState, Direction
from core.simulation     import SimulationEngine
from core.signal_controller import SignalController
from ai.ai_engine        import AIEngine
from renderer.renderer   import Renderer, UICommand


# ──────────────────────────────────────────────────────────────────────────
# CLI argument parsing
# ──────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Smart Adaptive Traffic Signal Controller"
    )
    p.add_argument("--scenario",  default="normal",
                   choices=["normal", "peak_hour", "emergency", "accident"],
                   help="Scenario to load on startup")
    p.add_argument("--algorithm", default="auto",
                   choices=["auto", "astar", "beam", "bfs", "dfs",
                            "hillclimb", "minimax"],
                   help="Force a specific AI algorithm")
    p.add_argument("--debug",     action="store_true",
                   help="Enable debug state overlay")
    return p.parse_args()


# ──────────────────────────────────────────────────────────────────────────
# UICommand handler
# ──────────────────────────────────────────────────────────────────────────

def handle_ui_command(cmd: UICommand,
                      simulation:  SimulationEngine,
                      controller:  SignalController,
                      ai_engine:   AIEngine,
                      renderer:    Renderer,
                      state:       TrafficState,
                      config:      dict) -> tuple:
    """
    Process a UICommand returned by the renderer.
    Returns (state, config, speed, running) tuple after applying the command.
    """
    speed   = config["simulation"].get("time_scale", 1.0)
    running = True

    if cmd.action == "quit":
        running = False

    elif cmd.action == "pause":
        state.paused = not state.paused

    elif cmd.action == "reset":
        state = TrafficState()
        simulation.reset(state)

    elif cmd.action == "emergency":
        direction = random.choice(list(Direction))
        simulation.trigger_emergency(direction, state)

    elif cmd.action == "accident":
        direction = random.choice(list(Direction))
        simulation.trigger_accident(direction, state)

    elif cmd.action == "scenario":
        scenario_name = cmd.data or "normal"
        scenario      = load_scenario(scenario_name)
        config        = merge_scenario(load_config(), scenario)
        simulation.load_scenario(scenario)
        state         = TrafficState()
        simulation.reset(state)

    elif cmd.action == "speed_up":
        speed = min(speed * 2, 8.0)
        config["simulation"]["time_scale"] = speed
        renderer.set_speed(speed)

    elif cmd.action == "speed_down":
        speed = max(speed / 2, 0.25)
        config["simulation"]["time_scale"] = speed
        renderer.set_speed(speed)

    elif cmd.action == "fullscreen":
        pygame.display.toggle_fullscreen()

    elif cmd.action == "toggle_debug":
        renderer.toggle_debug()

    elif cmd.action == "set_algo":
        algo = cmd.data or "auto"
        ai_engine.set_algorithm(algo)
        renderer.set_algo(algo)

    return state, config, speed, running


# ──────────────────────────────────────────────────────────────────────────
# Main game loop
# ──────────────────────────────────────────────────────────────────────────

def main():
    args   = parse_args()

    # ── Load config + scenario ──────────────────────────────────────────
    config   = load_config("config/settings.json")
    scenario = load_scenario(args.scenario)
    if scenario:
        config = merge_scenario(config, scenario)

    # ── Pygame init ─────────────────────────────────────────────────────
    pygame.init()
    pygame.display.set_caption("Smart Adaptive Traffic Signal Controller v1.0")

    # ── Create subsystems ───────────────────────────────────────────────
    state      = TrafficState()
    simulation = SimulationEngine(config["simulation"])
    controller = SignalController(config["signals"])
    ai_engine  = AIEngine(config["ai"], config["heuristic_weights"])
    renderer   = Renderer(config["renderer"])

    # Apply CLI overrides
    if args.algorithm != "auto":
        ai_engine.set_algorithm(args.algorithm)
        renderer.set_algo(args.algorithm)
    if args.debug:
        renderer.toggle_debug()

    # Force initial algorithm display
    renderer.set_speed(config["simulation"].get("time_scale", 1.0))

    clock      = pygame.time.Clock()
    tick       = 0
    running    = True
    ai_interval = config["ai"]["decision_interval_ticks"]

    # ── Game loop ────────────────────────────────────────────────────────
    while running:
        raw_dt = clock.tick(config["simulation"]["fps"]) / 1000.0
        dt     = raw_dt * config["simulation"].get("time_scale", 1.0)

        # ── Event handling ───────────────────────────────────────────────
        for event in pygame.event.get():
            cmd = renderer.handle_ui_event(event)
            if cmd:
                state, config, _, running = handle_ui_command(
                    cmd, simulation, controller, ai_engine,
                    renderer, state, config
                )
                if not running:
                    break

        if not running:
            break

        # ── Simulation tick ──────────────────────────────────────────────
        simulation.update(state, dt)
        controller.update(state, dt)

        # ── AI decision every N ticks ────────────────────────────────────
        if tick % ai_interval == 0:
            action = ai_engine.decide(state)
            controller.apply_action(action, state)

        # ── Render frame ─────────────────────────────────────────────────
        renderer.draw(
            state,
            simulation.vehicles,
            ai_engine.get_trace(),
            {},
            raw_dt
        )

        tick += 1

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
