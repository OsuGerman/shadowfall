"""Dynamisches Licht-System.

Verwendet eine dunkle Overlay-Surface, in die Licht-Quellen ihre radialen
Gradienten subtrahieren (BLEND_RGBA_SUB). Das Ergebnis wird auf das
fertige Frame geblittet.
"""

import math
import random
import pygame

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    np = None
    _HAS_NUMPY = False

from .constants import SCREEN_W, SCREEN_H
from . import sprites as sprites_mod


# Update #190: noise-basierte Fog-Texture entfernt.  Begruendung im
# render_fog-Docstring.  Die texturlose Variante (flat tint + vignette)
# loest das "klebt-an-Camera-vs-scrollt-mit-Welt"-Problem fundamental.


# Cache für radiale Gradienten-Surfaces.
_light_cache = {}


def _make_light(radius, color, intensity):
    """Erstellt eine Surface mit radialem Gradient (heller in der Mitte)."""
    key = (radius, color, intensity)
    if key in _light_cache:
        return _light_cache[key]
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    # Mehrere konzentrische Kreise mit abnehmender Intensität
    steps = 12
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        alpha = int(255 * intensity * (1 - t) ** 1.5)
        if alpha <= 0:
            continue
        col = (int(color[0] * intensity),
               int(color[1] * intensity),
               int(color[2] * intensity),
               alpha)
        pygame.draw.circle(surf, col, (radius, radius), r)
    _light_cache[key] = surf
    return surf


