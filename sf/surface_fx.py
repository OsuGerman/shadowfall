"""Material- und Surface-Effekte (PLAN V-01..V-08).

Persistente Boden-Decals die das Storytelling unterstuetzen:
  - V-01 Wet-Surface nach Rain-Event
  - V-02 Ice-Surface auf Frost-Stack >=3
  - V-03 Scorched-Earth nach Fire-AoE
  - V-04 Glas-Splitter-Boden in Glaslord-Arena (siehe boss-spawn)
  - V-07 Dust-Trail bei Sprint/Dodge
  - V-08 Cloth-Sim Verlet fuer Banner

Architektur:
  - `SurfaceFXSystem` haelt eine Liste von `Decal`-Dicts mit:
        {x, y, kind, life, life_max, radius, color}
  - `update(dt)` decayed alle Decals, entfernt expired.
  - `draw(game, screen)` rendert vor Entities aber nach Tiles.
  - Module-API: `spawn_wet_patch`, `spawn_ice_crack`,
                `spawn_scorched_earth`, `spawn_dust_puff`.

Pygame-Native — keine echten Materials, sondern alpha-blended Decals.
"""

import math
import random
import pygame


# ============================================================
# DECAL-KINDS
# ============================================================
class DecalKind:
    WET = 'wet'
    ICE = 'ice'
    SCORCHED = 'scorched'
    GLASS = 'glass'
    DUST = 'dust'


# Default-Lifetime + Color pro Kind
_DEFAULTS = {
    DecalKind.WET:      (6.0,  (140, 180, 220), 45),
    DecalKind.ICE:      (10.0, (200, 230, 250), 60),
    DecalKind.SCORCHED: (15.0, ( 60,  40,  30), 80),
    DecalKind.GLASS:    (30.0, (220, 230, 255), 50),
    DecalKind.DUST:     (1.5,  (180, 150, 110), 30),
}


