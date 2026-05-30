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
            # Update #184 (User-Fix „wirkt draufgelegt, keine Tiefe"):
            # 5-Layer Render statt eine Ellipse + ein Highlight.
            # Drop-Shadow, Inset-Rim, Wasser-Body, Wellen-Linien,
            # Specular-Hotspot + Bloom.
            life_alpha_mul = life_frac
            patch = pygame.Surface((r * 2 + 8, r + 12), pygame.SRCALPHA)
            cx_p, cy_p = r + 4, r // 2 + 6
            t_now = pygame.time.get_ticks() / 1000.0

            # Layer 1 — Soft Drop-Shadow (radialer Fade)
            for rad_mul, a in ((1.15, 18), (1.05, 28), (0.95, 38)):
                sh_w = int(r * 2 * rad_mul)
                sh_h = int(r * rad_mul)
                sh_sf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
                pygame.draw.ellipse(sh_sf,
                                     (15, 22, 32, int(a * life_alpha_mul)),
                                     (0, 0, sh_w, sh_h))
                patch.blit(sh_sf, (cx_p - sh_w // 2,
                                    cy_p - sh_h // 2 + 1))

            # Layer 2 — Inset-Rim (dunkler Pfuetzen-Rand)
            rim_alpha = int(100 * life_alpha_mul)
            pygame.draw.ellipse(patch, (25, 40, 55, rim_alpha),
                                 (cx_p - r, cy_p - r // 2, r * 2, r))

            # Layer 3 — Wasserkoerper (zwei Schichten: dunkler unten,
            # heller oben — Himmel-Reflex)
            body_alpha_lo = int(80 * life_alpha_mul)
            pygame.draw.ellipse(patch,
                                 (55, 95, 125, body_alpha_lo),
                                 (cx_p - r + 2, cy_p - r // 2 + 1,
                                  r * 2 - 4, r - 2))
            body_alpha_hi = int(60 * life_alpha_mul)
            pygame.draw.ellipse(patch,
                                 (*col, body_alpha_hi),
                                 (cx_p - r + 4, cy_p - r // 2 + 1,
                                  r * 2 - 8, r // 2 + 1))

            # Layer 4 — Wellen-Linien (2 sinus-modulierte Highlights)
            wave_a = int(50 * life_alpha_mul)
            if wave_a > 4:
                wave_t = t_now + d['jitter']
                for w_i in range(2):
                    wy = cy_p - 2 + w_i * 3
                    pts = []
                    for px in range(-r + 6, r - 6, 3):
                        rel_y = (wy - cy_p) / max(1, r // 2)
                        if abs(rel_y) >= 1:
                            continue
                        max_x = (r - 4) * (1 - rel_y * rel_y) ** 0.5
                        if abs(px) > max_x:
                            continue
                        yoff = math.sin(wave_t * 1.3 + px * 0.15
                                         + w_i * 0.7) * 0.7
                        pts.append((cx_p + px, wy + yoff))
                    if len(pts) >= 2:
                        pygame.draw.lines(patch,
                                           (200, 220, 240, wave_a),
                                           False, pts, 1)

            # Layer 5 — Specular-Hotspot + Bloom (Lichtreflex
            # oben-links, atmend versetzt)
            spec_off = int(math.sin(t_now * 0.3 + d['jitter']) * 3)
            hot_x = cx_p - int(r * 0.32)
            hot_y = cy_p - int(r * 0.25) + spec_off
            spec_a = int(140 * life_alpha_mul)
            # Bloom
            bloom_w = max(4, int(r * 0.6))
            bloom = pygame.Surface((bloom_w, bloom_w // 2),
                                    pygame.SRCALPHA)
            pygame.draw.ellipse(bloom,
                                 (180, 220, 245, spec_a // 3),
                                 (0, 0, bloom_w, bloom_w // 2))
            patch.blit(bloom, (hot_x - bloom_w // 2,
                                hot_y - bloom_w // 4))
            # Core
            core_w = max(3, int(r * 0.28))
            core_h = max(2, core_w // 2)
            pygame.draw.ellipse(patch,
                                 (235, 245, 255, spec_a),
                                 (hot_x - core_w // 2,
                                  hot_y - core_h // 2,
                                  core_w, core_h))
            # Glint
            pygame.draw.ellipse(patch,
                                 (255, 255, 255, min(240,
                                                      spec_a + 60)),
                                 (hot_x - 2, hot_y - 1, 4, 2))

            screen.blit(patch, (sx - cx_p, sy - cy_p))
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
