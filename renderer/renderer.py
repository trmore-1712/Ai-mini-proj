"""
renderer/renderer.py
====================
Master pygame rendering coordinator and UI event handler.
Light, friendly theme version.
"""

import pygame
import sys
import math
from typing import Optional, List, Any
from dataclasses import dataclass
from core.state import TrafficState, SignalPhase, Direction
from core.simulation import Vehicle

from renderer.road     import draw_road
from renderer.vehicles import draw_vehicles
from renderer.signals  import draw_signals
from renderer.hud      import draw_hud, draw_bottom_bar, HUD_X, SIM_H, _font

WIN_W, WIN_H = 1280, 720
VIEWPORT_W   = HUD_X

# Friendly map base color (grass)
BG_MAP_COLOR = (186, 223, 166)

CHART_UPDATE_INTERVAL = 2.0


@dataclass
class UICommand:
    action: str
    data:   Any = None


class Renderer:
    def __init__(self, config: dict):
        self.config   = config
        self.screen   = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Smart Traffic Simulation")

        self._debug_mode:    bool  = False
        self._show_scenario: bool  = False
        self._speed:         float = 1.0
        self._algo:          str   = "auto"
        self._elapsed:       float = 0.0

        self._splash_done  = False
        self._splash_timer = 0.0
        self._splash_alpha = 255

    def draw(self, state: TrafficState, vehicles: List[Vehicle],
             ai_trace: List[str], stats: dict, dt: float = 0.016) -> None:
        self._elapsed += dt

        if not self._splash_done:
            self._draw_splash(dt)
            pygame.display.flip()
            return

        # Friendly background fill
        self.screen.fill(BG_MAP_COLOR)

        vp_surf = self.screen.subsurface((0, 0, VIEWPORT_W, SIM_H))

        # Scene drawing
        draw_road(vp_surf, state)
        draw_vehicles(vp_surf, vehicles, state)
        draw_signals(vp_surf, state, self._elapsed)
        self._draw_direction_labels(vp_surf)

        if state.paused:
            self._draw_pause_overlay(vp_surf, state)

        if self._debug_mode:
            self._draw_debug(vp_surf, state)

        # UI
        draw_hud(self.screen, state, ai_trace, stats)
        draw_bottom_bar(self.screen, state, {}, self._speed, self._algo)
        self._draw_buttons(state)

        pygame.display.flip()

    def handle_ui_event(self, event: pygame.event.Event) -> Optional[UICommand]:
        if event.type == pygame.QUIT:
            return UICommand("quit")
        if event.type == pygame.KEYDOWN:
            return self._handle_key(event.key)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos)
        return None

    def _draw_splash(self, dt: float) -> None:
        self._splash_timer += dt
        self.screen.fill((255, 255, 255))

        cx, cy = WIN_W // 2, WIN_H // 2 - 60
        t      = self._splash_timer
        pygame.draw.rect(self.screen, (70, 75, 80), (cx - 20, cy - 50, 40, 100), border_radius=8)
        
        phase_t = t % 1.5
        if phase_t < 0.5:
            pygame.draw.circle(self.screen, (230, 60, 60),  (cx, cy - 30), 14)
            pygame.draw.circle(self.screen, (50, 50, 50),   (cx, cy),      14)
            pygame.draw.circle(self.screen, (50, 50, 50),   (cx, cy + 30), 14)
        elif phase_t < 1.0:
            pygame.draw.circle(self.screen, (50, 50, 50),   (cx, cy - 30), 14)
            pygame.draw.circle(self.screen, (240, 180, 20), (cx, cy),      14)
            pygame.draw.circle(self.screen, (50, 50, 50),   (cx, cy + 30), 14)
        else:
            pygame.draw.circle(self.screen, (50, 50, 50),   (cx, cy - 30), 14)
            pygame.draw.circle(self.screen, (50, 50, 50),   (cx, cy),      14)
            pygame.draw.circle(self.screen, (40, 200, 80),  (cx, cy + 30), 14)

        t1 = _font(36, bold=True).render("Smart Traffic Controller", True, (45, 55, 72))
        t2 = _font(16).render("Simulation Environment Starting...", True, (113, 128, 150))
        self.screen.blit(t1, (WIN_W // 2 - t1.get_width() // 2, cy + 80))
        self.screen.blit(t2, (WIN_W // 2 - t2.get_width() // 2, cy + 130))

        if self._splash_timer >= 2.0:
            self._splash_done = True

    def _draw_pause_overlay(self, surface: pygame.Surface, state: TrafficState) -> None:
        overlay = pygame.Surface((VIEWPORT_W, SIM_H), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 140))
        surface.blit(overlay, (0, 0))

        txt = _font(40, bold=True).render("PAUSED", True, (45, 55, 72))
        surface.blit(txt, (VIEWPORT_W // 2 - txt.get_width() // 2, SIM_H // 2 - 40))
        state_txt = _font(14).render(f"State: {state.as_tuple()}", True, (113, 128, 150))
        surface.blit(state_txt, (VIEWPORT_W // 2 - state_txt.get_width() // 2, SIM_H // 2 + 20))

    def _draw_debug(self, surface: pygame.Surface, state: TrafficState) -> None:
        lines = [
            f"State: {state.as_tuple()}",
            f"Phase timer: {state.phase_timer:.2f}s",
            f"Peak: {state.is_peak_hour}",
            f"Total veh: {state.total_vehicles}",
            f"Starv NS/EW: {state.cycles_since_green_NS}/{state.cycles_since_green_EW}",
        ]
        for i, line in enumerate(lines):
            surf = _font(12, bold=True).render(line, True, (45, 55, 72))
            surface.blit(surf, (15, 15 + i * 18))

    def _draw_direction_labels(self, surface: pygame.Surface) -> None:
        from renderer.road import CX, CY, ROAD_LEN
        col = (45, 55, 72)
        f = _font(16, bold=True)
        # Using subtle backgrounds for the labels to stand out
        labels = [
            ("N", CX - 8,           CY - ROAD_LEN - 30),
            ("S", CX - 6,           CY + ROAD_LEN +  10),
            ("E", CX + ROAD_LEN + 15, CY - 10),
            ("W", CX - ROAD_LEN -30,CY - 10),
        ]
        for text, x, y in labels:
            surf = f.render(text, True, col)
            surface.blit(surf, (x, y))

    def _draw_buttons(self, state: TrafficState) -> None:
        buttons = [
            ("PLAY/PAUSE",  340, "pause",     (72, 187, 120) if state.paused else (229, 62, 62)),
            ("RESET",       450, "reset",     (66, 153, 225)),
            ("EMERGENCY",   515, "emergency", (237, 137, 54)),
            ("ACCIDENT",    605, "accident",  (159, 122, 234)),
        ]
        for label, bx, _, col in buttons:
            w = _font(11, bold=True).size(label)[0] + 16
            pygame.draw.rect(self.screen, col, (bx, SIM_H + 15, w, 30), border_radius=6)
            surf = _font(11, bold=True).render(label, True, (255, 255, 255))
            self.screen.blit(surf, (bx + 8, SIM_H + 22))

    def _handle_key(self, key: int) -> Optional[UICommand]:
        mapping = {
            pygame.K_SPACE:   UICommand("pause"),
            pygame.K_r:       UICommand("reset"),
            pygame.K_e:       UICommand("emergency"),
            pygame.K_a:       UICommand("accident"),
            pygame.K_1:       UICommand("scenario", "normal"),
            pygame.K_2:       UICommand("scenario", "peak_hour"),
            pygame.K_3:       UICommand("scenario", "emergency"),
            pygame.K_4:       UICommand("scenario", "accident"),
            pygame.K_PLUS:    UICommand("speed_up"),
            pygame.K_KP_PLUS: UICommand("speed_up"),
            pygame.K_MINUS:   UICommand("speed_down"),
            pygame.K_KP_MINUS:UICommand("speed_down"),
            pygame.K_f:       UICommand("fullscreen"),
            pygame.K_d:       UICommand("toggle_debug"),
            pygame.K_ESCAPE:  UICommand("quit"),
        }
        algo_map = {
            pygame.K_F1: "astar", pygame.K_F2: "beam", pygame.K_F3: "bfs",
            pygame.K_F4: "dfs", pygame.K_F5: "hillclimb", pygame.K_F6: "minimax", pygame.K_F7: "auto",
        }
        if key in algo_map:
            self._algo = algo_map[key]
            return UICommand("set_algo", self._algo)
        if not self._splash_done:
            self._splash_done = True
            return None
        return mapping.get(key)

    def _handle_click(self, pos: tuple) -> Optional[UICommand]:
        if not self._splash_done:
            self._splash_done = True
            return None
        mx, my = pos
        if my < SIM_H: return None
        # Widths depend on text now, approximations:
        btn_regions = [
            (340, 435, "pause"), (450, 505, "reset"), (515, 595, "emergency"), (605, 680, "accident"),
        ]
        for x1, x2, action in btn_regions:
            if x1 <= mx <= x2: return UICommand(action)
        return None

    def set_speed(self, speed: float) -> None: self._speed = speed
    def set_algo(self, algo: str) -> None: self._algo = algo
    def toggle_debug(self) -> None: self._debug_mode = not self._debug_mode


