"""
renderer/signals.py
===================
Draws realistic, clear traffic lights.
"""

import pygame
import math
from core.state import TrafficState, SignalPhase, Direction

_SIGNAL_POSITIONS = {
    Direction.NORTH: (408, 255),
    Direction.SOUTH: (450, 365),
    Direction.EAST:  (490, 265),
    Direction.WEST:  (368, 355),
}

POLE_COLOR  = (100, 105, 110)
BOX_COLOR   = (30,  35,  40)
BOX_W, BOX_H = 16, 44
LIGHT_R      = 6

RED_ON    = (255, 60,  60)
RED_OFF   = (70,  20,  20)
YEL_ON    = (255, 200, 20)
YEL_OFF   = (70,  50,  10)
GRN_ON    = (40,  220, 80)
GRN_OFF   = (20,  60,  30)


def draw_signals(surface: pygame.Surface, state: TrafficState, elapsed: float) -> None:
    is_emergency = (state.emergency_NS or state.emergency_EW)

    for direction, (sx, sy) in _SIGNAL_POSITIONS.items():
        ns_dir = direction in (Direction.NORTH, Direction.SOUTH)
        ew_dir = not ns_dir

        phase = state.current_phase
        if phase == SignalPhase.YELLOW:
            r_on, y_on, g_on = False, True, False
        elif phase == SignalPhase.NS_GREEN:
            r_on, y_on, g_on = ew_dir, False, ns_dir
        elif phase == SignalPhase.EW_GREEN:
            r_on, y_on, g_on = ns_dir, False, ew_dir
        elif phase == SignalPhase.EMERGENCY_OVERRIDE:
            if direction in (Direction.NORTH, Direction.SOUTH):
                g_on, r_on = state.emergency_NS, not state.emergency_NS
            else:
                g_on, r_on = state.emergency_EW, not state.emergency_EW
            y_on = False
        else:
            r_on, y_on, g_on = True, False, False

        emergency_active_for_this_pole = is_emergency and (
            (ns_dir and state.emergency_NS) or (ew_dir and state.emergency_EW)
        )

        _draw_signal_head(surface, sx, sy, r_on, y_on, g_on, elapsed, emergency_active_for_this_pole)


def _draw_signal_head(surface: pygame.Surface, x: int, y: int,
                      red: bool, yellow: bool, green: bool,
                      elapsed: float, emergency: bool) -> None:
    
    # Draw pole
    pygame.draw.line(surface, POLE_COLOR, (x, y + BOX_H), (x, y + BOX_H + 20), 4)

    # Housing box (yellow outline, black inside)
    box_rect = pygame.Rect(x - BOX_W // 2, y, BOX_W, BOX_H)
    pygame.draw.rect(surface, BOX_COLOR, box_rect, border_radius=4)
    pygame.draw.rect(surface, (230, 180, 20), box_rect, 1, border_radius=4)

    # Lights (clean solid colors instead of blurry glow)
    _draw_light(surface, x, y + 8,  RED_ON if red    else RED_OFF, red)
    _draw_light(surface, x, y + 22, YEL_ON if yellow else YEL_OFF, yellow)
    _draw_light(surface, x, y + 36, GRN_ON if green  else GRN_OFF, green)

    # Emergency icon indicator
    if emergency:
        pulse = (math.sin(elapsed * 10) + 1) / 2
        alpha = int(200 * pulse)
        em_surf = pygame.Surface((30, 10), pygame.SRCALPHA)
        pygame.draw.rect(em_surf, (255, 59, 48, alpha), (0, 0, 30, 4), border_radius=2)
        pygame.draw.rect(em_surf, (49, 130, 206, alpha), (0, 6, 30, 4), border_radius=2)
        surface.blit(em_surf, (x - 15, y - 12))


def _draw_light(surface: pygame.Surface, x: int, y: int, colour: tuple, is_on: bool) -> None:
    # A crisp light bulb
    pygame.draw.circle(surface, colour, (x, y), LIGHT_R)
    # Bright inner highlight to make it pop safely
    if is_on:
        pygame.draw.circle(surface, (255, 255, 255), (x-2, y-2), 2)
