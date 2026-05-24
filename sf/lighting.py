"""Dynamisches Licht-System.

Verwendet eine dunkle Overlay-Surface, in die Licht-Quellen ihre radialen
Gradienten subtrahieren (BLEND_RGBA_SUB). Das Ergebnis wird auf das
fertige Frame geblittet.
"""

import math
import random
import pygame

from .constants import SCREEN_W, SCREEN_H
from . import sprites as sprites_mod


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

        # Fackeln (aus tiles)
        for t in game.tiles:
            if t.kind == 'torch':
                sx, sy = game.w2s_xy(t.x, t.y)
                self.add(sx, sy - 6, 160, (255, 170, 80), 0.8, flicker=6)
            elif t.kind == 'lantern':
                sx, sy = game.w2s_xy(t.x, t.y)
                self.add(sx, sy - 8, 200, (255, 200, 110), 0.9, flicker=4)
            elif t.kind == 'ember' or t.kind == 'lava_pool':
                # U-06: Lava-Glow staerker + atmender Pulse
                sx, sy = game.w2s_xy(t.x, t.y)
                t_pulse = (pygame.time.get_ticks() % 2000) / 2000.0
                pulse_r = int(60 + 8 * math.sin(t_pulse * math.tau))
                self.add(sx, sy, pulse_r, (255, 130, 50), 0.55, flicker=3)
            elif t.kind == 'crystal':
                # U-06: Crystal-Glow in Biome-Akzent-Farbe.
                sx, sy = game.w2s_xy(t.x, t.y)
                col_map = {'crypt':  (180, 200, 240),
                           'frost':  (160, 220, 255),
                           'astral': (220, 140, 255),
                           'swamp':  (140, 220, 160)}
                col = col_map.get(getattr(game, 'biome', 'crypt'),
                                  (180, 200, 240))
                self.add(sx, sy, 70, col, 0.45, flicker=2)
            elif t.kind == 'rune':
                sx, sy = game.w2s_xy(t.x, t.y)
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
        flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha))
        screen.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def render_bloom(self, screen, threshold=180, strength=0.55):
        """M-10 Bloom / Glow-Pass (Surface-Approximation).

        Extrahiert helle Pixel ueber `threshold`, blurt sie via
        Down-Up-Scale-Pass und blittet additiv zurueck.  Pygame ohne
        echte Shader — Bloom hier ist 2-Pass smoothscale.

        Settings-Toggle: `settings['bloom']` ∈ {off, low, high}.
        """
        if strength <= 0:
            return
        # Capture current screen
        try:
            captured = screen.copy()
        except Exception:
            return
        # Threshold-Mask: dunkle Pixel rausziehen
        # Approximation via Subtract eines grauen Layers (so dass nur
        # Hell-Pixel uebrigbleiben).
        thresh_layer = pygame.Surface(captured.get_size())
        thresh_layer.fill((threshold, threshold, threshold))
        bright = captured.copy()
        bright.blit(thresh_layer, (0, 0),
                    special_flags=pygame.BLEND_RGB_SUB)
        # Blur via 4× downscale + 4× upscale
        try:
            w, h = bright.get_size()
            small = pygame.transform.smoothscale(
                bright, (max(1, w // 6), max(1, h // 6)))
            blurred = pygame.transform.smoothscale(small, (w, h))
            # Strength: alpha-multiplikator
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

    def render_fog(self, screen, fog_color, fog_alpha, time_s):
        """M-05 (Update #67): Volumetric-Fog-Overlay.

        Animated horizontal fog-bands die langsam driften.  Wird ÜBER der
        Welt aber UNTER der HUD gerendert.  `fog_alpha` 0-255 = Dichte;
        `fog_color` z. B. (140, 150, 170) für Crypt-Nebel.
        """
        if fog_alpha <= 0:
            return
        from .constants import SCREEN_W, SCREEN_H
        layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        # 3 horizontale Bands mit unterschiedlichen Drift-Geschwindigkeiten
        for k, (band_y, speed, ph, height, alpha_mult) in enumerate([
            (SCREEN_H * 0.25, 12.0, 0.0, 60, 0.55),
            (SCREEN_H * 0.50, 18.0, 1.7, 80, 0.85),
            (SCREEN_H * 0.75, 9.0,  3.4, 70, 0.65),
        ]):
            band_a = int(fog_alpha * alpha_mult)
            # Sinus-Drift: Höhe wackelt um ±height/2 zentriert auf band_y
            mid = band_y + math.sin(time_s * 0.4 + ph) * height * 0.2
            top = int(mid - height // 2)
            for y_off in range(height):
                ny = y_off / max(1, height - 1)
                # Vertikal Soft-Fade (mehr Alpha in der Mitte)
                fade = 1.0 - abs(ny - 0.5) * 2.0
                alpha = int(band_a * fade)
                if alpha <= 0:
                    continue
                # Horizontaler Drift via Slice-Offset (gibt das „flow"-Feel)
                x_offset = int(math.sin(time_s * 0.2 + ph + ny * 0.5)
                                * speed * 4)
                pygame.draw.line(layer, (*fog_color, alpha),
                                  (x_offset, top + y_off),
                                  (SCREEN_W + x_offset, top + y_off))
        screen.blit(layer, (0, 0))
