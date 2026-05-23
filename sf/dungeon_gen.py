"""Procedurale Dungeon-Generierung: Tile-Grid mit Räumen und Korridoren."""

import math
import random
import pygame
from pygame.math import Vector2

CELL = 80   # Welt-Einheiten pro Zelle


# Cell-Inhalt:
VOID    = 0
FLOOR   = 1
WALL    = 2  # explizit (sonst wird aus VOID neben FLOOR abgeleitet)
DOOR    = 3
TRAP    = 4
SECRET  = 5  # geheimer Floor (zunächst als Wall getarnt, deckt sich auf)


class Room:
    """Rechteckiger Raum im Tile-Grid (in Cell-Koordinaten)."""
    __slots__ = ('x', 'y', 'w', 'h', 'kind',
                 'event', 'event_triggered')

    def __init__(self, x, y, w, h, kind='normal'):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.kind = kind  # 'normal' | 'spawn' | 'boss' | 'treasure' | 'fountain' | 'arena' | 'library' | 'secret'
        # Update #27: dynamic event-tag (None oder str-Key).
        self.event = None
        self.event_triggered = False

    @property
    def cx(self):
        return self.x + self.w // 2

    @property
    def cy(self):
        return self.y + self.h // 2

    def center(self):
        return (self.cx, self.cy)

    def intersects(self, other, padding=1):
        return not (
            self.x + self.w + padding <= other.x or
            other.x + other.w + padding <= self.x or
            self.y + self.h + padding <= other.y or
            other.y + other.h + padding <= self.y
        )

    def contains_cell(self, cx, cy):
        return self.x <= cx < self.x + self.w and self.y <= cy < self.y + self.h


