"""
renderer/hud.py
===============
Draws the right-side HUD panel. Refactored for a clean, professional "light" UI layout.
"""

import pygame
from typing import List, Dict, Optional
from core.state import TrafficState, SignalPhase, Direction

HUD_BG       = (255, 255, 255)
HUD_BG2      = (248, 250, 252)
PANEL_BORDER = (226, 232, 240)
TEXT_MAIN    = (45, 55, 72)
TEXT_DIM     = (113, 128, 150)
BAR_BG       = (255, 255, 255)

# Accent standard colors
C_BLUE   = (49,  130, 206)
C_GREEN  = (56,  161, 105)
C_AMBER  = (221, 107, 32)
C_RED    = (229, 62,  62)
C_PURPLE = (128, 90,  213)

HUD_X     = 866
HUD_W     = 414
WIN_H     = 720
BOTTOM_H  = 60
SIM_H     = WIN_H - BOTTOM_H

_fonts: Dict[str, pygame.font.Font] = {}

def _font(size: int, bold: bool = False) -> pygame.font.Font:
    key = f"{size}{'b' if bold else ''}"
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("segoeui, arial, helvetica", size, bold=bold)
    return _fonts[key]


def draw_hud(surface: pygame.Surface, state: TrafficState, ai_trace: List[str], stats: dict) -> None:
    """Render the dashboard UI."""
    pygame.draw.rect(surface, HUD_BG, (HUD_X, 0, HUD_W, SIM_H))
    pygame.draw.line(surface, PANEL_BORDER, (HUD_X, 0), (HUD_X, SIM_H), 1)

    y = 15
    y = _draw_title_row(surface, y)
    y = _draw_signal_block(surface, state, y)
    y = _draw_lane_stats(surface, state, y)
    y = _draw_banners(surface, state, y)

def draw_bottom_bar(surface: pygame.Surface, state: TrafficState, buttons: dict, speed: float, algo: str) -> None:
    """Minimal, light bottom control bar."""
    pygame.draw.rect(surface, BAR_BG, (0, SIM_H, 1280, BOTTOM_H))
    pygame.draw.line(surface, PANEL_BORDER, (0, SIM_H), (1280, SIM_H), 1)

    _blit(surface, f"Speed: {speed:.1f}x", 14, TEXT_MAIN, 20, SIM_H + 12, bold=True)
    _blit(surface, f"Cleared: {state.total_cleared}", 14, C_GREEN, 20, SIM_H + 32, bold=True)

    _blit(surface, f"Elapsed: {state.total_elapsed:.0f}s", 13, TEXT_DIM, 180, SIM_H + 20)
    _blit(surface, f"AI Mode: {algo}", 13, C_BLUE, 720, SIM_H + 20, bold=True)
    
    _blit(surface, "Shortcuts: [Space] Pause | [R] Reset | [E] Emerg | [A] Accident | [1-4] Scenario | [+/-] Speed", 
          12, TEXT_DIM, 866, SIM_H + 20)


def _draw_title_row(surface: pygame.Surface, y: int) -> int:
    _blit(surface, "SYSTEM OVERVIEW", 18, TEXT_MAIN, HUD_X + 20, y, bold=True)
    return y + 35

def _draw_signal_block(surface: pygame.Surface, state: TrafficState, y: int) -> int:
    _section_bg(surface, y, 95)
    
    _blit(surface, "Current Phase", 12, TEXT_DIM, HUD_X + 20, y + 10, bold=True)
    phase_str = state.current_phase.value.replace("_", " ")
    
    if state.current_phase == SignalPhase.NS_GREEN: phase_col = C_GREEN
    elif state.current_phase == SignalPhase.EW_GREEN: phase_col = C_BLUE
    elif state.current_phase == SignalPhase.YELLOW: phase_col = C_AMBER
    else: phase_col = C_RED

    _blit(surface, phase_str, 18, phase_col, HUD_X + 20, y + 25, bold=True)

    # Timer progression
    frac = max(0, min(state.phase_timer / 60.0, 1.0))
    _progress_bar(surface, HUD_X + 20, y + 55, 370, 8, frac, phase_col)
    
    _blit(surface, f"{state.phase_timer:.1f}s remaining", 12, TEXT_MAIN, HUD_X + 20, y + 70)
    _blit(surface, f"AI: {state.algorithm_used}", 12, C_PURPLE, HUD_X + 180, y + 70, bold=True)
    _blit(surface, f"Heuristic Cost: {state.last_decision_cost:.1f}", 12, TEXT_DIM, HUD_X + 280, y + 70)
    return y + 110