class SurfaceFXSystem:
    """Container fuer alle Surface-Effekte einer Szene."""

    def __init__(self):
        self.decals = []
        # Caps pro Kind (Performance — sonst staut sich z.B. Wet auf)
        self.caps = {
            DecalKind.WET:      120,
            DecalKind.ICE:      40,
            DecalKind.SCORCHED: 80,
            DecalKind.GLASS:    150,
            DecalKind.DUST:     80,
        }

    def clear(self):
        self.decals = []

    def spawn(self, x, y, kind, radius=None, life=None, color=None):
        defaults = _DEFAULTS.get(kind, (5.0, (180, 180, 180), 40))
        life_max = life if life is not None else defaults[0]
        col = color if color is not None else defaults[1]
        r = radius if radius is not None else defaults[2]
        d = {
            'x': float(x), 'y': float(y),
            'kind': kind,
            'life': life_max, 'life_max': life_max,
            'radius': r, 'color': col,
            'jitter': random.uniform(0, math.tau),
        }
        # Cap-Filter
        cap = self.caps.get(kind, 60)
        same = [k for k in self.decals if k['kind'] == kind]
        if len(same) >= cap:
            # Drop oldest of same kind
            for k in same[:len(same) - cap + 1]:
                self.decals.remove(k)
        self.decals.append(d)
        return d

    def spawn_wet_patch(self, x, y, radius=80):
        return self.spawn(x, y, DecalKind.WET, radius=radius, life=8.0)

    def spawn_ice_crack(self, x, y, radius=70):
        return self.spawn(x, y, DecalKind.ICE, radius=radius, life=12.0)

    def spawn_scorched_earth(self, x, y, radius=90):
        return self.spawn(x, y, DecalKind.SCORCHED,
                          radius=radius, life=18.0)

    def spawn_glass_shards(self, x, y, radius=120):
        return self.spawn(x, y, DecalKind.GLASS, radius=radius, life=60.0)

    def spawn_dust_puff(self, x, y, radius=20, color=(200, 180, 130)):
        return self.spawn(x, y, DecalKind.DUST, radius=radius,
                          color=color, life=1.5)

    def update(self, dt):
        keep = []
        for d in self.decals:
            d['life'] -= dt
            if d['life'] > 0:
                keep.append(d)
        self.decals = keep

    def has_ice_near(self, x, y, radius=80):
        """V-02: Check ob nearby ein Ice-Decal liegt (fuer Player-Slide)."""
        r2 = radius * radius
        for d in self.decals:
            if d['kind'] != DecalKind.ICE:
                continue
            dx = d['x'] - x
            dy = d['y'] - y
            if dx * dx + dy * dy <= r2:
                return True
        return False

    def draw(self, game, screen):
        for d in self.decals:
            self._draw_decal(game, screen, d)

    def _draw_decal(self, game, screen, d):
        sx, sy = game.w2s_xy(d['x'], d['y'])
        r = int(d['radius'])
        # Off-screen cull (cheap)
        if sx < -r or sx > screen.get_width() + r:
            return
        if sy < -r or sy > screen.get_height() + r:
            return
        life_frac = max(0.0, d['life'] / d['life_max'])
        kind = d['kind']
        col = d['color']
        if kind == DecalKind.WET:
            alpha = int(60 * life_frac)
            patch = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            # Spiegelnde Pfuetze: zentraler heller Glanz
            pygame.draw.ellipse(patch, (*col, alpha), (0, r // 2, r * 2, r))
            # Highlight-Streifen (Sinus-versetzt fuer „Atmen")
            hi_alpha = int(40 * life_frac)
            t = pygame.time.get_ticks() / 1000.0
            off = int(math.sin(t * 0.3 + d['jitter']) * 4)
            pygame.draw.ellipse(patch, (220, 230, 250, hi_alpha),
                                (r // 3, r // 2 + 6 + off, r, r // 3))
            screen.blit(patch, (sx - r, sy - r))
        elif kind == DecalKind.ICE:
            alpha = int(120 * life_frac)
            patch = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            # Kristallstruktur als Kreis-Cluster
            pygame.draw.circle(patch, (*col, alpha // 2), (r, r), r)
            # Risse-Linien (deterministisch durch jitter)
            rng = random.Random(int(d['jitter'] * 1000))
            for _ in range(6):
                a = rng.uniform(0, math.tau)
                rl = rng.randint(r // 2, r)
                ex = int(r + math.cos(a) * rl)
                ey = int(r + math.sin(a) * rl)
                pygame.draw.line(patch, (255, 255, 255, alpha),
                                  (r, r), (ex, ey), 2)
            screen.blit(patch, (sx - r, sy - r))
        elif kind == DecalKind.SCORCHED:
            alpha = int(180 * life_frac)
            patch = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            # Dunkle Sengflaeche
            pygame.draw.ellipse(patch, (*col, alpha), (0, 0, r * 2, r * 2))
            # Glut-Punkte
            rng = random.Random(int(d['jitter'] * 1000))
            for _ in range(8):
                px = rng.randint(r // 4, int(r * 1.5))
                py = rng.randint(r // 4, int(r * 1.5))
                pygame.draw.circle(patch, (180, 80, 30, alpha // 2),
                                    (px, py), 2)
            screen.blit(patch, (sx - r, sy - r))
        elif kind == DecalKind.GLASS:
            alpha = int(140 * life_frac)
            patch = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            rng = random.Random(int(d['jitter'] * 1000))
            for _ in range(18):
                a = rng.uniform(0, math.tau)
                rl = rng.randint(r // 3, r)
                ex = int(r + math.cos(a) * rl)
                ey = int(r + math.sin(a) * rl)
                pygame.draw.polygon(
                    patch, (*col, alpha),
                    [(r, r), (ex, ey),
                     (ex + rng.randint(-3, 3),
                      ey + rng.randint(-3, 3))])
            screen.blit(patch, (sx - r, sy - r))
        elif kind == DecalKind.DUST:
            alpha = int(80 * life_frac)
            patch = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(patch, (*col, alpha), (0, 0, r * 2, r * 2))
            screen.blit(patch, (sx - r, sy - r))


# ============================================================
# V-08 CLOTH-SIM (VERLET BANNER)
# ============================================================

class VerletCloth:
    """4-Knoten Verlet-Chain fuer Banner / Cloth.

    Knoten 0 ist statisch (Anker), 1-3 schwingen.  Wind-Phase wird
    von extern getrieben (globaler `wind_t`).
    """
    def __init__(self, anchor_x, anchor_y, length=50, segments=4,
                  color=(190, 150, 90)):
        self.anchor = (float(anchor_x), float(anchor_y))
        self.color = color
        self.segments = segments
        self.length = float(length)
        self.seg_len = length / max(1, segments - 1)
        self.points = []
        self.prev_points = []
        for i in range(segments):
            x = anchor_x
            y = anchor_y + i * self.seg_len
            self.points.append([x, y])
            self.prev_points.append([x, y])

    def update(self, dt, wind_x=0.0, gravity=180.0):
        # Verlet-Integration
        for i in range(1, self.segments):
            px, py = self.points[i]
            ppx, ppy = self.prev_points[i]
            vx = (px - ppx) * 0.96
            vy = (py - ppy) * 0.96
            ax = wind_x
            ay = gravity
            new_x = px + vx + ax * dt * dt * 60
            new_y = py + vy + ay * dt * dt * 60
            self.prev_points[i] = [px, py]
            self.points[i] = [new_x, new_y]
        # Constrain to segment length
        self.points[0] = list(self.anchor)
        for _ in range(3):  # 3 iterations stabilize
            for i in range(1, self.segments):
                ax, ay = self.points[i - 1]
                bx, by = self.points[i]
                dx = bx - ax
                dy = by - ay
                d = math.hypot(dx, dy)
                if d < 1e-3:
                    continue
                diff = (d - self.seg_len) / d
                if i == 1:
                    self.points[i][0] -= dx * diff
                    self.points[i][1] -= dy * diff
                else:
                    self.points[i][0] -= dx * diff * 0.5
                    self.points[i - 1][0] += dx * diff * 0.5
                    self.points[i][1] -= dy * diff * 0.5
                    self.points[i - 1][1] += dy * diff * 0.5

    def draw(self, game, screen, width=18):
        """Render the cloth as a 3-point polygon strip with the color."""
        if len(self.points) < 2:
            return
        # Build polygon: left + right edge (width offset perpendicular to chain)
        verts_left = []
        verts_right = []
        for i, (px, py) in enumerate(self.points):
            sx, sy = game.w2s_xy(px, py)
            # Perpendicular: half-width to the left/right
            if i > 0:
                lpx, lpy = self.points[i - 1]
                dx = px - lpx
                dy = py - lpy
                d = math.hypot(dx, dy)
                if d < 1e-3:
                    nx, ny = 1, 0
                else:
                    # Perpendicular: rotate 90 deg
                    nx = -dy / d
                    ny = dx / d
            else:
                nx, ny = 1, 0
            offset = width * (0.4 + 0.6 * (i / max(1, len(self.points) - 1)))
            lx = sx + nx * (offset * 0.5)
            ly = sy + ny * (offset * 0.5)
            rx = sx - nx * (offset * 0.5)
            ry = sy - ny * (offset * 0.5)
            verts_left.append((lx, ly))
            verts_right.append((rx, ry))
        verts = verts_left + list(reversed(verts_right))
        try:
            pygame.draw.polygon(screen, self.color, verts)
            # Saum-Highlight
            hi_col = tuple(min(255, c + 40) for c in self.color)
            for i in range(len(verts_left) - 1):
                pygame.draw.line(screen, hi_col,
                                  verts_left[i], verts_left[i + 1], 1)
        except (ValueError, TypeError):
            pass