class DungeonGrid:
    """Tile-basiertes Grid für ein Dungeon. Zellen sind 80 Welt-Einheiten groß.
    Origin so, dass Spawn-Raum-Zentrum ≈ (0,0).
    """
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.tiles = [[VOID] * w for _ in range(h)]
        self.cell = CELL
        self.origin = Vector2(0, 0)  # wird nach Spawn-Raum gesetzt
        self.rooms = []
        self.traps = []   # list of (cx, cy, trap_type)
        self.secrets = [] # list of Room objects

    # ---- Koordinaten ----
    def world_to_cell(self, wx, wy):
        cx = int((wx - self.origin.x) / self.cell)
        cy = int((wy - self.origin.y) / self.cell)
        return cx, cy

    def cell_to_world_center(self, cx, cy):
        return (self.origin.x + (cx + 0.5) * self.cell,
                self.origin.y + (cy + 0.5) * self.cell)

    def cell_to_world_corner(self, cx, cy):
        return (self.origin.x + cx * self.cell,
                self.origin.y + cy * self.cell)

    # ---- Abfragen ----
    def in_bounds(self, cx, cy):
        return 0 <= cx < self.w and 0 <= cy < self.h

    def get(self, cx, cy):
        if not self.in_bounds(cx, cy):
            return VOID
        return self.tiles[cy][cx]

    def is_walkable(self, cx, cy):
        t = self.get(cx, cy)
        return t in (FLOOR, DOOR, TRAP, SECRET)

    def is_walkable_world(self, wx, wy):
        cx, cy = self.world_to_cell(wx, wy)
        return self.is_walkable(cx, cy)

    def collide_circle(self, x, y, r):
        """True wenn ein Kreis um (x,y) mit Radius r in eine Wand ragt.

        Update #147 (User-Report „durch Wände laufen"): Robuster Check.
        - Center-Sample (vorher fehlend!) — catched 1-Cell-Walls
        - 16 statt 8 Perimeter-Samples — catched dünne Wände
        - Inner-Ring bei r/2 zusätzlich (catched Tunneling bei großem r)
        """
        # 1. Center
        if not self.is_walkable_world(x, y):
            return True
        # 2. 16 Perimeter-Samples
        for k in range(16):
            a = k * math.pi / 8
            if not self.is_walkable_world(
                    x + math.cos(a) * r, y + math.sin(a) * r):
                return True
        # 3. 8 Inner-Ring-Samples bei r/2 (catched dünne 1-Cell-Walls)
        if r > 10:
            inner_r = r * 0.5
            for k in range(8):
                a = k * math.pi / 4 + math.pi / 8  # offset rotated
                if not self.is_walkable_world(
                        x + math.cos(a) * inner_r,
                        y + math.sin(a) * inner_r):
                    return True
        return False

    def slide_move(self, x, y, dx, dy, r):
        """Bewege (x,y) um (dx,dy) mit Wand-Gleiten. Returnt (new_x, new_y).

        Update #147 (User-Report „durch Wände laufen"): Sub-Stepping bei
        großen Moves (Dodge mit 560 px/s × 0.05 dt = 28 px > cell/2=16).
        Splittet den Move in N kleine Schritte um Tunneling zu verhindern.
        """
        # Sub-Stepping wenn der Move > cell/3 ist (cell=32 → 10 px)
        move_len = math.hypot(dx, dy)
        max_step = self.cell * 0.33
        if move_len > max_step:
            n_steps = int(math.ceil(move_len / max_step))
            step_dx = dx / n_steps
            step_dy = dy / n_steps
            cur_x, cur_y = x, y
            for _ in range(n_steps):
                cur_x, cur_y = self._slide_step(
                    cur_x, cur_y, step_dx, step_dy, r)
            return cur_x, cur_y
        return self._slide_step(x, y, dx, dy, r)

    def _slide_step(self, x, y, dx, dy, r):
        """Single-Step-Slide ohne Sub-Division."""
        nx, ny = x + dx, y + dy
        if not self.collide_circle(nx, ny, r):
            return nx, ny
        if not self.collide_circle(nx, y, r):
            return nx, y
        if not self.collide_circle(x, ny, r):
            return x, ny
        return x, y

    def has_los(self, x1, y1, x2, y2):
        """Line-of-Sight: True wenn kein Wand-Cell auf der Linie liegt."""
        # Bresenham-artig durch Cells iterieren
        cx1, cy1 = self.world_to_cell(x1, y1)
        cx2, cy2 = self.world_to_cell(x2, y2)
        # Distanz in Cells
        dx = abs(cx2 - cx1)
        dy = abs(cy2 - cy1)
        sx_step = 1 if cx1 < cx2 else -1
        sy_step = 1 if cy1 < cy2 else -1
        err = dx - dy
        cx, cy = cx1, cy1
        steps = 0
        max_steps = dx + dy + 4
        while steps < max_steps:
            if (cx, cy) != (cx1, cy1) and (cx, cy) != (cx2, cy2):
                if not self.is_walkable(cx, cy):
                    return False
            if cx == cx2 and cy == cy2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx_step
            if e2 < dx:
                err += dx
                cy += sy_step
            steps += 1
        return True

    def astar(self, start_cell, end_cell, max_steps=300):
        """A* Pathfinding: returnt Liste von (cx,cy) Wegpunkten, oder None."""
        if start_cell == end_cell:
            return []
        if not self.is_walkable(*end_cell):
            # Suche nähestes walkable end
            for r in range(1, 5):
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if abs(dx) != r and abs(dy) != r:
                            continue
                        ncx, ncy = end_cell[0] + dx, end_cell[1] + dy
                        if self.is_walkable(ncx, ncy):
                            end_cell = (ncx, ncy)
                            break
                    if self.is_walkable(*end_cell):
                        break
                if self.is_walkable(*end_cell):
                    break
            else:
                return None
        import heapq
        open_set = [(0, 0, start_cell)]  # (f, tie-break counter, cell)
        came_from = {}
        g_score = {start_cell: 0}
        tie = 0
        steps = 0
        while open_set and steps < max_steps:
            steps += 1
            _, _, current = heapq.heappop(open_set)
            if current == end_cell:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path
            cx, cy = current
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = cx + dx, cy + dy
                if not self.is_walkable(nx, ny):
                    continue
                tentative_g = g_score[current] + 1
                if tentative_g < g_score.get((nx, ny), 1e9):
                    came_from[(nx, ny)] = current
                    g_score[(nx, ny)] = tentative_g
                    h = abs(nx - end_cell[0]) + abs(ny - end_cell[1])
                    tie += 1
                    heapq.heappush(open_set, (tentative_g + h, tie, (nx, ny)))
        return None  # kein Pfad innerhalb max_steps

    def find_walkable_near(self, x, y, max_radius=4):
        """Sucht nächste begehbare Zelle in Spirale.
        Returnt (wx, wy) der Zell-Mitte oder None.
        """
        cx, cy = self.world_to_cell(x, y)
        if self.is_walkable(cx, cy):
            return self.cell_to_world_center(cx, cy)
        for r in range(1, max_radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if abs(dx) != r and abs(dy) != r:
                        continue  # nur Ring
                    if self.is_walkable(cx + dx, cy + dy):
                        return self.cell_to_world_center(cx + dx, cy + dy)
        return None


def _fill_rect(grid, room, value=FLOOR):
    for cy in range(room.y, room.y + room.h):
        for cx in range(room.x, room.x + room.w):
            if grid.in_bounds(cx, cy):
                grid.tiles[cy][cx] = value


def _carve_corridor(grid, x1, y1, x2, y2):
    """L-förmiger Korridor (2 breit)."""
    # Horizontal first
    if random.random() < 0.5:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            grid.tiles[y1][x] = FLOOR
            if grid.in_bounds(x, y1 + 1):
                grid.tiles[y1 + 1][x] = FLOOR
        for y in range(min(y1, y2), max(y1, y2) + 1):
            grid.tiles[y][x2] = FLOOR
            if grid.in_bounds(x2 + 1, y):
                grid.tiles[y][x2 + 1] = FLOOR
    else:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            grid.tiles[y][x1] = FLOOR
            if grid.in_bounds(x1 + 1, y):
                grid.tiles[y][x1 + 1] = FLOOR
        for x in range(min(x1, x2), max(x1, x2) + 1):
            grid.tiles[y2][x] = FLOOR
            if grid.in_bounds(x, y2 + 1):
                grid.tiles[y2 + 1][x] = FLOOR


def generate(num_rooms=10, w=64, h=64, seed=None):
    """Erstellt ein DungeonGrid mit ~num_rooms Räumen.

    Returnt: (grid, room_list)
    """
    rng = random.Random(seed)
    grid = DungeonGrid(w, h)

    # Spawn-Raum in der Mitte (immer)
    spawn = Room(w // 2 - 3, h // 2 - 3, 7, 7, kind='spawn')
    _fill_rect(grid, spawn, FLOOR)
    grid.rooms.append(spawn)

    # Origin so, dass Spawn-Zentrum bei (0,0) liegt
    spawn_cx, spawn_cy = spawn.center()
    grid.origin = Vector2(-spawn_cx * grid.cell - grid.cell * 0.5,
                          -spawn_cy * grid.cell - grid.cell * 0.5)

    # Weitere Räume zufällig platzieren
    attempts = 0
    room_kinds = ['normal'] * 6 + ['treasure', 'fountain', 'arena', 'library']
    while len(grid.rooms) < num_rooms + 1 and attempts < 200:
        attempts += 1
        rw = rng.randint(5, 10)
        rh = rng.randint(5, 9)
        rx = rng.randint(2, w - rw - 2)
        ry = rng.randint(2, h - rh - 2)
        new_room = Room(rx, ry, rw, rh, kind=rng.choice(room_kinds))
        if any(new_room.intersects(r, padding=2) for r in grid.rooms):
            continue
        _fill_rect(grid, new_room, FLOOR)
        grid.rooms.append(new_room)
        # Verbinde zum nächstgelegenen bestehenden Raum
        nearest = min(grid.rooms[:-1],
                      key=lambda r: (r.cx - new_room.cx) ** 2 + (r.cy - new_room.cy) ** 2)
        _carve_corridor(grid, new_room.cx, new_room.cy, nearest.cx, nearest.cy)

    # Boss-Raum: weit weg vom Spawn, groß
    far = max(grid.rooms[1:],
              key=lambda r: (r.cx - spawn.cx) ** 2 + (r.cy - spawn.cy) ** 2)
    far.kind = 'boss'

    # Ein bis zwei geheime Räume (Secret) entfernt platziert
    for _ in range(2):
        attempts = 0
        while attempts < 30:
            attempts += 1
            rw, rh = rng.randint(4, 6), rng.randint(4, 6)
            rx = rng.randint(2, w - rw - 2)
            ry = rng.randint(2, h - rh - 2)
            sec = Room(rx, ry, rw, rh, kind='secret')
            if any(sec.intersects(r, padding=2) for r in grid.rooms):
                continue
            # Fülle mit SECRET (gerendert als Wand bis entdeckt)
            for cy in range(sec.y, sec.y + sec.h):
                for cx in range(sec.x, sec.x + sec.w):
                    if grid.in_bounds(cx, cy):
                        grid.tiles[cy][cx] = SECRET
            # Verbinde mit kürzestem Korridor zu nächstem Raum
            nearest = min(grid.rooms,
                          key=lambda r: (r.cx - sec.cx) ** 2 + (r.cy - sec.cy) ** 2)
            _carve_corridor(grid, sec.cx, sec.cy, nearest.cx, nearest.cy)
            grid.rooms.append(sec)
            grid.secrets.append(sec)
            break

    # Trap-Tiles in einigen normalen Räumen
    trap_types = ['spike', 'fire', 'arrow', 'plate']
    for room in grid.rooms:
        if room.kind in ('spawn', 'boss', 'treasure', 'secret'):
            continue
        if rng.random() < 0.45:
            ttype = rng.choice(trap_types)
            n = rng.randint(2, 4)
            for _ in range(n):
                tx = rng.randint(room.x + 1, room.x + room.w - 2)
                ty = rng.randint(room.y + 1, room.y + room.h - 2)
                if grid.tiles[ty][tx] == FLOOR:
                    grid.tiles[ty][tx] = TRAP
                    grid.traps.append((tx, ty, ttype))

    return grid


def reveal_secret(grid, room):
    """Geheimraum aufdecken: SECRET → FLOOR."""
    if room.kind != 'secret':
        return
    for cy in range(room.y, room.y + room.h):
        for cx in range(room.x, room.x + room.w):
            if grid.tiles[cy][cx] == SECRET:
                grid.tiles[cy][cx] = FLOOR
    room.kind = 'revealed_secret'