def _draw_lane_stats(surface: pygame.Surface, state: TrafficState, y: int) -> int:
    _section_bg(surface, y, 125)
    _blit(surface, "LANE QUEUES & WAIT TIMES", 12, TEXT_DIM, HUD_X + 20, y + 10, bold=True)

    rows = [(Direction.NORTH, "North"), (Direction.SOUTH, "South"), (Direction.EAST, "East"), (Direction.WEST, "West")]
    for i, (d, label) in enumerate(rows):
        ry = y + 35 + i * 20
        cnt = state.lanes[d].vehicle_count
        wt  = state.lanes[d].avg_wait_time
        
        col = C_RED if wt > 20 else (C_AMBER if wt > 10 else TEXT_MAIN)
        txt_tag = ""
        if state.lanes[d].emergency_flag: txt_tag = "[Emergency]"
        if state.lanes[d].blocked: txt_tag = "[Blocked]"

        _blit(surface, f"{label}:", 13, TEXT_DIM, HUD_X + 20, ry)
        _blit(surface, f"{cnt:>2} veh", 13, TEXT_MAIN, HUD_X + 70, ry, bold=True)
        _blit(surface, f"avg wait: {wt:>4.1f}s", 13, col, HUD_X + 140, ry)
        
        if txt_tag: _blit(surface, txt_tag, 12, C_RED, HUD_X + 240, ry, bold=True)
        
        bar_frac = min(cnt / 15.0, 1.0)
        _progress_bar(surface, HUD_X + 310, ry + 4, 80, 6, bar_frac, col)

    return y + 140

def _draw_banners(surface: pygame.Surface, state: TrafficState, y: int) -> int:
    banner_h = 0
    if state.emergency_NS or state.emergency_EW:
        _banner(surface, y, "EMERGENCY OVERRIDE ENFORCED", C_RED)
        banner_h += 35
    if state.is_peak_hour:
        _banner(surface, y + banner_h, "PEAK HOUR DETECTED — BEAM SEARCH ACTIVE", C_AMBER)
        banner_h += 35
    if any(l.blocked for l in state.lanes.values()):
        _banner(surface, y + banner_h, "ACCIDENT AHEAD — AO* REROUTING", C_PURPLE)
        banner_h += 35
    return y + max(banner_h, 0)



# Utilities
def _blit(surface, text, size, color, x, y, bold=False):
    surf = _font(size, bold).render(text, True, color)
    surface.blit(surf, (x, y))

def _section_bg(surface, y, h):
    pygame.draw.rect(surface, HUD_BG2, (HUD_X + 10, y, HUD_W - 20, h), border_radius=8)
    pygame.draw.rect(surface, PANEL_BORDER, (HUD_X + 10, y, HUD_W - 20, h), 1, border_radius=8)

def _progress_bar(surface, x, y, w, h, frac, color):
    pygame.draw.rect(surface, (237, 242, 246), (x, y, w, h), border_radius=4)
    filled = int(w * frac)
    if filled > 0:
        pygame.draw.rect(surface, color, (x, y, filled, h), border_radius=4)

def _banner(surface, y, text, col):
    bg_col = (col[0], col[1], col[2], 30) # Very light transparent tint
    rect = pygame.Rect(HUD_X + 10, y, HUD_W - 20, 30)
    bg_surface = pygame.Surface((HUD_W - 20, 30), pygame.SRCALPHA)
    pygame.draw.rect(bg_surface, bg_col, (0,0,HUD_W-20,30), border_radius=6)
    surface.blit(bg_surface, (HUD_X + 10, y))
    pygame.draw.rect(surface, col, rect, 1, border_radius=6)
    _blit(surface, text, 12, col, HUD_X + 20, y + 8, bold=True)