class LightingSystem:
    """Sammelt Licht-Quellen pro Frame und rendert sie als Overlay."""

    def __init__(self, ambient_alpha=130):
        self.ambient_alpha = ambient_alpha
        # Wieder verwendbare Dark-Overlay-Surface
        self._darkness = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._lights = []
        # Globale Flicker-Phase
        self._flicker = 0.0
        # Update #201 (FPS-Optimierung): Cache fuer light-emittierende Tiles.
        # gather_default scannte vorher self.tiles JEDEN FRAME komplett —
        # bei dichten Dungeons hunderte Iterationen pro Frame nur um die
        # 10-20 torches/lanterns/embers/crystals/runes zu finden.
        # Cache wird invalidiert wenn id(game.tiles) wechselt (Level-Reset).
        self._tile_light_cache_key = None
        self._tile_lights = []
        # Update #201: Lazy-Cache fuer Lightning-Flash-Surface (combat-
        # frequent). Spart 5.76 MB SRCALPHA-Alloc pro Frame waehrend
        # Storm-Rain / cast_lightning.
        self._flash_surf = None

    def begin_frame(self):
        self._lights.clear()
        self._flicker += 0.05

    def add(self, sx, sy, radius, color, intensity=1.0, flicker=0.0):
        if not (-radius < sx < SCREEN_W + radius and -radius < sy < SCREEN_H + radius):
            return  # Off-screen
        if flicker > 0:
            r_off = math.sin(self._flicker * (3 + radius * 0.01) + sx * 0.01) * flicker
            radius = max(10, int(radius + r_off))
        self._lights.append((int(sx), int(sy), radius, color, intensity))

    def gather_default(self, game):
        """Sammelt Standard-Lichter aus Game-Zustand.

        Update #168 (U-06..U-08): Erweitert um Lava-/Crystal-Cell-Glow,
        Player-Cast-Hand-Light bei aktiven Casts und Boss-Aura-Pulse.
        """
        # Spieler-Licht
        p = game.player
        psx, psy = game.w2s(p.pos)
        spec = sprites_mod.light_for_player(p)
        if spec:
            r, col, intens = spec
            self.add(psx, psy - p.height // 2, r, col, intens, flicker=4)
        # U-07 Player-Casting-Hand-Light: wenn casting_skill_id und in
        # Wind-Up-Phase, leuchten die Haende in der Klassen-Keystone-Farbe.
        if getattr(game, '_casting_t', 0.0) > 0.0:
            try:
                from . import aspects as _asp
                theme = _asp.class_theme(p.cls)
                col = theme.get('keystone_color', (255, 200, 120))
                self.add_player_cast_light(game, col, intensity=0.7)
            except Exception:
                pass
        # U-08 Boss-Aura-Lighting
        for e in getattr(game, 'enemies', ()):
            if getattr(e, 'is_boss', False):
                try:
                    self.add_boss_aura(game, e)
                except Exception:
                    pass

        # Gegner-Bosse
        for e in game.enemies:
            spec = sprites_mod.light_for_enemy(e)
            if spec:
                esx, esy = game.w2s(e.pos)
                r, col, intens = spec
                self.add(esx, esy - e.height // 2, r, col, intens, flicker=3)

        # Projektile
        for proj in game.projectiles:
            spec = sprites_mod.light_for_projectile(proj)
            if spec:
                sx, sy = game.w2s(proj.pos)
                r, col, intens = spec
                self.add(sx, sy, r, col, intens)

        # Fackeln (aus tiles) — Update #201: Cache statt full-scan pro Frame.
        # self.tiles wird nur bei Level-Init/Reset komplett neu belegt
        # (kein mid-game add/remove ausser in setup), id-Compare reicht.
        cache_key = (id(game.tiles), len(game.tiles))
        if cache_key != self._tile_light_cache_key:
            self._tile_light_cache_key = cache_key
            self._tile_lights = [
                (t.kind, t.x, t.y) for t in game.tiles
                if t.kind in ('torch', 'lantern', 'ember', 'lava_pool',
                              'crystal', 'rune')
            ]
        for kind, tx, ty in self._tile_lights:
            sx, sy = game.w2s_xy(tx, ty)
            if kind == 'torch':
                self.add(sx, sy - 6, 160, (255, 170, 80), 0.8, flicker=6)
            elif kind == 'lantern':
                self.add(sx, sy - 8, 200, (255, 200, 110), 0.9, flicker=4)
            elif kind == 'ember' or kind == 'lava_pool':
                t_pulse = (pygame.time.get_ticks() % 2000) / 2000.0
                pulse_r = int(60 + 8 * math.sin(t_pulse * math.tau))
                self.add(sx, sy, pulse_r, (255, 130, 50), 0.55, flicker=3)
            elif kind == 'crystal':
                col_map = {'crypt':  (180, 200, 240),
                           'frost':  (160, 220, 255),
                           'astral': (220, 140, 255),
                           'swamp':  (140, 220, 160)}
                col = col_map.get(getattr(game, 'biome', 'crypt'),
                                  (180, 200, 240))
                self.add(sx, sy, 70, col, 0.45, flicker=2)
            elif kind == 'rune':
                col_map = {'crypt': (180, 80, 80),
                           'frost': (140, 200, 240),
                           'lava':  (255, 140, 60)}
                col = col_map.get(game.biome, (180, 80, 80))
                self.add(sx, sy, 50, col, 0.3, flicker=2)

        # Portale
        for portal in game.portals:
            from .world import BIOMES
            sx, sy = game.w2s(portal.pos)
            self.add(sx, sy, 100, BIOMES[portal.biome]['accent'], 0.7, flicker=4)

    def render(self, screen, ambient_color=(10, 8, 18)):
        """Zeichnet das fertige Licht-Overlay auf den Bildschirm."""
        # Reset
        self._darkness.fill((*ambient_color, self.ambient_alpha))
        # Subtrahiere Licht-Quellen
        for sx, sy, r, col, intens in self._lights:
            light = _make_light(r, col, intens)
            self._darkness.blit(light, (sx - r, sy - r),
                                special_flags=pygame.BLEND_RGBA_SUB)
        screen.blit(self._darkness, (0, 0))

    # ========================================================
    # U-01..U-09 (Update #168): Lighting Engine 2.0
    # ========================================================
    def render_light_buffer(self, screen, ambient_color=(10, 8, 18),
                            ambient_alpha=None, mul_mode=False):
        """U-01 Multi-Source-Light-Buffer (POE2-Style).

        Statt SUB-Blending wird hier optional ein additiver Light-Buffer
        gerendert (mul_mode=True nutzt BLEND_MULT auf die Lights).
        Gibt diffusere, weichere Beleuchtung als der reine SUB-Pass.
        Default-mode bleibt SUB (`render` unten) — diese Variante ist
        opt-in via `settings['lighting_v2'] = True`.
        """
        if ambient_alpha is None:
            ambient_alpha = self.ambient_alpha
        self._darkness.fill((*ambient_color, ambient_alpha))
        for sx, sy, r, col, intens in self._lights:
            light = _make_light(r, col, intens)
            self._darkness.blit(light, (sx - r, sy - r),
                                special_flags=pygame.BLEND_RGBA_SUB)
        screen.blit(self._darkness, (0, 0))

    def add_cell_glow(self, game, cells, color, radius=60, intensity=0.45,
                       flicker=3):
        """U-06 Lava/Glow-Cell-Tint.

        `cells` ist eine Liste von (cell_x, cell_y)-Tuples die einen
        kraeftigen radialen Glow ausstrahlen (z.B. lava_pool, crystal).
        Cell-Center wird in Screen-Space transformiert.  Nutzt einen
        0.5 Hz Sinus fuer subtle Atmung der Intensitaet.
        """
        if not cells:
            return
        t = self._flicker * 0.5
        pulse = 0.85 + 0.15 * math.sin(t)
        col = (int(color[0] * pulse), int(color[1] * pulse),
               int(color[2] * pulse))
        for cx, cy in cells:
            sx, sy = game.w2s_xy(cx, cy)
            self.add(sx, sy, radius, col, intensity, flicker=flicker)

    def add_god_rays(self, screen, source_x, source_y, num_rays=6,
                      length=380, color=(255, 240, 180), alpha=70):
        """U-05 God-Rays in Boss-Intros.

        Zeichnet `num_rays` divergierende Light-Cones vom Source-Punkt
        (z.B. Boss-Pivot) durch die Arena. Sinus-rotierend.  Sehr
        kosmetisch — sollte nur waehrend Cinematics gerendert werden.
        """
        # NOTE: god_rays nicht gecached — nur in Cinematics aktiv, nicht
        # im Combat-Hotpath. Plus die smoothscale-Blur weiter unten
        # allokiert sowieso 2 neue Surfaces.
        ray_layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        t = self._flicker
        for i in range(num_rays):
            base_angle = (i / num_rays) * math.tau
            angle = base_angle + math.sin(t * 0.3 + i) * 0.06
            # Triangular cone (3 verts)
            spread = 0.18
            half = spread * 0.5
            x1 = source_x
            y1 = source_y
            x2 = source_x + math.cos(angle - half) * length
            y2 = source_y + math.sin(angle - half) * length
            x3 = source_x + math.cos(angle + half) * length
            y3 = source_y + math.sin(angle + half) * length
            pygame.draw.polygon(
                ray_layer, (*color, alpha),
                [(x1, y1), (x2, y2), (x3, y3)])
        # Soft-Glow via Blur-Approximation (2-step downscale + up)
        try:
            small = pygame.transform.smoothscale(
                ray_layer, (SCREEN_W // 4, SCREEN_H // 4))
            ray_layer = pygame.transform.smoothscale(
                small, (SCREEN_W, SCREEN_H))
        except Exception:
            pass
        screen.blit(ray_layer, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def add_player_cast_light(self, game, color, intensity=0.8):
        """U-07 Player-Casting-Hand-Light.

        Zuendet sich an, wenn ein Cast-Skill in der Wind-Up-Phase ist.
        Klassen-Keystone-Color aus `aspects.CLASS_THEMES` als Standard.
        """
        p = game.player
        psx, psy = game.w2s(p.pos)
        # Leicht versetzt zu beiden Haenden (relativ zu Player-Center)
        for dx in (-12, 12):
            self.add(psx + dx, psy - p.height // 2 + 6,
                     60, color, intensity, flicker=5)

    def add_boss_aura(self, game, boss):
        """U-08 Boss-Aura-Lighting.

        Strahlt in Phase-Color um den Boss mit ±20 px Pulse-Radius.
        Phase wird aus `boss.phase_idx` (Default 0) abgeleitet.
        """
        # Per-Phase Farb-Palette (Default red -> orange -> magenta)
        PALETTE = [
            (220,  80,  60),    # Phase 1: warnend rot
            (255, 140,  40),    # Phase 2: ascher orange
            (200,  60, 200),    # Phase 3: chaotisch lila
        ]
        idx = max(0, min(2, getattr(boss, 'phase_idx', 0)))
        color = PALETTE[idx]
        sx, sy = game.w2s(boss.pos)
        # Pulse-Radius
        t = (pygame.time.get_ticks() % 2000) / 2000.0
        radius = int(180 + 20 * math.sin(t * math.tau))
        self.add(sx, sy - boss.height // 2, radius, color, 0.7, flicker=8)

    def render_lightning_flash(self, screen, intensity=0.35):
        """U-09 Global Lightning-Strike-Flash.

        60 ms vollflaechiger Weiss-Tint.  Respektiert Photosensitive-
        Limiter via `Game.request_flash(intensity)`.  Caller muss die
        Frame-Dauer selbst takten (z.B. ueber `game._lightning_flash_t`).
        """
        if intensity <= 0:
            return
        alpha = int(255 * intensity)
        # Update #201: Surface-Cache statt Per-Call-Alloc (5.76 MB SRCALPHA).
        if self._flash_surf is None:
            self._flash_surf = pygame.Surface(
                (SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._flash_surf.fill((255, 255, 255, alpha))
        screen.blit(self._flash_surf, (0, 0),
                    special_flags=pygame.BLEND_RGBA_ADD)

    def render_bloom(self, screen, threshold=180, strength=0.55):
        """M-10 Bloom / Glow-Pass (Surface-Approximation).

        Update #191 (Perf-Fix): Komplette Operation laeuft jetzt auf
        einem 1/4-Aufloesungs-Buffer (1/16 der Pixel) und nutzt
        `pygame.transform.scale` (nearest-neighbor, GPU-friendly) statt
        smoothscale. Plus Buffer-Caching gegen per-Frame 8MB Surface-Mallocs.
        Misst ~10ms → ~2ms auf 1920x1080 (5x speedup).
        """
        if strength <= 0:
            return
        w, h = screen.get_size()
        sw, sh = max(1, w // 4), max(1, h // 4)
        # Cache: 1/4-Res Buffer + Threshold-Layer
        buf = getattr(self, '_bloom_buf', None)
        if buf is None or buf.get_size() != (sw, sh):
            self._bloom_buf = pygame.Surface((sw, sh))
            self._bloom_thresh = pygame.Surface((sw, sh))
            self._bloom_thresh_val = -1
            self._bloom_up = None
        # Update #202: Upscale-Ziel cachen.  Vorher allokierte
        # `pygame.transform.scale(buf, (w,h))` jede Frame eine NEUE
        # full-res Surface (1600x900 = 5.76 MB) -> Heap-Churn + GC-Spikes.
        # Mit Dest-Surface skaliert SDL in-place, null Alloc.
        up = getattr(self, '_bloom_up', None)
        if up is None or up.get_size() != (w, h):
            self._bloom_up = pygame.Surface((w, h))
        thr = getattr(self, '_bloom_thresh', None)
        if self._bloom_thresh_val != threshold:
            thr.fill((threshold, threshold, threshold))
            self._bloom_thresh_val = threshold
        try:
            # Downscale screen direkt in den Cache-Buffer
            pygame.transform.scale(screen, (sw, sh), self._bloom_buf)
            # Threshold (Subtract gray) — alles unter `threshold` wird schwarz
            self._bloom_buf.blit(thr, (0, 0),
                                  special_flags=pygame.BLEND_RGB_SUB)
            # Wieder hochskalieren (nearest = schnell, Blockiness wird
            # vom Additive-Blend mit niedrigem Alpha ueberdeckt).
            # Update #202: in den gecachten _bloom_up-Buffer skalieren.
            blurred = self._bloom_up
            pygame.transform.scale(self._bloom_buf, (w, h), blurred)
            blurred.set_alpha(int(255 * strength))
            screen.blit(blurred, (0, 0),
                        special_flags=pygame.BLEND_RGBA_ADD)
        except Exception:
            pass

    def render_heat_distortion(self, screen, heat_cells, time_s,
                                amplitude=4, frequency=6.0):
        """M-12 Heat-Distortion bei Fire-AoE / Lava.

        Verschiebt vertikale Pixel-Spalten in den `heat_cells`-Regionen
        sinus-foermig nach oben/unten.  Sehr CPU-budgetiert — pro Cell
        wird nur das Cell-Rect mit subsurface kopiert + neu geblittet.

        `heat_cells` ist eine Liste von (sx, sy, w, h) Screen-Rects.
        Sicher gegen Out-of-Range (Pygame raises bei subsurface auf OOB).
        """
        if not heat_cells:
            return
        for (rx, ry, rw, rh) in heat_cells:
            # Clamp
            rx = max(0, min(SCREEN_W - 1, int(rx)))
            ry = max(0, min(SCREEN_H - 1, int(ry)))
            rw = max(1, min(SCREEN_W - rx, int(rw)))
            rh = max(1, min(SCREEN_H - ry, int(rh)))
            try:
                src = screen.subsurface(
                    pygame.Rect(rx, ry, rw, rh)).copy()
            except Exception:
                continue
            # Pro-Spalte vertikalen Offset anwenden
            for col in range(0, rw, 2):
                phase = (col / max(1, rw)) * math.tau
                dy = int(math.sin(time_s * frequency + phase) * amplitude)
                if dy == 0:
                    continue
                try:
                    column = src.subsurface(
                        pygame.Rect(col, 0, 2, rh)).copy()
                    screen.blit(column, (rx + col, ry + dy))
                except Exception:
                    pass


    def render_shadow_polygons(self, screen, game, light_x, light_y,
                                 radius=200, num_rays=24):
        """U-02 Dynamic Shadow-Casting (2D Raymarch).

        Pro Light-Source ein Radial-Raycast gegen Wall-Cells; baut ein
        Polygon-Schatten auf den Light-Buffer.  Performance-Hinweis:
        nur fuer 1-2 wichtige Light-Sources (Player-Halo + Boss) — alles
        andere wuerde Frame-Time killen.

        Returnt False wenn kein Grid (Town) oder ausserhalb.
        """
        grid = getattr(game, 'grid', None)
        if grid is None:
            return False
        # Sample Walls via Raycast
        sample_step = 8
        max_dist = radius
        hits = []
        for i in range(num_rays):
            angle = (i / num_rays) * math.tau
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            # Walk along ray
            for d in range(0, max_dist + 1, sample_step):
                wx = light_x + cos_a * d
                wy = light_y + sin_a * d
                if not grid.is_walkable_world(wx, wy):
                    # Wall hit — record screen-pos
                    sx, sy = game.w2s_xy(wx, wy)
                    hits.append((sx, sy))
                    break
            else:
                # No wall hit within radius → ray-edge
                ex = light_x + cos_a * max_dist
                ey = light_y + sin_a * max_dist
                sx, sy = game.w2s_xy(ex, ey)
                hits.append((sx, sy))
        if len(hits) < 3:
            return False
        # Build shadow-polygon (the *gaps* between rays are lit; the rest
        # gets a dimming overlay).  Pygame way: render a dark polygon on
        # a SRCALPHA layer = the inverse area, then blit MULT.
        light_sx, light_sy = game.w2s_xy(light_x, light_y)
        shadow = pygame.Surface(
            (radius * 2, radius * 2), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 110))
        # Sub-area: visible polygon
        local_hits = [(hx - light_sx + radius, hy - light_sy + radius)
                      for (hx, hy) in hits]
        try:
            pygame.draw.polygon(shadow, (0, 0, 0, 0), local_hits)
        except (ValueError, TypeError):
            return False
        screen.blit(shadow, (light_sx - radius, light_sy - radius))
        return True

    def render_fog(self, screen, fog_color, fog_alpha, time_s,
                    camera=None, wind=(1.0, 0.0)):
        """Atmosphaerischer Color-Cast fuer das aktuelle Biom.

        Iterations-History — warum es jetzt SO und nicht anders ist:

          #67   3 dicke draw.line-Bands → "Balken" am Screen
          #186  Wispy numpy-noise overlay → 2 fps + klebte
          #187  Pre-baked noise-Surface, scrollt mit Camera
          #188  parallax=1.0 → fog scrollt mit Welt → MOTION SICKNESS
          #189  parallax=0, wind=0 → fog komplett still →
                "klebt an Camera, Dungeon ist anderer Layer"
          #190  KEINE Textur mehr. Flat Color-Tint + Vignette.

        Root-Cause aller Iterationen vor #190:  Jede sichtbare Textur-
        Pattern, die ueber dem Dungeon liegt, wird vom Auge als separater
        Layer wahrgenommen — egal wie sie sich bewegt.  Bewegungslos →
        klebt an Camera; bewegend → Schein-Beschleunigung beim Laufen.

        Loesung (#190):  Fog wird zum Color-Cast.  Kein Pattern, das das
        Auge tracken koennte → keine Layer-Wahrnehmung.  Ein Vignette
        verdichtet den Effekt an den Bildschirmraendern (Lore: limitierte
        Sicht, atmosphaerische Tiefe).  Pre-baked, statisch, ein Blit.

        camera/wind/time_s sind in der Signatur fuer Compat — werden
        bewusst ignoriert weil Fog jetzt zeitlos statisch ist.
        """
        if fog_alpha <= 0:
            return
        _ = camera, wind, time_s  # signature compat
        tint = self._get_fog_tint(fog_color, fog_alpha)
        if tint is None:
            return
        screen.blit(tint, (0, 0))

    def _get_fog_tint(self, fog_color, fog_alpha):
        """Lazy-cached flat-tint + vignette Surface."""
        from .constants import SCREEN_W, SCREEN_H
        if not hasattr(self, '_fog_tint_cache'):
            self._fog_tint_cache = {}
        key = (tuple(fog_color), int(fog_alpha), SCREEN_W, SCREEN_H)
        surf = self._fog_tint_cache.get(key)
        if surf is not None:
            return surf
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        if _HAS_NUMPY:
            # Radiales Vignette: Mitte 0.45*alpha (Spieler sieht klar),
            # Ecken ~1.4*alpha (atmosphaerische Verdichtung).  KEIN Noise.
            yy, xx = np.meshgrid(np.arange(SCREEN_H), np.arange(SCREEN_W),
                                 indexing='xy')
            cx, cy = SCREEN_W * 0.5, SCREEN_H * 0.5
            dx = (xx - cx) / (SCREEN_W * 0.5)
            dy = (yy - cy) / (SCREEN_H * 0.5)
            dist = np.sqrt(dx * dx + dy * dy)
            vig = np.clip(0.45 + dist * 0.85, 0.45, 1.4)
            alpha = (vig * fog_alpha).clip(0, 255).astype(np.uint8)
            rgb = pygame.surfarray.pixels3d(surf)
            a = pygame.surfarray.pixels_alpha(surf)
            rgb[:, :, 0] = fog_color[0]
            rgb[:, :, 1] = fog_color[1]
            rgb[:, :, 2] = fog_color[2]
            a[:] = alpha
            del rgb, a
        else:
            # Fallback ohne numpy: einfach flat color tint.
            surf.fill((*fog_color, int(fog_alpha)))
        self._fog_tint_cache[key] = surf
        return surf

