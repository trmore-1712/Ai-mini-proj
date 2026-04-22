"""
renderer/road.py
================
Draws the 4-way intersection road surface and markings.
Refined for a clean, non-neon, realistic styling.
"""

import pygame
from core.state import TrafficState, Direction

# Modern aesthetic colors
ROAD_COLOR     = (85, 95, 105)       # Solid slate asphalt
MARKING_COLOR  = (240, 245, 250)     # Clean white
ZEBRA_COLOR    = (230, 235, 240)
ISLAND_COLOR   = (150, 160, 170)

# Intersection layout
CX, CY      = 430, 310
ROAD_W      = 80
ROAD_HALF   = ROAD_W // 2
ROAD_LEN    = 220
LANE_W      = ROAD_W // 2

def draw_road(surface: pygame.Surface, state: TrafficState) -> None:
    _draw_road_surface(surface)
    _draw_lane_heat(surface, state)
    _draw_lane_markings(surface)
    _draw_zebra_crossings(surface)
    _draw_stop_lines(surface)
    _draw_intersection_box(surface)

def _draw_road_surface(surface: pygame.Surface) -> None:
    # E-W
    pygame.draw.rect(surface, ROAD_COLOR, (CX - ROAD_LEN, CY - ROAD_HALF, ROAD_LEN * 2, ROAD_W))
    # N-S
    pygame.draw.rect(surface, ROAD_COLOR, (CX - ROAD_HALF, CY - ROAD_LEN, ROAD_W, ROAD_LEN * 2))

def _draw_lane_heat(surface: pygame.Surface, state: TrafficState) -> None:
    """Soft, transparent queue indicator instead of heavy neon heatmap."""
    heat_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    
    def get_heat_color(count: int):
        if count <= 2: return None
        if count <= 6: return (237, 201, 72, 40)   # soft yellow
        return (229, 62, 62, 45)                   # soft red
        
    directions = [
        (Direction.NORTH, (CX - ROAD_HALF, CY - ROAD_LEN, ROAD_W, ROAD_LEN - ROAD_HALF)),
        (Direction.SOUTH, (CX - ROAD_HALF, CY + ROAD_HALF, ROAD_W, ROAD_LEN - ROAD_HALF)),
        (Direction.EAST,  (CX + ROAD_HALF, CY - ROAD_HALF, ROAD_LEN - ROAD_HALF, ROAD_W)),
        (Direction.WEST,  (CX - ROAD_LEN,  CY - ROAD_HALF, ROAD_LEN - ROAD_HALF, ROAD_W)),
    ]
    
    for direction, rect in directions:
        col = get_heat_color(state.lanes[direction].vehicle_count)
        if col:
            pygame.draw.rect(heat_surf, col, rect)
            
    surface.blit(heat_surf, (0, 0))

def _draw_lane_markings(surface: pygame.Surface) -> None:
    dash_len, dash_gap, dash_w = 15, 12, 2

    # Vertical
    for yy in [CY - ROAD_LEN, CY + ROAD_HALF]:
        ty = yy
        while ty < yy + ROAD_LEN - ROAD_HALF:
            pygame.draw.rect(surface, MARKING_COLOR, (CX - 1, ty, dash_w, dash_len))
            ty += dash_len + dash_gap

    # Horizontal
    for xx in [CX - ROAD_LEN, CX + ROAD_HALF]:
        tx = xx
        while tx < xx + ROAD_LEN - ROAD_HALF:
            pygame.draw.rect(surface, MARKING_COLOR, (tx, CY - 1, dash_len, dash_w))
            tx += dash_len + dash_gap

def _draw_zebra_crossings(surface: pygame.Surface) -> None:
    stripe_w = 6
    n_stripes = 6
    offset = ROAD_HALF + 10
    
    # N and S
    for i in range(n_stripes):
        x = CX - ROAD_HALF + 2 + i * (ROAD_W // n_stripes)
        pygame.draw.rect(surface, ZEBRA_COLOR, (x, CY - offset - stripe_w * 2, ROAD_W // n_stripes - 2, stripe_w * 2))
        pygame.draw.rect(surface, ZEBRA_COLOR, (x, CY + offset, ROAD_W // n_stripes - 2, stripe_w * 2))

    # E and W
    for i in range(n_stripes):
        y = CY - ROAD_HALF + 2 + i * (ROAD_W // n_stripes)
        pygame.draw.rect(surface, ZEBRA_COLOR, (CX + offset, y, stripe_w * 2, ROAD_W // n_stripes - 2))
        pygame.draw.rect(surface, ZEBRA_COLOR, (CX - offset - stripe_w * 2, y, stripe_w * 2, ROAD_W // n_stripes - 2))

def _draw_stop_lines(surface: pygame.Surface) -> None:
    lw = 4
    gap = ROAD_HALF + 2
    # Only draw stop lines across the incoming lanes
    pygame.draw.line(surface, MARKING_COLOR, (CX - ROAD_HALF, CY - gap), (CX, CY - gap), lw)           # N in
    pygame.draw.line(surface, MARKING_COLOR, (CX, CY + gap), (CX + ROAD_HALF, CY + gap), lw)           # S in
    pygame.draw.line(surface, MARKING_COLOR, (CX + gap, CY - ROAD_HALF), (CX + gap, CY), lw)           # E in
    pygame.draw.line(surface, MARKING_COLOR, (CX - gap, CY), (CX - gap, CY + ROAD_HALF), lw)           # W in

def _draw_intersection_box(surface: pygame.Surface) -> None:
    pygame.draw.rect(surface, ROAD_COLOR, (CX - ROAD_HALF, CY - ROAD_HALF, ROAD_W, ROAD_W))
    # Soft box junction lines
    pygame.draw.rect(surface, (237, 201, 72, 100), (CX - ROAD_HALF+2, CY - ROAD_HALF+2, ROAD_W-4, ROAD_W-4), 2)
