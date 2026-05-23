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
        """Sammelt Standard-Lichter aus Game-Zustand."""
        # Spieler-Licht
        p = game.player
        psx, psy = game.w2s(p.pos)
        spec = sprites_mod.light_for_player(p)
        if spec:
            r, col, intens = spec
            self.add(psx, psy - p.height // 2, r, col, intens, flicker=4)

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
                sx, sy = game.w2s_xy(t.x, t.y)
                self.add(sx, sy, 60, (255, 130, 50), 0.4, flicker=3)
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
