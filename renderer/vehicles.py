"""
renderer/vehicles.py
====================
Draws vehicles with drop shadows, crisp color definitions, and clean UI indicators.
"""

import pygame
from typing import List
from core.state import TrafficState, Direction
from core.simulation import Vehicle

CAR_W, CAR_H   = 20, 12
BUS_W, BUS_H   = 28, 14
TRUCK_W        = 26
AMBU_W, AMBU_H = 24, 13

_font_obj: pygame.font.Font = None

def _get_font(size: int = 10) -> pygame.font.Font:
    global _font_obj
    if _font_obj is None:
        _font_obj = pygame.font.SysFont("segoeui, arial, helvetica", size, bold=True)
    return _font_obj


def draw_vehicles(surface: pygame.Surface, vehicles: List[Vehicle], state: TrafficState) -> None:
    for direction, lane in state.lanes.items():
        if lane.blocked:
            _draw_blocked_overlay(surface, direction)

    for v in vehicles:
        _draw_vehicle(surface, v)

def _draw_vehicle(surface: pygame.Surface, v: Vehicle) -> None:
    x, y   = int(v.position[0]), int(v.position[1])
    is_ns  = v.direction in (Direction.NORTH, Direction.SOUTH)

    w, h = (CAR_W, CAR_H)
    if v.vehicle_type == "bus":
        w, h = (BUS_W, BUS_H) if is_ns else (BUS_H, BUS_W)
    elif v.vehicle_type == "truck":
        w, h = (TRUCK_W, 13) if is_ns else (13, TRUCK_W)
    elif v.vehicle_type == "ambulance":
        w, h = (AMBU_W, AMBU_H) if is_ns else (AMBU_H, AMBU_W)
    else:  # car
        w, h = (CAR_W, CAR_H) if is_ns else (CAR_H, CAR_W)

    rect = pygame.Rect(x - w // 2, y - h // 2, w, h)

    # 1. Drop shadow for depth
    shadow_rect = rect.copy()
    shadow_rect.move_ip(3, 3)
    shadow_surf = pygame.Surface((w+6, h+6), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, (0, 0, 0, 50), (3, 3, w, h), border_radius=4)
    surface.blit(shadow_surf, (shadow_rect.left - 3, shadow_rect.top - 3))

    color = v.color
    if v.vehicle_type == "ambulance":
        color = (229, 62, 62) if v.flash_state else (255, 255, 255)

    # 2. Main body
    line_col = (max(0, color[0]-40), max(0, color[1]-40), max(0, color[2]-40))
    pygame.draw.rect(surface, color, rect, border_radius=4)
    pygame.draw.rect(surface, line_col, rect, 1, border_radius=4)

    # 3. Windshield/Details
    ww, wh = max(4, w // 3), max(3, h // 3)
    
    if v.direction == Direction.SOUTH:
        wr = pygame.Rect(x - ww // 2, rect.top + 2, ww, wh)
    elif v.direction == Direction.NORTH:
        wr = pygame.Rect(x - ww // 2, rect.bottom - wh - 2, ww, wh)
    elif v.direction == Direction.EAST:
        wr = pygame.Rect(rect.left + 2, y - wh // 2, ww, wh)
    else:
        wr = pygame.Rect(rect.right - ww - 2, y - wh // 2, ww, wh)
        
    pygame.draw.rect(surface, (170, 210, 240), wr, border_radius=2)
    pygame.draw.rect(surface, (255, 255, 255, 80), (rect.left+1, rect.top+1, w-2, 3), border_radius=2)

    # Special icons
    if v.vehicle_type == "ambulance":
        mx, my = x, y
        c_icon = (255, 255, 255) if v.flash_state else (229, 62, 62)
        pygame.draw.line(surface, c_icon, (mx - 3, my),     (mx + 3, my),     2)
        pygame.draw.line(surface, c_icon, (mx,     my - 3), (mx,     my + 3), 2)

    if v.vehicle_type == "bus":
        label = _get_font(9).render("BUS", True, (45, 55, 72))
        surface.blit(label, (x - label.get_width() // 2, y - label.get_height() // 2))

def _draw_blocked_overlay(surface: pygame.Surface, direction: Direction) -> None:
    from renderer.road import CX, CY, ROAD_HALF, ROAD_LEN

    cx, cy, w, h = 0, 0, 0, 0
    if direction == Direction.NORTH:
        cx, cy, w, h = CX - ROAD_HALF, CY - ROAD_LEN, 40, ROAD_LEN - ROAD_HALF
    elif direction == Direction.SOUTH:
        cx, cy, w, h = CX, CY + ROAD_HALF, 40, ROAD_LEN - ROAD_HALF
    elif direction == Direction.EAST:
        cx, cy, w, h = CX + ROAD_HALF, CY - ROAD_HALF, ROAD_LEN - ROAD_HALF, 40
    else:
        cx, cy, w, h = CX - ROAD_LEN, CY, ROAD_LEN - ROAD_HALF, 40

    # Diagonal hatching for blocked lane
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(overlay, (229, 62, 62, 80), (0, 0, w, h))
    surface.blit(overlay, (cx, cy))

    # Clean Warning Icon
    mx, my = cx + w // 2, cy + h // 2
    pygame.draw.circle(surface, (255, 255, 255), (mx, my), 14)
    pygame.draw.circle(surface, (229, 62, 62), (mx, my), 14, 3)
    text = _get_font(12).render("!", True, (229, 62, 62))
    surface.blit(text, (mx - text.get_width() // 2, my - text.get_height() // 2))
