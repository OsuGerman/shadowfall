"""Wetter- und Atmosphäre-Effekte: biom-spezifische Partikel + Parallax."""

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


# ============================================================
# CLOUD-SPRITE-GENERATOR (Update #184)
# ============================================================
# Vorher (Update #1..#183): draw_parallax zeichnete eine flache ellipse pro
# Layer — sah aus wie "fliegender Schatten" statt Wolke.  Jetzt: pre-baked
# volumetric clouds via numpy value-noise + vertikalem Gradient.
# Tools-Liste-konform (numpy ist im Stack) — kein neues Dependency.

def _value_noise_2d(w, h, scale, rng):
    """Bilinear-upsampled value-noise, shape (w, h) in [0..1]."""
    if not _HAS_NUMPY:
        return None
    scale = max(2, int(scale))
    gw = max(2, int(w) // scale + 1)
    gh = max(2, int(h) // scale + 1)
    # Random grid in einem RGB-Surface verpacken (pygame braucht 3 Channels
    # fuer make_surface) — wir lesen nur Channel 0.
    grid_rgb = rng.integers(0, 256, size=(gw, gh, 3), dtype=np.uint8)
    src = pygame.surfarray.make_surface(grid_rgb)
    big = pygame.transform.smoothscale(src, (w, h))
    arr = pygame.surfarray.pixels3d(big)[:, :, 0].astype(np.float32) / 255.0
    return arr


def _make_cloud_sprite(size, top_color, bot_color, rng_seed):
    """Erzeugt ein volumetrisches Cloud-Sprite.

    - Radiale Maske (weiche Wolken-Form, nicht hart elliptisch)
    - Mehrere fBm-Octaven Value-Noise fuer flauschige Textur
    - Vertikaler Gradient: hell oben (Sonne), dunkler unten (Schatten)
    - Alpha-Falloff am Rand fuer organische Kanten

    Returns: pygame.Surface (SRCALPHA), Groesse ~(size*2.4, size*1.2).
    """
    if not _HAS_NUMPY:
        return _make_cloud_sprite_fallback(size, top_color, bot_color, rng_seed)
    rng = np.random.default_rng(rng_seed)
    W = max(32, int(size * 2.4))
    H = max(20, int(size * 1.2))

    # Coord-Grid: in pygame surfarray-Konvention shape=(W,H)
    yy, xx = np.meshgrid(np.arange(H), np.arange(W), indexing='xy')
    cx, cy = W * 0.5, H * 0.55  # leicht nach unten, klassische Wolken-Silhouette
    dx = (xx - cx) / (W * 0.5)
    dy = (yy - cy) / (H * 0.45)
    dist = np.sqrt(dx * dx + dy * dy)
    radial = np.clip(1.0 - dist, 0.0, 1.0)
    # Power-Falloff: weicher Rand, kompakter Kern
    radial = radial ** 1.4

    # fBm-Noise (3 Octaven) — perturbiert die Form damit es flauschig wird
    s_int = int(size)
    n1 = _value_noise_2d(W, H, max(8, s_int // 4), rng)
    n2 = _value_noise_2d(W, H, max(4, s_int // 8), rng)
    n3 = _value_noise_2d(W, H, max(2, s_int // 16), rng)
    if n1 is None or n2 is None or n3 is None:
        return _make_cloud_sprite_fallback(size, top_color, bot_color, rng_seed)
    noise = 0.55 * n1 + 0.30 * n2 + 0.15 * n3  # [0..1]

    # Density: radial * (Bias + Noise-Modulation).  Das Noise-Detail
    # zerfranst die Wolken-Form realistisch am Rand.
    density = radial * (0.35 + 0.75 * noise)
    density = np.clip(density, 0.0, 1.0)

    # Soft-Threshold damit der Kern dicht bleibt aber Raender ausfedern
    alpha = np.where(
        density > 0.18,
        np.clip((density - 0.05) * 1.35, 0.0, 1.0) ** 1.1 * 215.0,
        0.0,
    ).astype(np.uint8)

    # Vertikaler Color-Gradient (Sonnenlicht-Effekt)
    t = (yy / max(1, H - 1)).astype(np.float32)
    # Noise leicht ins Lighting mischen — gibt der Wolke Volumen
    light_var = (noise - 0.5) * 0.25
    t = np.clip(t + light_var, 0.0, 1.0)
    R = (top_color[0] * (1 - t) + bot_color[0] * t).astype(np.uint8)
    G = (top_color[1] * (1 - t) + bot_color[1] * t).astype(np.uint8)
    B = (top_color[2] * (1 - t) + bot_color[2] * t).astype(np.uint8)

    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    rgb = pygame.surfarray.pixels3d(surf)
    a = pygame.surfarray.pixels_alpha(surf)
    rgb[:, :, 0] = R
    rgb[:, :, 1] = G
    rgb[:, :, 2] = B
    a[:] = alpha
    del rgb, a  # surfarray locks freigeben
    return surf


def _make_cloud_sprite_fallback(size, top_color, bot_color, rng_seed):
    """Fallback ohne numpy: gestapelte halbtransparente Kreis-Cluster.

    Immer noch besser als eine flache ellipse — bekommt 6 unregelmaessige
    Pluffs uebereinandergelagert mit vertikalem Gradient via per-circle-Tint.
    """
    rng = random.Random(rng_seed)
    W = max(32, int(size * 2.4))
    H = max(20, int(size * 1.2))
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    n_pluffs = 9
    for i in range(n_pluffs):
        # Mehr Pluffs unten/seitlich -> Wolken-Silhouette
        u = rng.uniform(0.15, 0.85)
        v = rng.uniform(0.35, 0.85)
        px = int(u * W)
        py = int(v * H)
        r = int(rng.uniform(size * 0.22, size * 0.42))
        # Top-Bot-Farbmix per pluff
        t = v
        col = (
            int(top_color[0] * (1 - t) + bot_color[0] * t),
            int(top_color[1] * (1 - t) + bot_color[1] * t),
            int(top_color[2] * (1 - t) + bot_color[2] * t),
        )
        a = rng.randint(55, 95)
        pluff = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(pluff, (*col, a), (r, r), r)
        # Weicher Rand: nochmal kleiner Kreis dichter
        pygame.draw.circle(pluff, (*col, min(255, a + 40)),
                            (r, r), int(r * 0.65))
        surf.blit(pluff, (px - r, py - r))
    return surf


class WeatherSystem:
    """Spawnt biom-spezifische Hintergrund-Partikel (Regen/Schnee/Asche/Pollen)."""

    def __init__(self):
        self.particles = []  # list of dicts
        self.parallax = []   # ferne Wolken/Nebel-Schichten
        self.stars = []      # Sterne für Astral-Biom
        self._biome = None
        self._spawn_timer = 0.0
        # PLAN D-05 (Update #102 audit): Wind-Vector pro Biom — wird vom
        # AI-Smell-Sensor genutzt. Default Süd-Wind (0, -1) für alle.
        self.wind_vector = (0.0, -1.0)
        # Update #184: pre-baked cloud sprite cache pro Biom
        self._cloud_sprites = []   # list of pygame.Surface
        # Update #185: Camera-Delta-Tracking fuer korrektes Parallax.
        # Vorher: layer['x'] -= camera.x * speed (absolut!) — Wolken
        # haben sich nur bewegt waehrend der Spieler stand und blieben
        # sonst am Screen kleben.  Jetzt: Delta-basiert.
        self._last_cam_x = None
        self._last_cam_y = None

    # Per-Biome Wind-Vektoren (Lore-konform): Salzkrypta/Marrowport-Westwind
    # vom Meer, Aschenfelder-Nord, Wurzelgrab-still, Glasgolden-leichter
    # Süd, Astral-Wirbel, Desert-Ost.
    _WIND_VECTORS = {
        'crypt':  ( 0.6, -0.2),  # West (Marrowport-Meer-Wind)
        'frost':  ( 0.2, -0.5),  # Nord-Nordwest
        'lava':   ( 0.0, -0.8),  # heißer Aufwind
        'swamp':  ( 0.0, -0.1),  # nahezu still
        'astral': ( 0.4,  0.3),  # spiral-wirbel
        'desert': (-0.7, -0.2),  # Ost-Wind (Wüste)
        'town':   ( 0.3, -0.4),  # mildes Meer-aufdrift
    }

    def set_biome(self, biome):
        if biome == self._biome:
            return
        self._biome = biome
        self.particles.clear()
        self.parallax.clear()
        self.stars.clear()
        self._cloud_sprites = []
        # Update #185: Reset camera-tracking damit der erste Frame nach
        # Biome-Wechsel keinen massiven Delta-Jump produziert (Spieler
        # teleportiert ggf. von Town nach Dungeon — camera springt).
        self._last_cam_x = None
        self._last_cam_y = None
        # Wind-Vector per Biome setzen
        self.wind_vector = self._WIND_VECTORS.get(biome, (0.0, -1.0))
        rng = random.Random(hash(biome) & 0xFFFFFFFF)
        # Update #184: Cloud-Sprites einmalig pro Biom pre-baken.
        # 6 Varianten → jede parallax-Layer waehlt eine zufaellig.
        cloud_pal = _CLOUD_PALETTES.get(biome)
        if cloud_pal is not None:
            n_variants = 6
            for i in range(n_variants):
                sz = rng.uniform(110, 200)
                # Leichte Per-Sprite-Color-Variation
                top_c = tuple(
                    max(0, min(255, c + rng.randint(-10, 10)))
                    for c in cloud_pal['top']
                )
                bot_c = tuple(
                    max(0, min(255, c + rng.randint(-10, 10)))
                    for c in cloud_pal['bot']
                )
                seed = rng.randrange(2 ** 32)
                self._cloud_sprites.append(
                    _make_cloud_sprite(sz, top_c, bot_c, seed)
                )
        # Parallax-Layers (referenzieren ein Sprite ueber sprite_idx)
        for _ in range(8):
            if self._cloud_sprites:
                sprite_idx = rng.randrange(len(self._cloud_sprites))
                base_w = self._cloud_sprites[sprite_idx].get_width()
                # Scale-Variation 0.7..1.3
                scale = rng.uniform(0.7, 1.3)
            else:
                sprite_idx = -1
                base_w = 160
                scale = 1.0
            self.parallax.append({
                'x': rng.uniform(-SCREEN_W, SCREEN_W * 2),
                # Wolken duerfen jetzt ueber den ganzen Bildschirm driften —
                # sie liegen ohnehin als overlay UEBER der Map, also macht es
                # keinen Unterschied ob "oben" oder "unten" — verteilte
                # Verteilung sieht atmosphaerisch besser aus.
                'y': rng.uniform(-30, SCREEN_H - 30),
                # Update #189 (User-Fix "DIE SOLLEN NICHT SCROLLEN"):
                # speed = 0 -> Wolken reagieren GAR NICHT auf Camera.
                # Sie sind ein statischer Screen-Overlay — wie ein Vignette-
                # Effekt, der einfach da ist.  Drift kommt nur sehr langsam
                # vom Wind (siehe update-Methode).
                'speed': 0.0,
                'sprite_idx': sprite_idx,
                'scale': scale,
                # Backward-Compat-Felder (Fallback-Path / Stars-Code):
                'size': base_w * scale * 0.5,
                # Alpha bewusst subtil — sonst dominieren die Wolken den Map-
                # Content und es wirkt wieder wie ueberlagerte Schatten.
                'alpha': rng.randint(55, 95),
            })
        # Sterne (nur für Astral-Biom): über ganzen Bildschirm
        if biome == 'astral':
            for _ in range(180):
                self.stars.append({
                    'x': rng.uniform(0, SCREEN_W),
                    'y': rng.uniform(0, SCREEN_H),
                    'size': rng.choice([1, 1, 1, 2, 2, 3]),
                    'twinkle': rng.uniform(0, math.tau),
                    'speed': rng.uniform(0.02, 0.10),
                })

    def update(self, dt, camera, ambient_density=1.0):
        cfg = _WEATHER_CONFIG.get(self._biome)
        if cfg is None:
            self.particles.clear()
            return

        # Wetter ist AMBIENT — Spawn-Rate skaliert mit Settings-Slider +
        # Dynamic-Culling (C-02/C-03). Bei density=0 keine neuen Particles.
        if ambient_density <= 0.01:
            effective_rate = 0.0
        else:
            effective_rate = cfg['rate'] * ambient_density

        # Spawn neue Partikel
        self._spawn_timer -= dt
        if effective_rate > 0 and self._spawn_timer <= 0:
            self._spawn_timer = 1.0 / effective_rate
            self.particles.append({
                'x': random.uniform(0, SCREEN_W),
                'y': -10,
                'vx': cfg['wind'] + random.uniform(-10, 10),
                'vy': cfg['fall_speed'] + random.uniform(-20, 20),
                'kind': cfg['kind'],
                'size': random.uniform(*cfg['size_range']),
                'rot': random.uniform(0, math.tau),
                'rot_v': random.uniform(-2, 2),
                'life': random.uniform(2.0, 5.0),
                'age': 0.0,
            })

        for p in self.particles[:]:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['rot'] += p['rot_v'] * dt
            p['age'] += dt
            if p['y'] > SCREEN_H + 20 or p['age'] > p['life']:
                self.particles.remove(p)

        # Parallax-Wolken bewegen (Update #185: korrekt via Camera-Delta).
        # Vorher: layer['x'] -= camera.x * speed * 0.01 — wertete die
        # ABSOLUTE Camera-Position jeden Frame aus, dadurch klebten die
        # Wolken am Screen statt durch die Welt zu driften.  Jetzt:
        # Camera-Delta * fraktionaler Speed = ferne Wolken die der Spieler
        # langsam "ueberholt".
        cam_x = float(getattr(camera, 'x', 0.0))
        cam_y = float(getattr(camera, 'y', 0.0))
        if self._last_cam_x is None:
            self._last_cam_x = cam_x
            self._last_cam_y = cam_y
        dcx = cam_x - self._last_cam_x
        dcy = cam_y - self._last_cam_y
        self._last_cam_x = cam_x
        self._last_cam_y = cam_y
        # Sanity-Clamp: bei Teleport / Akt-Wechsel kann der Delta riesig
        # sein und alle Wolken auf einmal off-screen jagen.
        if abs(dcx) > SCREEN_W or abs(dcy) > SCREEN_H:
            dcx = 0.0
            dcy = 0.0
        wind_dx = self.wind_vector[0]
        wind_dy = self.wind_vector[1]
        for layer in self.parallax:
            sp = layer['speed']
            # Update #189: sp = 0 -> Wolken ignorieren Camera komplett.
            # Statischer Screen-Overlay.  Wenn sp doch != 0 gesetzt wird
            # (z.B. zukuenftige Town-Maps mit echtem Himmel), bleibt die
            # alte Formel verfuegbar.
            if sp > 0:
                layer['x'] -= dcx * sp
                layer['y'] -= dcy * sp
            # Wind-Drift: sehr langsam — gerade noch wahrnehmbar wenn man
            # eine Weile hinschaut, aber nicht ablenkend.
            layer['x'] += wind_dx * dt * 3.0
            layer['y'] += wind_dy * dt * 1.0
            # Wrap (Sprites groesser als alte ellipsen → weitere Margin)
            if layer['x'] < -360:
                layer['x'] = SCREEN_W + 200
            elif layer['x'] > SCREEN_W + 360:
                layer['x'] = -200
            if layer['y'] < -240:
                layer['y'] = SCREEN_H + 120
            elif layer['y'] > SCREEN_H + 240:
                layer['y'] = -120

    def draw_parallax(self, screen, ambient):
        """Hintergrund-Schichten (Wolken/Nebel/Sterne) — ZUERST gezeichnet."""
        cfg = _WEATHER_CONFIG.get(self._biome)
        # Sterne für Astral (vor Wolken-Schichten)
        if self.stars:
            for s in self.stars:
                tw = (math.sin(s['twinkle'] + pygame.time.get_ticks() * 0.002) + 1) * 0.5
                a = int(120 + 130 * tw)
                pygame.draw.circle(screen, (240, 220, 255, a),
                                    (int(s['x']), int(s['y'])), s['size'])
                if s['size'] >= 2:
                    # Glow um große Sterne
                    glow = pygame.Surface((10, 10), pygame.SRCALPHA)
                    pygame.draw.circle(glow, (200, 160, 255, a // 4),
                                        (5, 5), 5)
                    screen.blit(glow, (int(s['x']) - 5, int(s['y']) - 5))
        # Update #184: volumetric clouds — pre-baked sprites statt flacher
        # ellipsen.  Astral hat keine Wolken (Sterne uebernehmen).
        if not self._cloud_sprites:
            return
        for layer in self.parallax:
            idx = layer.get('sprite_idx', -1)
            if idx < 0 or idx >= len(self._cloud_sprites):
                continue
            sprite = self._cloud_sprites[idx]
            scale = layer.get('scale', 1.0)
            if abs(scale - 1.0) > 0.02:
                w = max(1, int(sprite.get_width() * scale))
                h = max(1, int(sprite.get_height() * scale))
                spr = pygame.transform.smoothscale(sprite, (w, h))
            else:
                spr = sprite
                w, h = sprite.get_width(), sprite.get_height()
            # alpha aus Layer (atmosphaerische Tiefe) — pro Layer leicht
            # ausblendbar, da der ambient-Slider ueber draw-call-Pfade lebt.
            base_alpha = int(layer.get('alpha', 200))
            spr.set_alpha(base_alpha)
            screen.blit(spr, (int(layer['x'] - w * 0.5),
                                int(layer['y'])))

    def draw_particles(self, screen):
        """Wetter-Partikel — über allem zeichnen (foreground)."""
        for p in self.particles:
            sx, sy = int(p['x']), int(p['y'])
            kind = p['kind']
            if kind == 'rain':
                # Regen: schräge Linie
                pygame.draw.line(screen, (140, 160, 180),
                                 (sx, sy), (sx - 2, sy + int(p['size'])), 1)
            elif kind == 'snow':
                # Schnee: weißer Kreis
                pygame.draw.circle(screen, (240, 250, 255),
                                   (sx, sy), int(p['size'] * 0.2))
            elif kind == 'ash':
                # Asche: glühender Punkt
                pygame.draw.circle(screen, (255, 140, 60),
                                   (sx, sy), int(p['size'] * 0.15))
                pygame.draw.circle(screen, (200, 60, 30),
                                   (sx, sy), int(p['size'] * 0.25), 1)
            elif kind == 'pollen':
                # Pollen: gelblicher Schimmer
                pygame.draw.circle(screen, (220, 200, 120),
                                   (sx, sy), int(p['size'] * 0.18))
            elif kind == 'dust':
                # Staub: bräunlicher Punkt
                pygame.draw.circle(screen, (160, 140, 100),
                                   (sx, sy), int(p['size'] * 0.2))
            elif kind == 'sand':
                # Sand: helle Linie schräg
                pygame.draw.line(screen, (220, 200, 140),
                                 (sx, sy), (sx + 4, sy + 1), 1)
            elif kind == 'spore':
                # Spore: grünlicher Schimmer
                pygame.draw.circle(screen, (140, 220, 140),
                                   (sx, sy), int(p['size'] * 0.2))
            elif kind == 'stardust':
                # Sternenstaub: weißer Punkt + violetter Glow
                pygame.draw.circle(screen, (200, 160, 255),
                                   (sx, sy), int(p['size'] * 0.3))
                pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 1)


_CLOUD_PALETTES = {
    # Lore-treue Wolkenfarben fuer top-down overlay-clouds.
    # Top-Down-Sicht: die Wolken werden UEBER den Boden geblittet, also
    # muessen sie hell-tonig sein damit sie als "lichter Wolken-Haze" lesbar
    # bleiben und nicht den Map-Content abdunkeln (wuerde wieder wie
    # Schatten wirken — siehe User-Feedback Update #184).
    # top/bot Gradient = subtile Tonvariation, beide Werte hell-saturiert.
    'crypt':  dict(top=(210, 200, 180), bot=(165, 150, 125)),  # staubig hell
    'frost':  dict(top=(240, 245, 252), bot=(200, 215, 235)),  # eis-weiss
    'lava':   dict(top=(245, 195, 130), bot=(200, 130,  80)),  # warm glow
    'town':   dict(top=(252, 248, 238), bot=(220, 215, 200)),  # sonnig weiss
    'desert': dict(top=(245, 225, 175), bot=(215, 185, 130)),  # warm sand
    'swamp':  dict(top=(195, 210, 180), bot=(140, 165, 130)),  # blass-gruen
    # Astral hat keine Wolken — Sterne uebernehmen.
}


_WEATHER_CONFIG = {
    'crypt': dict(
        kind='dust', rate=8, fall_speed=20, wind=10,
        size_range=(8, 14),
        parallax_color=(60, 50, 40),
    ),
    'frost': dict(
        kind='snow', rate=25, fall_speed=80, wind=-15,
        size_range=(8, 18),
        parallax_color=(160, 180, 220),
    ),
    'lava': dict(
        kind='ash', rate=15, fall_speed=40, wind=20,
        size_range=(8, 14),
        parallax_color=(120, 50, 30),
    ),
    'town': dict(
        kind='pollen', rate=5, fall_speed=25, wind=15,
        size_range=(8, 12),
        parallax_color=(180, 160, 110),
    ),
    'desert': dict(
        kind='sand', rate=30, fall_speed=60, wind=80,
        size_range=(6, 12),
        parallax_color=(200, 170, 110),
    ),
    'swamp': dict(
        kind='spore', rate=10, fall_speed=15, wind=5,
        size_range=(8, 14),
        parallax_color=(80, 100, 70),
    ),
    'astral': dict(
        kind='stardust', rate=20, fall_speed=10, wind=0,
        size_range=(4, 10),
        parallax_color=(120, 60, 180),
    ),
}


# ============================================================
# TAG/NACHT-ZYKLUS (in Town)
# ============================================================
def day_night_ambient(time_seconds):
    """Returnt (ambient_r, ambient_g, ambient_b) für Tag/Nacht-Zyklus.

    Zykluslänge: 60 Sekunden Spielzeit = 1 Tag.
    """
    t = (time_seconds % 60.0) / 60.0  # 0.0-1.0
    # Phasen:
    #   0.0-0.15  Morgenrot (warm)
    #   0.15-0.40 Tag (hell)
    #   0.40-0.55 Sonnenuntergang (warm-orange)
    #   0.55-0.80 Nacht (dunkel-blau)
    #   0.80-1.00 Morgendämmerung (kühl-grau)
    if t < 0.15:
        # Morgenrot
        f = t / 0.15
        r = int(50 + 30 * f)
        g = int(30 + 30 * f)
        b = int(20 + 30 * f)
    elif t < 0.40:
        # Tag
        r, g, b = 30, 30, 30  # sehr helles ambient (= wenig darken)
    elif t < 0.55:
        f = (t - 0.40) / 0.15
        r = int(30 + 80 * f)
        g = int(30 + 30 * f)
        b = int(30)
    elif t < 0.80:
        # Nacht (dunkelblau)
        r, g, b = 8, 10, 25
    else:
        # Dämmerung
        f = (t - 0.80) / 0.20
        r = int(8 + 22 * f)
        g = int(10 + 20 * f)
        b = int(25 + 5 * f)
    return (r, g, b)


def is_day_phase(time_seconds):
    """W-11 (Update #48): Boolean Tag/Nacht für NPC-Schedules.

    Day-Phase = 0.0–0.55 (Morgenrot + Tag + früher Abend).
    Night-Phase = 0.55–1.0 (Nacht + Dämmerung).
    """
    t = (time_seconds % 60.0) / 60.0
    return t < 0.55


def day_night_ambient_alpha(time_seconds):
    """Alpha für Darkness-Overlay je nach Tageszeit. Tag = dünn, Nacht = dick."""
    t = (time_seconds % 60.0) / 60.0
    if 0.15 <= t < 0.40:
        return 30   # Tag: sehr hell
    if t < 0.15:
        return int(30 + 50 * (1 - t / 0.15))  # Morgenrot
    if t < 0.55:
        return int(30 + 90 * ((t - 0.40) / 0.15))  # Abend
    if t < 0.80:
        return 180  # Nacht
    return int(180 - 100 * ((t - 0.80) / 0.20))


def town_color_grading(time_seconds):
    """Update #138 (M-21): Dynamic Day/Night Color-Grading.

    Returnt eine (tint_color, blend_mode)-Tupel.  tint_color ist ein
    multiplikativer RGB-Tint der via `pygame.BLEND_RGB_MULT` auf den
    finalen Render-Output angewandt wird — Morgen warm, Mittag neutral,
    Abend rosé, Nacht kalt-blau.

    Multiplikatoren werden als 0..255-Werte zurückgegeben, wobei
    255 = unverändert, < 255 = darken/tönen.  Verschiedene Channels
    geben den Color-Cast (Morgen = R erhöht, B leicht reduziert).

    Lore-Anker: Brassweir-Hafenstadt verändert sich subtil über den
    Tag — die Salzpfützen reflektieren morgens warm-bronze, abends
    violett-rosé.
    """
    t = (time_seconds % 60.0) / 60.0
    if t < 0.15:
        # Morgenrot — warm: R+15%, G+5%, B-5%
        f = t / 0.15
        return (
            min(255, int(255 + 35 * (1 - f) * 0.0)),    # neutral als Mult
            255 if f > 0.5 else int(245 + 10 * f),       # leicht G-warm
            int(225 + 20 * f),                            # B leicht gedämpft
        )
    elif t < 0.40:
        # Tag — neutral (alle 255)
        return (255, 255, 255)
    elif t < 0.55:
        # Sonnenuntergang — rosé/orange: R neutral, G leicht runter, B runter
        f = (t - 0.40) / 0.15
        return (
            255,
            int(245 - 25 * f),
            int(225 - 50 * f),
        )
    elif t < 0.80:
        # Nacht — kalt-blau: R 80%, G 85%, B 100%
        return (200, 215, 255)
    else:
        # Dämmerung — graduell zurück
        f = (t - 0.80) / 0.20
        return (
            int(200 + 55 * f),
            int(215 + 40 * f),
            255,
        )


# ============================================================
# BLUT-PFÜTZEN (persistent am Boden)
# ============================================================
class BloodPool:
    """Update #136 (V-05): Blood-Pool-Persistence mit Lore-Farben.

    Persistente Blut-Pfütze am Todesort, trocknet über `life`-Sekunden
    aus.  `color` ist jetzt optional — wenn None, wird ein Default-Rot
    gewürfelt (Backward-Compat).  Mob-spezifische Farben kommen aus
    combat._BLOOD_COLORS (Salzgeist silbrig, Glaslord glas-splitter etc.).
    `kind` markiert Spezial-Decals ('salt_crystal' für Salzgeist statt
    Blut).
    """
    __slots__ = ('x', 'y', 'size', 'age', 'life', 'color', 'kind')

    def __init__(self, x, y, size, color=None, life=15.0,
                 kind='blood'):
        self.x = x
        self.y = y
        self.size = size
        self.age = 0.0
        self.life = float(life)
        if color is None:
            # Update #182 (User-Fix „random Schatten ueberall"):
            # Default-Color war zu dunkel (80-130, 15-30, 15-30) -> sah
            # wie zufaellige Schatten-Ellipsen statt Blut aus.  Jetzt
            # klar rot-saturiert (160-200, 30-50, 30-50) damit der
            # Spieler es sofort als Blut erkennt.
            self.color = (random.randint(160, 200),
                          random.randint(30, 50),
                          random.randint(30, 50))
        else:
            self.color = tuple(int(c) for c in color[:3])
        self.kind = kind   # 'blood' | 'salt_crystal' | 'ash' | 'sap'

    def alpha(self):
        # Update #182: Base-Alpha 180 -> 150 (weniger dominant am Boden).
        # Letzten 33 % ausblenden — "trocknet"-Look.
        fade_start = self.life * 0.67
        if self.age < fade_start:
            return 150
        fade_dur = max(0.001, self.life - fade_start)
        return int(150 * max(0, 1.0 - (self.age - fade_start) / fade_dur))


def draw_blood_pool(screen, pool, sx, sy):
    a = pool.alpha()
    if a <= 0:
        return
    kind = getattr(pool, 'kind', 'blood')
    if kind == 'salt_crystal':
        # Update #136 (V-05): Salzgeist hinterlässt kleine Salzkristalle
        # statt einer Blut-Pfütze.  Lore: Bestiarium-Realismus.
        s = pygame.Surface((int(pool.size) * 2, int(pool.size) * 2),
                            pygame.SRCALPHA)
        cx = int(pool.size)
        # 5 Kristall-Splitter als kleine Diamonds
        for k in range(5):
            ang = k * 1.25
            r = pool.size * 0.7
            ox = int(math.cos(ang) * r)
            oy = int(math.sin(ang) * r * 0.5)
            pts = [(cx + ox,     cx + oy - 3),
                   (cx + ox + 3, cx + oy),
                   (cx + ox,     cx + oy + 3),
                   (cx + ox - 3, cx + oy)]
            pygame.draw.polygon(s, (*pool.color, a), pts)
            pygame.draw.polygon(s, (255, 255, 255, a // 2), pts, 1)
        screen.blit(s, (sx - cx, sy - cx))
        return
    if kind == 'ash':
        # Update #183 (User-Fix „komische graue Kreise nach Kill"):
        # Aschenbrut hinterliess einen generischen dunkel-grauen
        # Ellipsen-Pool ueber den Default-Branch — sah aus wie
        # zufaellige schwebende Schatten.  Jetzt: kleine Asche-Spur
        # mit verstreuten Glut-Punkten statt einer flaechigen Ellipse.
        size = max(6, int(pool.size * 0.7))
        s = pygame.Surface((size * 2 + 8, size + 6), pygame.SRCALPHA)
        cx = size + 4
        cy = (size + 6) // 2
        # Streifige Asche statt voller Ellipse
        for k in range(4):
            offset_y = cy + (k - 2) * 2
            stripe_w = int(size * (0.85 - k * 0.12))
            pygame.draw.line(
                s, (*pool.color, max(0, a - 30)),
                (cx - stripe_w, offset_y),
                (cx + stripe_w, offset_y), 2)
        # Glut-Funken (warm-orange) verteilt — Aschenbrut-Lore-Akzent
        ember_col = (200, 120, 50)
        rng = math.sin(pool.x * 0.13 + pool.y * 0.09)
        for k in range(5):
            ang = k * 1.25 + rng
            r = size * (0.3 + 0.5 * (k % 3) / 3)
            ox = int(math.cos(ang) * r)
            oy = int(math.sin(ang) * r * 0.45)
            pygame.draw.circle(s, (*ember_col, max(0, a - 60)),
                                (cx + ox, cy + oy), 1)
        screen.blit(s, (sx - cx, sy - cy))
        return
    if kind == 'sap':
        # Update #183: Wurzelhueter hinterliess einen generischen
        # grauen Pool — jetzt kleine gruene Saft-Pfuetze mit Blatt-
        # Bits, lesbar als Pflanzen-Sap statt als Schatten-Oval.
        size = max(8, int(pool.size * 0.85))
        sz_w_sap = size * 2
        sz_h_sap = size
        s = pygame.Surface((sz_w_sap, sz_h_sap), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (*pool.color, a),
                             (0, 0, sz_w_sap, sz_h_sap))
        inner_col_sap = (min(255, pool.color[0] + 60),
                          min(255, pool.color[1] + 70),
                          min(255, pool.color[2] + 40))
        inner_w_sap = int(sz_w_sap * 0.55)
        inner_h_sap = int(sz_h_sap * 0.5)
        pygame.draw.ellipse(s, (*inner_col_sap, max(0, a - 30)),
                             (int(sz_w_sap * 0.18), int(sz_h_sap * 0.2),
                              inner_w_sap, inner_h_sap))
        leaf_col = (40, 80, 30)
        for k in range(2):
            ang = (k * 1.7) + math.sin(pool.x * 0.07)
            lx = int(size + math.cos(ang) * size * 0.7)
            ly = int(size // 2 + math.sin(ang) * size * 0.3)
            pygame.draw.circle(s, (*leaf_col, a), (lx, ly), 2)
            pygame.draw.line(s, (*leaf_col, a),
                              (lx, ly), (lx + 2, ly + 2), 1)
        screen.blit(s, (sx - size, sy - size // 2))
        return
    # Default Blood-Pool
    # Update #182 (User-Fix „random Schatten"): Inner-Highlight macht die
    # Pfuetze als nasse Fluessigkeit lesbar statt als flachen Schatten.
    sz_w = int(pool.size) * 2
    sz_h = int(pool.size)
    s = pygame.Surface((sz_w, sz_h), pygame.SRCALPHA)
    # Aeussere Pool-Form (dunkler Rand)
    pygame.draw.ellipse(s, (*pool.color, a), (0, 0, sz_w, sz_h))
    # Innerer Glossy-Highlight — heller-roter Kern, kleiner als die Pool-Form,
    # schraeg nach oben-links versetzt (simuliert Lichtreflex).
    inner_col = (min(255, pool.color[0] + 40),
                  min(255, pool.color[1] + 20),
                  min(255, pool.color[2] + 20))
    inner_w = int(sz_w * 0.55)
    inner_h = int(sz_h * 0.5)
    inner_x = int(sz_w * 0.18)
    inner_y = int(sz_h * 0.2)
    pygame.draw.ellipse(s, (*inner_col, max(0, a - 40)),
                        (inner_x, inner_y, inner_w, inner_h))
    # Mini-Glanzpunkt (sehr klein, fast weiss-rot)
    glint_col = (min(255, pool.color[0] + 80),
                  min(255, pool.color[1] + 60),
                  min(255, pool.color[2] + 60))
    pygame.draw.ellipse(s, (*glint_col, max(0, a - 80)),
                        (inner_x + int(inner_w * 0.15),
                         inner_y + int(inner_h * 0.1),
                         max(2, int(inner_w * 0.25)),
                         max(2, int(inner_h * 0.3))))
    # Splatter (kleine Tropfen drumherum)
    for k in range(3):
        ang = k * 2.094
        ox = math.cos(ang) * pool.size * 0.8
        oy = math.sin(ang) * pool.size * 0.4
        pygame.draw.circle(s, (*pool.color, a),
                           (int(pool.size + ox), int(pool.size * 0.5 + oy)), 2)
    screen.blit(s, (sx - int(pool.size), sy - int(pool.size * 0.5)))
