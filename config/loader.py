"""
config/loader.py
================
Loads and merges JSON configuration files.
Handles settings.json and per-scenario override files.
"""

import json
import os
from typing import Any, Dict


def load_config(path: str = "config/settings.json") -> Dict[str, Any]:
    """Load the master settings JSON and return as a dict."""
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Config not found: {abs_path}")
    with open(abs_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_scenario(name: str,
                  base_dir: str = "config/scenarios") -> Dict[str, Any]:
    """
    Load a named scenario JSON file.
    `name` can be 'normal', 'peak_hour', 'emergency', or 'accident'.
    Returns the scenario dict or an empty dict if not found.
    """
    path = os.path.abspath(os.path.join(base_dir, f"{name}.json"))
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_scenario(base_config: Dict[str, Any],
                   scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep-merge a scenario override dict onto the base config.
    Scenario keys override matching keys in base_config['simulation'].
    Returns the updated base_config dict (mutated in-place).
    """
    sim_overrides = scenario.get("simulation", {})
    for k, v in sim_overrides.items():
        base_config["simulation"][k] = v
    return base_config
