"""Wetter- und Atmosphäre-Effekte: biom-spezifische Partikel + Parallax."""

import math
import random
import pygame

from .constants import SCREEN_W, SCREEN_H


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
        # Wind-Vector per Biome setzen
        self.wind_vector = self._WIND_VECTORS.get(biome, (0.0, -1.0))
        rng = random.Random(hash(biome) & 0xFFFFFFFF)
        for _ in range(8):
            self.parallax.append({
                'x': rng.uniform(-SCREEN_W, SCREEN_W * 2),
                'y': rng.uniform(0, SCREEN_H * 0.6),
                'speed': rng.uniform(0.08, 0.18),
                'size': rng.uniform(80, 180),
                'alpha': rng.randint(20, 50),
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

        # Parallax-Wolken bewegen (relativ zur Kamera)
        for layer in self.parallax:
            layer['x'] -= camera.x * layer['speed'] * 0.01
            # Falls außerhalb Sicht → wrap
            if layer['x'] < -200:
                layer['x'] = SCREEN_W + 100
            elif layer['x'] > SCREEN_W + 100:
                layer['x'] = -200

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
        if cfg is None or 'parallax_color' not in cfg:
            return
        color = cfg['parallax_color']
        for layer in self.parallax:
            surf = pygame.Surface((int(layer['size']) * 2,
                                    int(layer['size']) * 0.4),
                                   pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (*color, layer['alpha']),
                                (0, 0, int(layer['size']) * 2,
                                 int(layer['size']) * 0.4))
            screen.blit(surf, (layer['x'] - layer['size'],
                                layer['y']))

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
            self.color = (random.randint(80, 130),
                          random.randint(15, 30),
                          random.randint(15, 30))
        else:
            self.color = tuple(int(c) for c in color[:3])
        self.kind = kind   # 'blood' | 'salt_crystal' | 'ash' | 'sap'

    def alpha(self):
        # Letzten 33 % ausblenden (statt nur letzte 5 s) — "trocknet"-Look
        fade_start = self.life * 0.67
        if self.age < fade_start:
            return 180
        fade_dur = max(0.001, self.life - fade_start)
        return int(180 * max(0, 1.0 - (self.age - fade_start) / fade_dur))


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
    # Default Blood-Pool
    s = pygame.Surface((int(pool.size) * 2, int(pool.size)), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (*pool.color, a),
                        (0, 0, int(pool.size) * 2, int(pool.size)))
    # Splatter (kleine Tropfen drumherum)
    for k in range(3):
        ang = k * 2.094
        ox = math.cos(ang) * pool.size * 0.8
        oy = math.sin(ang) * pool.size * 0.4
        pygame.draw.circle(s, (*pool.color, a),
                           (int(pool.size + ox), int(pool.size * 0.5 + oy)), 2)
    screen.blit(s, (sx - int(pool.size), sy - int(pool.size * 0.5)))
