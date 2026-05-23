"""Biome, Boden-Texturen, Decor-Generierung, Portale, Mini-Map."""

import math
import random
import pygame

from .constants import SCREEN_W, SCREEN_H, GOLD, GOLD_BRIGHT, WHITE, BLACK, FIRE, FROST
from .entities import Decor


# ============================================================
# BIOM-DEFINITIONEN
# ============================================================
BIOMES = {
    'crypt': dict(
        name='Krypta',
        bg=(18, 14, 10),
        ground=(58, 48, 36),
        ground_alt=(82, 68, 50),
        crack=(26, 18, 10),
        decor_kinds=['stone', 'skull', 'bone', 'rune', 'pillar', 'torch', 'sarcophagus'],
        big_decor=['pillar', 'sarcophagus', 'broken_wall', 'torch'],
        small_decor=['skull', 'bone', 'rune', 'stone'],
        accent=(180, 140, 90),
    ),
    'frost': dict(
        name='Eisfeld',
        bg=(14, 22, 36),
        ground=(54, 78, 116),
        ground_alt=(78, 110, 156),
        crack=(220, 235, 255),
        decor_kinds=['rock', 'bone', 'ice', 'rune', 'ice_spike', 'frozen_pillar'],
        big_decor=['frozen_pillar', 'ice_spike'],
        small_decor=['ice', 'bone', 'rock', 'rune'],
        accent=(180, 220, 255),
    ),
    'lava': dict(
        name='Lavakammer',
        bg=(28, 12, 8),
        ground=(96, 44, 24),
        ground_alt=(142, 64, 30),
        crack=(255, 160, 60),
        decor_kinds=['stone', 'skull', 'rock', 'ember', 'lava_pool', 'pillar'],
        big_decor=['lava_pool', 'pillar', 'broken_wall'],
        small_decor=['ember', 'skull', 'stone', 'rock'],
        accent=(255, 150, 70),
    ),
    'town': dict(
        name='Heimstatt',
        bg=(32, 28, 22),
        ground=(120, 102, 78),
        ground_alt=(160, 138, 100),
        crack=(80, 64, 44),
        decor_kinds=['stone', 'rune', 'torch', 'pillar', 'lantern'],
        big_decor=['pillar', 'torch', 'lantern'],
        small_decor=['stone', 'rune'],
        accent=(220, 180, 110),
    ),
    'desert': dict(
        name='Wüste',
        bg=(46, 30, 12),
        ground=(190, 150, 85),
        ground_alt=(220, 180, 110),
        crack=(110, 80, 40),
        decor_kinds=['stone', 'rock', 'rune', 'pillar'],
        big_decor=['pillar', 'broken_wall', 'sarcophagus'],
        small_decor=['stone', 'rock', 'bone'],
        accent=(240, 200, 100),
    ),
    'swamp': dict(
        name='Sumpf',
        bg=(14, 22, 14),
        ground=(46, 68, 40),
        ground_alt=(68, 96, 56),
        crack=(20, 36, 22),
        decor_kinds=['stone', 'bone', 'rune', 'pillar', 'mushroom'],
        big_decor=['pillar', 'broken_wall', 'mushroom'],
        small_decor=['bone', 'rune', 'stone', 'mushroom'],
        accent=(120, 200, 120),
    ),
    'astral': dict(
        name='Astral-Ebene',
        bg=(8, 4, 22),
        ground=(40, 30, 80),
        ground_alt=(70, 50, 130),
        crack=(180, 140, 240),
        decor_kinds=['stone', 'rune', 'crystal', 'pillar'],
        big_decor=['pillar', 'crystal'],
        small_decor=['rune', 'crystal', 'stone'],
        accent=(200, 160, 255),
    ),
}


# ============================================================
# BODEN-TEXTUREN (Tile-Pattern, gecacht)
# ============================================================
TILE_SIZE = 128
_tile_cache = {}
# ROADMAP T2.2: Cache fuer pro-Cell-skalierte AI-Tiles (biome, cell_size).
_dungeon_cell_cache = {}


def reload_tile_cache() -> None:
    """Hot-Reload-Helper: Tile-Caches leeren. Beim naechsten Render werden
    AI-Tiles + Procedural-Tiles neu aufgebaut. Praktisch wenn man via
    tools/sprite_gen.py re-generiert waehrend das Game laeuft (F5-Debug)."""
    _tile_cache.clear()
    _dungeon_cell_cache.clear()


def _get_ai_tile(biome) -> pygame.Surface | None:
    """ROADMAP T2.2: Liefert AI-generierte Biome-Tile-Surface (skaliert auf
    TILE_SIZE) wenn assets/sprites/tiles/<biome>.png existiert. Sonst None
    → Procedural-Fallback in _make_tile()."""
    try:
        from . import sprites as _spr
    except ImportError:
        return None
    src = _spr.get_tile_sprite(biome)
    if src is None:
        return None
    # AI-Tile ist 512×512 Painterly-Texture. Wir skalieren auf TILE_SIZE
    # und nutzen es als Pattern-Repeat.
    if src.get_size() != (TILE_SIZE, TILE_SIZE):
        try:
            src = pygame.transform.smoothscale(src, (TILE_SIZE, TILE_SIZE))
        except Exception:
            return None
    return src


def _make_tile(biome):
    # ROADMAP T2.2: Wenn AI-Tile verfuegbar -> direkt verwenden.
    ai = _get_ai_tile(biome)
    if ai is not None:
        return ai
    bd = BIOMES[biome]
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    surf.fill(bd['ground'])

    # Pflastersteine: 4x4 Quadrate mit leichtem Versatz
    cell = TILE_SIZE // 4
    rng = random.Random(hash(biome))  # deterministisch pro Biom
    for cy in range(4):
        for cx in range(4):
            x = cx * cell
            y = cy * cell
            shade = rng.uniform(0.85, 1.15)
            color = tuple(max(0, min(255, int(c * shade))) for c in bd['ground'])
            pygame.draw.rect(surf, color, (x, y, cell - 1, cell - 1))
            # Mörtel-Linien
            pygame.draw.rect(surf, bd['crack'], (x, y, cell, cell), 1)
            # Gelegentlich heller Stein
            if rng.random() < 0.15:
                hl = tuple(max(0, min(255, c + 8)) for c in color)
                pygame.draw.rect(surf, hl, (x + 2, y + 2, cell - 6, 2))

    # Biom-spezifische Details
    if biome == 'lava':
        # Helle Risse mit Glow
        for _ in range(6):
            x1 = rng.randint(0, TILE_SIZE)
            y1 = rng.randint(0, TILE_SIZE)
            x2 = x1 + rng.randint(-25, 25)
            y2 = y1 + rng.randint(-25, 25)
            pygame.draw.line(surf, bd['crack'], (x1, y1), (x2, y2), 2)
            pygame.draw.line(surf, (255, 200, 100), (x1, y1), (x2, y2), 1)
    elif biome == 'frost':
        # Eisrisse (weiß-blaue Linien)
        for _ in range(8):
            x1 = rng.randint(0, TILE_SIZE)
            y1 = rng.randint(0, TILE_SIZE)
            pts = [(x1, y1)]
            for _ in range(3):
                x1 += rng.randint(-12, 12)
                y1 += rng.randint(-12, 12)
                pts.append((x1, y1))
            if len(pts) >= 2:
                pygame.draw.lines(surf, bd['crack'], False, pts, 1)
    elif biome == 'crypt':
        # Dunkle Flecken (Schimmel)
        for _ in range(10):
            x = rng.randint(0, TILE_SIZE)
            y = rng.randint(0, TILE_SIZE)
            pygame.draw.circle(surf, bd['crack'], (x, y), rng.randint(2, 4))

    return surf


def get_tile(biome):
    if biome not in _tile_cache:
        _tile_cache[biome] = _make_tile(biome)
    return _tile_cache[biome]


def draw_floor(screen, biome, camera):
    """Kachelt den Boden über das ganze Sichtfeld, scrollt mit Kamera."""
    tile = get_tile(biome)
    ox = int(-camera.x) % TILE_SIZE - TILE_SIZE
    oy = int(-camera.y) % TILE_SIZE - TILE_SIZE
    for y in range(oy, SCREEN_H + TILE_SIZE, TILE_SIZE):
        for x in range(ox, SCREEN_W + TILE_SIZE, TILE_SIZE):
            screen.blit(tile, (x, y))


def draw_dungeon_floor(screen, grid, biome, w2s_xy, camera):
    """Zeichnet NUR Floor-Zellen des Grids (mit Boden-Textur).

    Update #42: Per-Biom Floor-Akzente (Risse/Mosaik/Pebbles/Runen) für
    atmosphärischere Dungeons. Akzente sind deterministisch (Hash aus
    cell-Position), damit jede Cell konstant ihre Variante behält.
    """
    from . import dungeon_gen as dg
    bd = BIOMES[biome]
    cell = grid.cell
    floor_col = bd['ground']
    alt_col = bd['ground_alt']
    crack_col = bd['crack']
    # Biom-spezifische Akzent-Paletten
    if biome == 'crypt':
        accent_a = (40, 32, 28)        # tiefer Riss
        accent_b = (180, 160, 120)     # heller Mosaik-Stein
        rune_col = (200, 170, 110)
    elif biome == 'frost':
        accent_a = (180, 200, 230)     # Eiskristall-Glanz
        accent_b = (110, 140, 190)     # Schatten-Riss
        rune_col = (200, 230, 255)
    elif biome == 'lava':
        accent_a = (255, 100, 30)      # Glut-Riss
        accent_b = (60, 30, 20)        # verbrannter Stein
        rune_col = (255, 180, 80)
    elif biome == 'desert':
        accent_a = (220, 180, 110)     # Sand-Spur
        accent_b = (130, 100, 50)      # dunkler Sand
        rune_col = (240, 210, 140)
    elif biome == 'swamp':
        accent_a = (50, 70, 40)        # Moos-Fleck
        accent_b = (90, 110, 70)       # Moos-Highlight
        rune_col = (140, 180, 120)
    elif biome == 'astral':
        accent_a = (140, 100, 220)     # Stern-Glanz
        accent_b = (60, 30, 100)       # Schatten
        rune_col = (190, 150, 240)
    else:
        accent_a = crack_col
        accent_b = alt_col
        rune_col = (200, 180, 120)

    # ROADMAP T2.2 + Tile-Variants: Wenn 4 Variants verfuegbar → per-Cell
    # deterministische Auswahl (Hash) gegen Pattern-Repeat.
    # Sonst Fallback auf Single-Tile.
    ai_variants_cell: list = []
    # 1px overlap-skalierung verhindert sichtbare schwarze Gitter-Linien
    # zwischen benachbarten Floor-Cells (Sub-Pixel-Rendering-Artefakt).
    tile_render_size = cell + 1
    try:
        from . import sprites as _spr
        variants = _spr.get_tile_variants(biome)
    except Exception:
        variants = []
    if variants:
        for i, v in enumerate(variants):
            cache_key = (biome, cell, 'var', i)
            v_cell = _dungeon_cell_cache.get(cache_key)
            if v_cell is None:
                try:
                    v_cell = pygame.transform.smoothscale(v, (tile_render_size, tile_render_size))
                    _dungeon_cell_cache[cache_key] = v_cell
                except Exception:
                    v_cell = None
            if v_cell is not None:
                ai_variants_cell.append(v_cell)
    # Fallback: Single-Tile (alter Pfad) wenn keine Variants
    ai_tile_cell = None
    if not ai_variants_cell:
        ai_full = _get_ai_tile(biome)
        if ai_full is not None:
            cache_key = (biome, cell)
            ai_tile_cell = _dungeon_cell_cache.get(cache_key)
            if ai_tile_cell is None:
                try:
                    ai_tile_cell = pygame.transform.smoothscale(ai_full, (tile_render_size, tile_render_size))
                    _dungeon_cell_cache[cache_key] = ai_tile_cell
                except Exception:
                    ai_tile_cell = None

    # Edge-Overlay-Lookup (Auto-Tile-Light, Update #160).
    # Nur aktiv wenn AI-Wall-Tile vorhanden — sonst bleibt 3D-Procedural
    # Walls aktiv, die haben bereits eigene Schatten-Logik.
    try:
        from . import sprites as _spr
        edge_enabled = _spr.TILE_WALL_MAP.get(biome) is not None
    except Exception:
        edge_enabled = False

    # Sichtbarer Cell-Bereich
    cam_cx, cam_cy = grid.world_to_cell(camera.x, camera.y)
    visible_w = SCREEN_W // cell + 2
    visible_h = SCREEN_H // cell + 2
    for cy in range(max(0, cam_cy - visible_h // 2), min(grid.h, cam_cy + visible_h // 2 + 1)):
        for cx in range(max(0, cam_cx - visible_w // 2), min(grid.w, cam_cx + visible_w // 2 + 1)):
            t = grid.tiles[cy][cx]
            if t in (dg.FLOOR, dg.TRAP, dg.DOOR):
                wx, wy = grid.cell_to_world_corner(cx, cy)
                sx, sy = w2s_xy(wx, wy)
                if ai_variants_cell:
                    # Deterministischer Variant-Picker per Cell-Hash
                    # — gleiche Cell zeigt immer die gleiche Variante,
                    # aber Nachbarn unterscheiden sich.
                    h = (cx * 73856093 ^ cy * 19349663) & 0x7FFFFFFF
                    v_idx = h % len(ai_variants_cell)
                    screen.blit(ai_variants_cell[v_idx], (sx, sy))
                elif ai_tile_cell is not None:
                    screen.blit(ai_tile_cell, (sx, sy))
                else:
                    col = alt_col if (cx + cy) % 2 == 0 else floor_col
                    pygame.draw.rect(screen, col, (sx, sy, cell + 1, cell + 1))
                    # Mörtellinie
                    pygame.draw.rect(screen, crack_col, (sx, sy, cell + 1, cell + 1), 1)
                # Auto-Tile-Edge-Overlay: 4-Neighbor-Bitmask, dann
                # gradient-Schatten auf Floor-Cells die an Wand grenzen.
                if edge_enabled and (ai_variants_cell or ai_tile_cell is not None):
                    em = 0
                    if grid.in_bounds(cx, cy - 1) and \
                            grid.tiles[cy - 1][cx] in (dg.VOID, dg.SECRET):
                        em |= 1  # N
                    if grid.in_bounds(cx + 1, cy) and \
                            grid.tiles[cy][cx + 1] in (dg.VOID, dg.SECRET):
                        em |= 2  # E
                    if grid.in_bounds(cx, cy + 1) and \
                            grid.tiles[cy + 1][cx] in (dg.VOID, dg.SECRET):
                        em |= 4  # S
                    if grid.in_bounds(cx - 1, cy) and \
                            grid.tiles[cy][cx - 1] in (dg.VOID, dg.SECRET):
                        em |= 8  # W
                    if em:
                        try:
                            overlay = _spr.get_edge_overlay(biome, em, cell)
                        except Exception:
                            overlay = None
                        if overlay is not None:
                            screen.blit(overlay, (sx, sy))
                # Deterministischer Akzent: nur ~1 von 8 Cells, basierend auf
                # Hash der Position (damit Pattern stabil bleibt).
                h = (cx * 73856093 ^ cy * 19349663) & 0xFFFF
                pick = h & 0x7  # 0..7
                if pick == 0:
                    # Riss (zwei Linien diagonal)
                    pygame.draw.line(screen, accent_a,
                                     (sx + 6, sy + 8),
                                     (sx + cell - 8, sy + cell - 14), 1)
                    pygame.draw.line(screen, accent_a,
                                     (sx + 10, sy + cell - 8),
                                     (sx + cell - 16, sy + 12), 1)
                elif pick == 1:
                    # Mosaik-Stein (kleines Highlight-Rechteck)
                    hx = sx + 8 + (h >> 4) % max(1, cell - 18)
                    hy = sy + 8 + (h >> 8) % max(1, cell - 18)
                    pygame.draw.rect(screen, accent_b,
                                     (hx, hy, 8, 6), 0)
                    pygame.draw.rect(screen, accent_a,
                                     (hx, hy, 8, 6), 1)
                elif pick == 2:
                    # Pebble-Cluster (3 Punkte)
                    for k in range(3):
                        dx_ = ((h >> (k * 3)) & 0xF) + 6
                        dy_ = ((h >> (k * 3 + 5)) & 0xF) + 6
                        pygame.draw.circle(screen, accent_b,
                                           (sx + dx_, sy + dy_), 2)
                        pygame.draw.circle(screen, accent_a,
                                           (sx + dx_, sy + dy_), 2, 1)
                elif pick == 3:
                    # Rune-Glyph: kleiner Kreis + Strich (selten, ~12.5%)
                    rx, ry = sx + cell // 2, sy + cell // 2
                    pygame.draw.circle(screen, rune_col, (rx, ry), 6, 1)
                    pygame.draw.line(screen, rune_col,
                                     (rx - 4, ry), (rx + 4, ry), 1)
                    pygame.draw.line(screen, rune_col,
                                     (rx, ry - 4), (rx, ry + 4), 1)
                elif pick == 4:
                    # Kanten-Schatten (Floor-Edge nahe Wand)
                    if grid.in_bounds(cx, cy - 1) and \
                            grid.tiles[cy - 1][cx] in (dg.VOID, dg.SECRET):
                        shadow = pygame.Surface(
                            (cell + 1, 8), pygame.SRCALPHA)
                        shadow.fill((0, 0, 0, 70))
                        screen.blit(shadow, (sx, sy))
                elif pick == 5:
                    # W-09 (Update #49): Biom-Signatur-Surface-Texture.
                    # Jedes Biom bekommt eine eigene atmosphärische
                    # Floor-Identität (Lore-Bibel: regional spürbar).
                    if biome == 'crypt':
                        # Salzkruste: weiße Kristall-Flecken (Marrowport-Salz)
                        for _i in range(3):
                            ox = (h >> (_i * 4 + 2)) & 0x1F
                            oy = (h >> (_i * 5 + 3)) & 0x1F
                            px = sx + 6 + (ox % max(1, cell - 12))
                            py = sy + 6 + (oy % max(1, cell - 12))
                            pygame.draw.circle(screen, (220, 230, 240),
                                                (px, py), 2)
                            pygame.draw.circle(screen, (160, 180, 200),
                                                (px, py), 2, 1)
                    elif biome == 'frost':
                        # Glas-Streu: silberne Splitter (Glasgolden-Lineage)
                        for _i in range(2):
                            ang_h = (h >> (_i * 3)) & 0x7
                            ang = ang_h * (math.pi / 4)
                            mid_x = sx + cell // 2
                            mid_y = sy + cell // 2
                            ex = mid_x + int(math.cos(ang) * 8)
                            ey = mid_y + int(math.sin(ang) * 8)
                            pygame.draw.line(screen, (220, 240, 255),
                                              (mid_x, mid_y), (ex, ey), 1)
                            pygame.draw.line(screen, (140, 180, 230),
                                              (mid_x, mid_y),
                                              (mid_x + (ex - mid_x) // 2,
                                               mid_y + (ey - mid_y) // 2), 2)
                    elif biome == 'lava':
                        # Asche-Drift: graue Schwaden (Vehren-Lineage)
                        ash_surf = pygame.Surface((cell, 14),
                                                    pygame.SRCALPHA)
                        for _i in range(4):
                            ax = ((h >> (_i * 3)) & 0xF) % cell
                            pygame.draw.line(
                                ash_surf, (90, 70, 60, 120),
                                (ax, _i * 3),
                                (min(cell, ax + 12), _i * 3 + 2), 2)
                        screen.blit(ash_surf, (sx, sy + cell - 16))
                    elif biome == 'desert':
                        # Sand-Drift: hellgelbe Wellen (Zhar-Eth-Karawanen)
                        wave_h = 3
                        for wx in range(0, cell, 5):
                            wy = sy + cell - 8 + int(math.sin(
                                (cx + wx * 0.1) * 1.4) * wave_h)
                            pygame.draw.line(screen, (240, 210, 140),
                                              (sx + wx, wy),
                                              (sx + wx + 3, wy), 2)
                    elif biome == 'swamp':
                        # Nass-Patches: dunkelgrüne Pfützen (Vossharil-Wurzel)
                        pw = 14 + ((h >> 6) & 0x7)
                        ph = 6 + ((h >> 9) & 0x3)
                        px_ = sx + 8 + ((h >> 2) & 0xF) % max(1, cell - pw - 8)
                        py_ = sy + 8 + ((h >> 5) & 0xF) % max(1, cell - ph - 8)
                        pud = pygame.Surface((pw, ph), pygame.SRCALPHA)
                        pygame.draw.ellipse(pud, (30, 50, 30, 150),
                                             (0, 0, pw, ph))
                        pygame.draw.ellipse(pud, (90, 130, 80, 200),
                                             (1, 1, pw - 2, ph - 2), 1)
                        screen.blit(pud, (px_, py_))
                    elif biome == 'astral':
                        # Stern-Glanz: lila Punkte (Spiegelhof-Sterne)
                        for _i in range(5):
                            ox = (h >> (_i * 3)) & 0x1F
                            oy = (h >> (_i * 5 + 1)) & 0x1F
                            px = sx + 4 + (ox % max(1, cell - 8))
                            py = sy + 4 + (oy % max(1, cell - 8))
                            pygame.draw.circle(screen, (220, 180, 255),
                                                (px, py), 1)


def draw_dungeon_walls(screen, grid, biome, w2s_xy, camera):
    """Zeichnet 3/4-View Wände mit hohem Kontrast zum Boden."""
    from . import dungeon_gen as dg
    bd = BIOMES[biome]
    cell = grid.cell
    # Distinkte Wand-Farben (Stein-grau, NICHT vom Boden abgeleitet)
    wall_top = (96, 86, 76)          # Hell-grauer Stein
    wall_top_alt = (130, 118, 100)   # Highlight-Variante
    wall_face = (52, 44, 36)         # Dunkle Seitenfläche
    wall_edge = (12, 8, 4)           # Schwarz für Outline
    if biome == 'frost':
        wall_top = (130, 150, 180)
        wall_top_alt = (170, 200, 230)
        wall_face = (40, 60, 90)
    elif biome == 'lava':
        wall_top = (90, 60, 40)
        wall_top_alt = (130, 80, 50)
        wall_face = (40, 18, 10)
    elif biome == 'desert':
        wall_top = (160, 130, 80)
        wall_top_alt = (190, 160, 100)
        wall_face = (90, 60, 30)
    elif biome == 'swamp':
        wall_top = (60, 80, 50)
        wall_top_alt = (90, 110, 70)
        wall_face = (24, 36, 24)
    elif biome == 'astral':
        wall_top = (70, 50, 130)
        wall_top_alt = (110, 80, 200)
        wall_face = (30, 14, 60)
    height = 22  # höhere Wand-Seite

    cam_cx, cam_cy = grid.world_to_cell(camera.x, camera.y)
    visible_w = SCREEN_W // cell + 3
    visible_h = SCREEN_H // cell + 3

    wall_blocks = []
    for cy in range(max(0, cam_cy - visible_h // 2),
                    min(grid.h, cam_cy + visible_h // 2 + 1)):
        for cx in range(max(0, cam_cx - visible_w // 2),
                        min(grid.w, cam_cx + visible_w // 2 + 1)):
            t = grid.tiles[cy][cx]
            is_wall_cell = t in (dg.VOID, dg.SECRET)
            if not is_wall_cell:
                continue
            neighbors_walkable = any(
                grid.in_bounds(cx + dx, cy + dy) and
                grid.tiles[cy + dy][cx + dx] in (dg.FLOOR, dg.TRAP, dg.DOOR)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
            )
            if not neighbors_walkable:
                # Innen-Wand (zwischen anderen Walls) — überspringen, spart Render
                continue
            wall_blocks.append((cy, cx))

    # ROADMAP T2.2: AI-Wall-Tile pro Biome ggf. einmal cachen.
    ai_wall_cell = None
    try:
        from . import sprites as _spr
        ai_wall_full = _spr.get_wall_sprite(biome)
        if ai_wall_full is not None:
            wkey = (biome, cell, 'wall')
            ai_wall_cell = _dungeon_cell_cache.get(wkey)
            if ai_wall_cell is None:
                # +1 overlap analog Floor-Tiles
                ai_wall_cell = pygame.transform.smoothscale(ai_wall_full, (cell + 1, cell + 1))
                _dungeon_cell_cache[wkey] = ai_wall_cell
    except Exception:
        ai_wall_cell = None

    # Update: Wenn AI-Wall geladen → flat-top-down-Look (height=0, keine
    # 3D-Erhebung). Sonst Procedural-3D mit height=22 wie bisher.
    if ai_wall_cell is not None:
        height = 0

    wall_blocks.sort(key=lambda b: b[0])
    for cy, cx in wall_blocks:
        wx, wy = grid.cell_to_world_corner(cx, cy)
        sx, sy = w2s_xy(wx, wy)
        sx, sy = int(sx), int(sy)
        below = grid.in_bounds(cx, cy + 1) and grid.tiles[cy + 1][cx] in (dg.FLOOR, dg.TRAP, dg.DOOR)
        right_floor = grid.in_bounds(cx + 1, cy) and grid.tiles[cy][cx + 1] in (dg.FLOOR, dg.TRAP, dg.DOOR)
        left_floor = grid.in_bounds(cx - 1, cy) and grid.tiles[cy][cx - 1] in (dg.FLOOR, dg.TRAP, dg.DOOR)
        # Schatten + Side-Face NUR im Procedural-Modus (height>0)
        if height > 0 and right_floor:
            shadow = pygame.Surface((10, cell + height), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, 130))
            screen.blit(shadow, (sx + cell, sy))
        if height > 0 and below:
            pygame.draw.rect(screen, wall_face,
                             (sx, sy + cell, cell + 1, height))
            # Vertikale Fugen
            pygame.draw.line(screen, wall_edge,
                             (sx + cell // 2, sy + cell),
                             (sx + cell // 2, sy + cell + height), 1)
            # Untere Schwarzlinie
            pygame.draw.rect(screen, wall_edge,
                             (sx, sy + cell, cell + 1, height), 2)
        # Top-Face — ROADMAP T2.2: AI-Wall-Tile wenn verfuegbar, sonst Procedural.
        if ai_wall_cell is not None:
            # 1px overlap (cell+1) damit keine schwarzen Lines zwischen Cells
            screen.blit(ai_wall_cell, (sx, sy))
            # KEINE Outline — AI-Tile hat eigene Stein-Definition
        else:
            # Procedural-Top-Face mit Stein-Pattern
            col_top = wall_top if (cx + cy) % 2 == 0 else wall_top_alt
            pygame.draw.rect(screen, col_top, (sx, sy, cell + 1, cell + 1))
            pygame.draw.line(screen, wall_top_alt,
                             (sx + 2, sy + 2), (sx + cell - 2, sy + 2), 2)
            pygame.draw.line(screen, wall_face,
                             (sx, sy + cell // 2), (sx + cell, sy + cell // 2), 1)
            pygame.draw.line(screen, wall_face,
                             (sx + cell // 2, sy), (sx + cell // 2, sy + cell), 1)
            pygame.draw.rect(screen, wall_edge, (sx, sy, cell + 1, cell + 1), 3)


def draw_traps(screen, grid, w2s_xy, camera):
    """Zeichnet Trap-Tiles (Stachel, Feuer, Pfeil, Platte)."""
    cell = grid.cell
    cam_cx, cam_cy = grid.world_to_cell(camera.x, camera.y)
    visible_w = SCREEN_W // cell + 3
    visible_h = SCREEN_H // cell + 3
    for cx, cy, ttype in grid.traps:
        if not (cam_cx - visible_w // 2 - 1 <= cx <= cam_cx + visible_w // 2 + 1):
            continue
        if not (cam_cy - visible_h // 2 - 1 <= cy <= cam_cy + visible_h // 2 + 1):
            continue
        wx, wy = grid.cell_to_world_center(cx, cy)
        sx, sy = w2s_xy(wx, wy)
        sx, sy = int(sx), int(sy)
        if ttype == 'spike':
            # Spike-Tile: schwarze Dreiecke
            for k in range(4):
                a = k * math.pi / 2 + math.pi / 4
                tx = sx + int(math.cos(a) * 14)
                ty = sy + int(math.sin(a) * 14)
                pygame.draw.polygon(screen, (50, 40, 30),
                                    [(tx - 4, ty + 4), (tx + 4, ty + 4), (tx, ty - 8)])
                pygame.draw.polygon(screen, (180, 180, 180),
                                    [(tx - 3, ty + 3), (tx + 3, ty + 3), (tx, ty - 6)])
        elif ttype == 'fire':
            # Flammen-Tile (animiert)
            phase = pygame.time.get_ticks() * 0.005 + cx * 0.5 + cy * 0.3
            active = (math.sin(phase) > 0.3)
            if active:
                glow = pygame.Surface((50, 50), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 100, 30, 140), (25, 25), 22)
                pygame.draw.circle(glow, (255, 200, 100, 200), (25, 25), 10)
                screen.blit(glow, (sx - 25, sy - 25))
            # Düse am Boden immer sichtbar
            pygame.draw.circle(screen, (60, 40, 30), (sx, sy), 5)
            pygame.draw.circle(screen, BLACK, (sx, sy), 5, 1)
        elif ttype == 'arrow':
            # Wandöffnung mit Pfeil-Symbol
            pygame.draw.rect(screen, (40, 30, 20), (sx - 8, sy - 8, 16, 16))
            pygame.draw.polygon(screen, (200, 180, 100),
                                [(sx - 4, sy), (sx + 4, sy - 3), (sx + 4, sy + 3)])
        elif ttype == 'plate':
            # Druckplatte (rundlich)
            pygame.draw.circle(screen, (70, 60, 40), (sx, sy), 18, 3)
            pygame.draw.circle(screen, (50, 45, 30), (sx, sy), 14)
        elif ttype == 'sumpf_pool':
            # Schlammtümpel (dunkel-grün, blubbert)
            phase = pygame.time.get_ticks() * 0.003 + cx * 0.5
            pygame.draw.ellipse(screen, (40, 60, 32), (sx - 22, sy - 14, 44, 28))
            pygame.draw.ellipse(screen, (60, 90, 50), (sx - 20, sy - 12, 40, 24))
            # Blubber-Blasen
            for k in range(3):
                bx = sx + math.cos(phase + k * 2) * 8
                by = sy + math.sin(phase * 0.5 + k * 2) * 4
                pygame.draw.circle(screen, (80, 120, 70),
                                    (int(bx), int(by)), 2)
        elif ttype == 'lava_pool':
            # Lava-See (glüht)
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.004 + sx * 0.01))
            sw = pygame.Surface((44, 28), pygame.SRCALPHA)
            pygame.draw.ellipse(sw, (40, 15, 8), (0, 0, 44, 28))
            pygame.draw.ellipse(sw, (255, 120, 40, int(180 + pulse * 60)),
                                 (4, 3, 36, 22))
            pygame.draw.ellipse(sw, (255, 200, 100, int(220 + pulse * 30)),
                                 (10, 7, 24, 14))
            screen.blit(sw, (sx - 22, sy - 14))
        elif ttype == 'ice_patch':
            # Eisfläche (leicht durchsichtig)
            sw = pygame.Surface((40, 24), pygame.SRCALPHA)
            pygame.draw.ellipse(sw, (180, 220, 255, 160),
                                 (0, 0, 40, 24))
            pygame.draw.ellipse(sw, (240, 250, 255, 200),
                                 (4, 4, 32, 16), 1)
            # Risse
            pygame.draw.line(sw, (180, 220, 255, 200),
                              (8, 4), (20, 16), 1)
            pygame.draw.line(sw, (180, 220, 255, 200),
                              (16, 6), (28, 18), 1)
            screen.blit(sw, (sx - 20, sy - 12))
        elif ttype == 'quicksand':
            # Treibsand
            pygame.draw.ellipse(screen, (140, 110, 60), (sx - 18, sy - 12, 36, 24))
            pygame.draw.ellipse(screen, (180, 150, 80), (sx - 14, sy - 8, 28, 16))
            for k in range(4):
                ang = k * 1.57 + pygame.time.get_ticks() * 0.001
                rx = sx + int(math.cos(ang) * 8)
                ry = sy + int(math.sin(ang) * 5)
                pygame.draw.circle(screen, (200, 170, 100), (rx, ry), 1)
        elif ttype == 'bone_pile':
            # Knochenstapel
            for k in range(3):
                pygame.draw.line(screen, (200, 190, 160),
                                  (sx - 10 + k * 4, sy + 6 - k * 2),
                                  (sx + 10 - k * 4, sy + 6 - k * 2), 2)
            pygame.draw.circle(screen, (220, 210, 180), (sx, sy - 4), 4)
            pygame.draw.circle(screen, BLACK, (sx - 1, sy - 5), 1)
            pygame.draw.circle(screen, BLACK, (sx + 1, sy - 5), 1)


def _shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])


# ============================================================
# DECOR-GENERIERUNG
# ============================================================
def generate_decor(biome):
    biome_data = BIOMES[biome]
    tiles = []
    bounds = 2200
    # Kleine Streu-Decor (viel)
    for _ in range(120):
        tiles.append(Decor(
            random.uniform(-bounds, bounds),
            random.uniform(-bounds, bounds),
            random.choice(biome_data['small_decor']),
            random.uniform(0, math.tau),
        ))
    # Mittelgroße Stein-Platten (locker verteilt, am Boden)
    for _ in range(40):
        tiles.append(Decor(
            random.uniform(-bounds, bounds),
            random.uniform(-bounds, bounds),
            'stone',
            random.uniform(0, math.tau),
            random.uniform(40, 90),
            random.uniform(0.05, 0.18),
        ))
    # Große Objekte (selten, beeindruckend)
    for _ in range(18):
        tiles.append(Decor(
            random.uniform(-bounds, bounds),
            random.uniform(-bounds, bounds),
            random.choice(biome_data['big_decor']),
            random.uniform(0, math.tau),
        ))
    return tiles


# ============================================================
# DECOR-ZEICHNEN
# ============================================================
def _decor_shadow(screen, sx, sy, w=40, h=16, alpha=110):
    """Update #153 (PLAN U-03): Generischer Drop-Shadow für Tall-Decor.

    Rendert eine flache Ellipse unter dem Decor-Ground-Anker.  Größe
    proportional zur Sprite-Breite; alpha 110 mittel-stark (sichtbar
    aber nicht erdrückend).  Wird VOR dem Decor-Body gezeichnet, damit
    der Schatten unter dem Sprite liegt.
    """
    sh = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, alpha), (0, 0, w, h))
    screen.blit(sh, (sx - w // 2, sy + 4))


def draw_decor(screen, t, sp, biome):
    biome_data = BIOMES[biome]
    sx, sy = int(sp[0]), int(sp[1])

    if t.kind == 'stone':
        alpha = int(80 * t.shade)
        s = int(t.size)
        surf = pygame.Surface((s, s), pygame.SRCALPHA)
        col = biome_data['ground_alt']
        pygame.draw.rect(surf, (*col, alpha), (0, 0, s, s))
        pygame.draw.rect(surf, (*biome_data['accent'], alpha // 2), (0, 0, s, s), 1)
        rot = pygame.transform.rotate(surf, math.degrees(t.rot))
        screen.blit(rot, (sx - rot.get_width() // 2, sy - rot.get_height() // 2))

    elif t.kind == 'skull':
        # Schädel mit Tiefe
        pygame.draw.circle(screen, (180, 160, 130), (sx, sy), 7)
        pygame.draw.circle(screen, (120, 100, 80), (sx, sy), 7, 1)
        pygame.draw.ellipse(screen, BLACK, (sx - 4, sy - 2, 3, 4))
        pygame.draw.ellipse(screen, BLACK, (sx + 1, sy - 2, 3, 4))
        pygame.draw.line(screen, (80, 60, 50), (sx - 3, sy + 3), (sx + 3, sy + 3), 1)
        # Zähne
        for k in (-2, 0, 2):
            pygame.draw.line(screen, WHITE, (sx + k, sy + 3), (sx + k, sy + 5), 1)

    elif t.kind == 'bone':
        pygame.draw.line(screen, (200, 180, 150), (sx - 10, sy), (sx + 10, sy), 3)
        pygame.draw.circle(screen, (200, 180, 150), (sx - 10, sy - 1), 3)
        pygame.draw.circle(screen, (200, 180, 150), (sx - 10, sy + 1), 3)
        pygame.draw.circle(screen, (200, 180, 150), (sx + 10, sy - 1), 3)
        pygame.draw.circle(screen, (200, 180, 150), (sx + 10, sy + 1), 3)

    elif t.kind == 'rock':
        pts = [(sx - 12, sy + 5), (sx - 7, sy - 7),
               (sx + 5, sy - 6), (sx + 10, sy + 4)]
        pygame.draw.polygon(screen, biome_data['ground_alt'], pts)
        pygame.draw.polygon(screen, biome_data['ground'], pts, 1)
        # Highlight oben links
        pygame.draw.line(screen, biome_data['accent'],
                         (sx - 8, sy - 4), (sx - 3, sy - 6), 1)

    elif t.kind == 'rune':
        col = biome_data['accent']
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.001 + sx * 0.01)) * 80 + 100
        glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*col, int(pulse * 0.3)), (20, 20), 18)
        screen.blit(glow, (sx - 20, sy - 20))
        pygame.draw.circle(screen, col, (sx, sy), 14, 1)
        pygame.draw.line(screen, col, (sx - 10, sy), (sx + 10, sy), 1)
        pygame.draw.line(screen, col, (sx, sy - 10), (sx, sy + 10), 1)
        pygame.draw.line(screen, col, (sx - 7, sy - 7), (sx + 7, sy + 7), 1)
        pygame.draw.line(screen, col, (sx + 7, sy - 7), (sx - 7, sy + 7), 1)

    elif t.kind == 'ice':
        # Kristallcluster
        pts = [(sx, sy - 10), (sx + 7, sy + 2), (sx + 2, sy + 8),
               (sx - 4, sy + 6), (sx - 7, sy - 2)]
        pygame.draw.polygon(screen, (160, 200, 240), pts)
        pygame.draw.polygon(screen, (220, 240, 255), pts, 1)
        # Highlight
        pygame.draw.line(screen, WHITE, (sx - 2, sy - 6), (sx + 3, sy + 4), 1)

    elif t.kind == 'ember':
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003 + sx * 0.02))
        glow = pygame.Surface((28, 28), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 120, 40, int(80 + pulse * 60)), (14, 14), 12)
        pygame.draw.circle(glow, (255, 220, 120, int(180 + pulse * 60)), (14, 14), 5)
        screen.blit(glow, (sx - 14, sy - 14))

    elif t.kind == 'pillar':
        # Säule (großes Objekt, von oben gesehen)
        pygame.draw.circle(screen, (70, 60, 50), (sx, sy + 8), 18)  # Basis
        pygame.draw.circle(screen, (50, 40, 30), (sx, sy + 8), 18, 2)
        # Säulen-Hauptkörper
        pygame.draw.circle(screen, (110, 95, 80), (sx, sy), 12)
        pygame.draw.circle(screen, (80, 65, 50), (sx, sy), 12, 2)
        pygame.draw.circle(screen, (140, 120, 95), (sx - 2, sy - 2), 5)
        # Schatten
        sh = pygame.Surface((40, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 120), (0, 0, 40, 18))
        screen.blit(sh, (sx - 20, sy + 12))

    elif t.kind == 'frozen_pillar':
        _decor_shadow(screen, sx, sy + 8, w=42, h=18)
        pygame.draw.circle(screen, (60, 80, 110), (sx, sy + 8), 18)
        pygame.draw.circle(screen, (40, 60, 90), (sx, sy + 8), 18, 2)
        pygame.draw.circle(screen, (130, 170, 220), (sx, sy), 14)
        pygame.draw.circle(screen, (200, 230, 255), (sx, sy), 14, 2)
        # Eiskristalle drum
        for k, ang in enumerate((0.3, 1.5, 2.7, 3.9, 5.1)):
            ex = sx + math.cos(ang) * 14
            ey = sy + math.sin(ang) * 14
            pygame.draw.polygon(screen, (220, 240, 255), [
                (int(ex), int(ey - 4)), (int(ex + 3), int(ey)),
                (int(ex), int(ey + 4)), (int(ex - 3), int(ey)),
            ])

    elif t.kind == 'torch':
        _decor_shadow(screen, sx, sy + 8, w=22, h=10, alpha=130)
        # Säulenfuß
        pygame.draw.rect(screen, (60, 45, 30), (sx - 4, sy - 4, 8, 16))
        pygame.draw.rect(screen, (40, 30, 20), (sx - 4, sy - 4, 8, 16), 1)
        # Update #36: Großer Atmosphäre-Glow um Fackel (additiv-blend).
        # Flackert mit ±15 % Intensität, gibt dem Dungeon „Licht-Inseln".
        flicker_t = pygame.time.get_ticks() * 0.01 + sx * 0.1
        flicker = math.sin(flicker_t) * 2
        intensity = 0.85 + 0.15 * math.sin(flicker_t * 0.7)
        # Außen-Glow (großer warmer Halo)
        big_glow = pygame.Surface((96, 96), pygame.SRCALPHA)
        pygame.draw.circle(big_glow,
                            (255, 150, 60, int(45 * intensity)),
                            (48, 48), 44)
        pygame.draw.circle(big_glow,
                            (255, 180, 80, int(80 * intensity)),
                            (48, 48), 30)
        screen.blit(big_glow, (sx - 48, sy - 48 + int(flicker)),
                     special_flags=pygame.BLEND_RGBA_ADD)
        # Innen-Flamme
        glow = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 140, 40, int(120 * intensity)),
                            (15, 15), 14)
        pygame.draw.circle(glow, (255, 220, 120, int(220 * intensity)),
                            (15, 15), 7)
        screen.blit(glow, (sx - 15, sy - 15 + int(flicker)))
        pygame.draw.polygon(screen, (255, 220, 120), [
            (sx, sy - 14 + int(flicker)),
            (sx + 4, sy - 6),
            (sx - 4, sy - 6),
        ])
        pygame.draw.circle(screen, WHITE, (sx, sy - 8 + int(flicker)), 2)

    elif t.kind == 'sarcophagus':
        _decor_shadow(screen, sx, sy + 12, w=58, h=20)
        # Steinsarg, langgezogen
        sw = pygame.Surface((48, 24), pygame.SRCALPHA)
        sw.fill((0, 0, 0, 0))
        pygame.draw.rect(sw, (90, 75, 60), (0, 0, 48, 24))
        pygame.draw.rect(sw, (60, 50, 40), (0, 0, 48, 24), 2)
        pygame.draw.rect(sw, (130, 110, 85), (2, 2, 44, 6))
        pygame.draw.circle(sw, (50, 40, 30), (24, 14), 5)
        # Kreuz oben drauf
        pygame.draw.line(sw, GOLD, (24, 11), (24, 19), 1)
        pygame.draw.line(sw, GOLD, (20, 14), (28, 14), 1)
        rot = pygame.transform.rotate(sw, math.degrees(t.rot))
        screen.blit(rot, (sx - rot.get_width() // 2, sy - rot.get_height() // 2))

    elif t.kind == 'broken_wall':
        _decor_shadow(screen, sx, sy + 10, w=56, h=16)
        # Mauer-Rest, verschiedene Stein-Reihen
        sw = pygame.Surface((50, 24), pygame.SRCALPHA)
        for row in range(3):
            for col in range(4):
                x = col * 12 + (row % 2) * 6
                y = row * 8
                if random.Random(int(sx + sy + row + col)).random() < 0.75:
                    pygame.draw.rect(sw, (80, 70, 55), (x, y, 11, 7))
                    pygame.draw.rect(sw, (50, 40, 30), (x, y, 11, 7), 1)
        rot = pygame.transform.rotate(sw, math.degrees(t.rot))
        screen.blit(rot, (sx - rot.get_width() // 2, sy - rot.get_height() // 2))

    elif t.kind == 'ice_spike':
        _decor_shadow(screen, sx, sy + 6, w=30, h=10)
        # Gruppe von Eis-Spitzen
        for off, height in ((-6, 10), (0, 16), (6, 12)):
            base_pts = [
                (sx + off - 4, sy + 6),
                (sx + off + 4, sy + 6),
                (sx + off, sy + 6 - height),
            ]
            pygame.draw.polygon(screen, (160, 200, 240), base_pts)
            pygame.draw.polygon(screen, (220, 240, 255), base_pts, 1)
            pygame.draw.line(screen, WHITE,
                             (sx + off, sy + 6 - height + 2),
                             (sx + off, sy + 6 - height // 2), 1)

    elif t.kind == 'fountain':
        # Steinbrunnen mit Wasser
        pygame.draw.circle(screen, (60, 50, 40), (sx, sy + 6), 24)
        pygame.draw.circle(screen, BLACK, (sx, sy + 6), 24, 2)
        pygame.draw.circle(screen, (60, 100, 160), (sx, sy + 6), 18)
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003))
        pygame.draw.circle(screen, (140, 180, 240), (sx, sy + 6), int(14 + pulse * 2))
        pygame.draw.circle(screen, WHITE, (sx - 4, sy + 2), 2)
        # Sockel-Säule mit Wasserspeier
        pygame.draw.rect(screen, (80, 70, 60), (sx - 4, sy - 18, 8, 14))
        pygame.draw.circle(screen, (140, 180, 240), (sx, sy - 14), 4)

    elif t.kind == 'chest_decor':
        # Truhe (geschlossen, gold-rand)
        pygame.draw.rect(screen, (90, 60, 30), (sx - 14, sy - 6, 28, 18))
        pygame.draw.rect(screen, BLACK, (sx - 14, sy - 6, 28, 18), 2)
        pygame.draw.rect(screen, (130, 90, 50), (sx - 14, sy - 6, 28, 6))
        pygame.draw.rect(screen, GOLD, (sx - 4, sy - 6, 8, 14))
        pygame.draw.rect(screen, BLACK, (sx - 4, sy - 6, 8, 14), 1)
        # Glow
        glow = pygame.Surface((40, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 220, 120, 80), (0, 0, 40, 22))
        screen.blit(glow, (sx - 20, sy - 4))

    elif t.kind == 'house':
        # Top-Down-Haus: Mauern + Dach (Schräg) + Tür
        # Dach
        roof_color = (130, 60, 40)
        roof_dark = (90, 40, 24)
        sz = int(t.size) if t.size > 20 else 60
        # Hausgrundriss (Schatten)
        sh = pygame.Surface((sz + 20, sz // 2 + 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 100), (0, 0, sz + 20, sz // 2 + 12))
        screen.blit(sh, (sx - sz // 2 - 10, sy + sz // 2 - 6))
        # Wände (sechseckiger Top-View)
        pygame.draw.rect(screen, (160, 130, 90),
                         (sx - sz // 2, sy - sz // 2, sz, sz))
        pygame.draw.rect(screen, BLACK,
                         (sx - sz // 2, sy - sz // 2, sz, sz), 2)
        # Dach (Dreieck-Top, Trapezoid für 3/4-View)
        roof_pts = [
            (sx - sz // 2 - 4, sy - sz // 2),
            (sx + sz // 2 + 4, sy - sz // 2),
            (sx + sz // 2 - 8, sy - sz // 2 - 18),
            (sx - sz // 2 + 8, sy - sz // 2 - 18),
        ]
        pygame.draw.polygon(screen, roof_color, roof_pts)
        pygame.draw.polygon(screen, roof_dark, roof_pts, 2)
        # First (Linie auf Dach)
        pygame.draw.line(screen, roof_dark,
                         (sx - sz // 2 + 4, sy - sz // 2 - 12),
                         (sx + sz // 2 - 4, sy - sz // 2 - 12), 2)
        # Tür
        pygame.draw.rect(screen, (80, 50, 30),
                         (sx - 6, sy + sz // 2 - 12, 12, 12))
        pygame.draw.circle(screen, GOLD, (sx + 3, sy + sz // 2 - 6), 1)
        # Fenster (gelb glühend)
        pygame.draw.rect(screen, (255, 200, 100),
                         (sx - sz // 3 - 3, sy - 4, 6, 6))
        pygame.draw.rect(screen, BLACK,
                         (sx - sz // 3 - 3, sy - 4, 6, 6), 1)
        pygame.draw.rect(screen, (255, 200, 100),
                         (sx + sz // 3 - 3, sy - 4, 6, 6))
        pygame.draw.rect(screen, BLACK,
                         (sx + sz // 3 - 3, sy - 4, 6, 6), 1)

    elif t.kind == 'market_stall':
        # Marktstand mit Sonnensegel
        # Pfosten
        pygame.draw.rect(screen, (90, 60, 30), (sx - 14, sy - 4, 3, 14))
        pygame.draw.rect(screen, (90, 60, 30), (sx + 11, sy - 4, 3, 14))
        # Segel
        sail = pygame.Surface((36, 12), pygame.SRCALPHA)
        sail.fill((180, 60, 60))
        screen.blit(sail, (sx - 18, sy - 14))
        pygame.draw.rect(screen, BLACK, (sx - 18, sy - 14, 36, 12), 1)
        # Verkaufstheke
        pygame.draw.rect(screen, (140, 100, 60), (sx - 14, sy - 2, 28, 8))
        pygame.draw.rect(screen, BLACK, (sx - 14, sy - 2, 28, 8), 1)
        # Waren (3 kleine Kreise)
        pygame.draw.circle(screen, (220, 60, 60), (sx - 7, sy + 2), 2)
        pygame.draw.circle(screen, (60, 220, 60), (sx, sy + 2), 2)
        pygame.draw.circle(screen, (60, 100, 220), (sx + 7, sy + 2), 2)

    elif t.kind == 'well':
        # Brunnen mit Holzdach
        pygame.draw.circle(screen, (60, 50, 40), (sx, sy + 4), 18)
        pygame.draw.circle(screen, BLACK, (sx, sy + 4), 18, 2)
        pygame.draw.circle(screen, (40, 60, 90), (sx, sy + 4), 14)
        # Pfosten + Dach
        pygame.draw.line(screen, (90, 60, 30), (sx - 14, sy + 4), (sx - 14, sy - 16), 3)
        pygame.draw.line(screen, (90, 60, 30), (sx + 14, sy + 4), (sx + 14, sy - 16), 3)
        roof_pts = [(sx - 18, sy - 16), (sx + 18, sy - 16),
                    (sx + 6, sy - 24), (sx - 6, sy - 24)]
        pygame.draw.polygon(screen, (130, 60, 40), roof_pts)
        pygame.draw.polygon(screen, BLACK, roof_pts, 2)

    elif t.kind == 'crate':
        pygame.draw.rect(screen, (110, 75, 45), (sx - 8, sy - 8, 16, 16))
        pygame.draw.rect(screen, BLACK, (sx - 8, sy - 8, 16, 16), 1)
        pygame.draw.line(screen, (80, 55, 30), (sx, sy - 8), (sx, sy + 8), 1)
        pygame.draw.line(screen, (80, 55, 30), (sx - 8, sy), (sx + 8, sy), 1)

    elif t.kind == 'barrel':
        pygame.draw.ellipse(screen, (90, 60, 30), (sx - 8, sy - 9, 16, 18))
        pygame.draw.ellipse(screen, BLACK, (sx - 8, sy - 9, 16, 18), 1)
        for dy in (sy - 4, sy + 1, sy + 6):
            pygame.draw.line(screen, (60, 40, 20),
                             (sx - 7, dy), (sx + 7, dy), 1)

    elif t.kind == 'banner':
        # Update #119: Faction-Banner-Support.  Hat das Banner ein
        # `faction_color`-Attribut, übernimmt es die Fraktions-Farbe;
        # sonst Standard-Rot.  Faction-Banner sind zusätzlich größer
        # gerendert für bessere Sichtbarkeit + Glow-Highlight am Saum.
        flag_color = getattr(t, 'faction_color', None) or (180, 50, 50)
        is_faction = hasattr(t, 'faction_color')
        # Stange (Faction-Variante etwas höher)
        pole_top = sy - 28 if is_faction else sy - 16
        pygame.draw.line(screen, (60, 40, 20),
                          (sx, pole_top), (sx, sy + 6), 2)
        # Fahne (Faction-Variante 26 px hoch statt 20)
        if is_faction:
            flag_pts = [(sx, sy - 26), (sx + 16, sy - 26),
                        (sx + 12, sy - 12), (sx + 16, sy + 4),
                        (sx, sy + 4)]
        else:
            flag_pts = [(sx, sy - 14), (sx + 12, sy - 14),
                        (sx + 8, sy - 4), (sx + 12, sy + 6),
                        (sx, sy + 6)]
        pygame.draw.polygon(screen, flag_color, flag_pts)
        pygame.draw.polygon(screen, BLACK, flag_pts, 1)
        # Sigil-Knopf
        sig_y = sy - 11 if is_faction else sy - 4
        pygame.draw.circle(screen, GOLD, (sx + 5, sig_y), 2)
        # Faction-Banner haben Glow-Highlight am Saum
        if is_faction:
            highlight = (min(255, flag_color[0] + 40),
                          min(255, flag_color[1] + 40),
                          min(255, flag_color[2] + 40))
            pygame.draw.line(screen, highlight,
                              (sx + 1, sy - 25), (sx + 14, sy - 25), 1)

    elif t.kind == 'statue':
        # Statue (großer Sockel + Figur)
        pygame.draw.rect(screen, (90, 80, 70), (sx - 10, sy + 6, 20, 8))
        pygame.draw.rect(screen, BLACK, (sx - 10, sy + 6, 20, 8), 2)
        pygame.draw.rect(screen, (120, 110, 95), (sx - 6, sy - 16, 12, 22))
        pygame.draw.circle(screen, (140, 130, 110), (sx, sy - 20), 5)
        pygame.draw.circle(screen, BLACK, (sx, sy - 20), 5, 1)

    elif t.kind == 'path_tile':
        # Heller Pflaster-Stein als Weg-Markierung (klein, flach)
        bd = biome_data
        path_col = tuple(min(255, c + 35) for c in bd['ground'][:3])
        path_dark = bd.get('crack', (40, 30, 20))
        pygame.draw.rect(screen, path_col, (sx - 14, sy - 14, 28, 28))
        pygame.draw.rect(screen, path_dark, (sx - 14, sy - 14, 28, 28), 1)
        # Subtile Steinplatten-Kreuz
        pygame.draw.line(screen, path_dark, (sx - 14, sy), (sx + 14, sy), 1)
        pygame.draw.line(screen, path_dark, (sx, sy - 14), (sx, sy + 14), 1)

    elif t.kind == 'lore_tablet':
        # Steintafel mit glühender Schrift
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003))
        glow = pygame.Surface((40, 30), pygame.SRCALPHA)
        if not getattr(t, 'lore_read', False):
            pygame.draw.rect(glow, (180, 140, 60, int(80 + pulse * 40)),
                              (0, 0, 40, 30))
        screen.blit(glow, (sx - 20, sy - 15))
        pygame.draw.rect(screen, (90, 80, 60), (sx - 14, sy - 10, 28, 20))
        pygame.draw.rect(screen, BLACK, (sx - 14, sy - 10, 28, 20), 2)
        # Schrift-Linien
        for dy in (-4, 0, 4):
            pygame.draw.line(screen, (200, 170, 100),
                              (sx - 10, sy + dy), (sx + 10, sy + dy), 1)
        if not getattr(t, 'lore_read', False):
            # Glühendes Sternchen
            pygame.draw.circle(screen, (255, 220, 100),
                                (sx + 10, sy - 10), 3)

    elif t.kind == 'bookshelf':
        _decor_shadow(screen, sx, sy + 12, w=36, h=12)
        pygame.draw.rect(screen, (70, 50, 30), (sx - 14, sy - 24, 28, 36))
        pygame.draw.rect(screen, BLACK, (sx - 14, sy - 24, 28, 36), 2)
        # Bücher in Reihen
        for ry, row_y in enumerate((sy - 18, sy - 6, sy + 6)):
            for k, dx in enumerate((-10, -5, 0, 5, 10)):
                col_choices = [(140, 30, 30), (30, 80, 140), (80, 50, 120), (120, 100, 40)]
                col = col_choices[(k + ry) % len(col_choices)]
                pygame.draw.rect(screen, col, (sx + dx - 1, row_y - 4, 4, 8))

    elif t.kind == 'lantern':
        _decor_shadow(screen, sx, sy, w=20, h=8, alpha=130)
        # Update #134 (User-Screenshot): Laternen-Glow war massiv
        # überdimensioniert (72×72 + BLEND_ADD) und mit ~20 Laternen pro
        # Town entstand eine gelbe Glow-Wand die die Stadt verdeckt hat.
        # Jetzt: kleiner Halo (32×32) ohne additive Blend, dezenter
        # innerer Glow.  Lore-Atmosphäre bleibt, aber Stadt-Layout ist
        # wieder lesbar.
        pygame.draw.line(screen, (60, 50, 40), (sx, sy - 16), (sx, sy - 4), 1)
        flicker_t = pygame.time.get_ticks() * 0.008 + sx * 0.1
        flicker = math.sin(flicker_t) * 1.5
        intensity = 0.88 + 0.12 * math.sin(flicker_t * 0.6)
        # Kleiner Atmosphäre-Halo (kein additive Blend mehr)
        halo = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(halo,
                            (255, 200, 110, int(48 * intensity)),
                            (16, 16), 14)
        pygame.draw.circle(halo,
                            (255, 220, 140, int(90 * intensity)),
                            (16, 16), 8)
        screen.blit(halo, (sx - 16, sy - 16 + int(flicker)))
        # Laternen-Korpus
        pygame.draw.circle(screen, (200, 160, 90), (sx, sy), 6)
        pygame.draw.circle(screen, BLACK, (sx, sy), 6, 1)
        pygame.draw.circle(screen, (255, 240, 180), (sx, sy), 3)

    elif t.kind == 'mushroom':
        # Glühender Sumpf-Pilz (Stiel + leuchtende Kappe)
        pygame.draw.rect(screen, (200, 190, 160), (sx - 3, sy + 2, 6, 10))
        cap_color = (200, 80, 200)
        glow = pygame.Surface((30, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*cap_color, 120), (0, 0, 30, 14))
        screen.blit(glow, (sx - 15, sy - 8))
        pygame.draw.ellipse(screen, cap_color, (sx - 12, sy - 6, 24, 12))
        pygame.draw.ellipse(screen, BLACK, (sx - 12, sy - 6, 24, 12), 1)
        # Punkte auf der Kappe
        for k in (-6, 0, 6):
            pygame.draw.circle(screen, WHITE, (sx + k, sy - 2), 1)

    elif t.kind == 'crystal':
        # Astral-Kristall (großer Diamant mit Glow)
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003 + sx * 0.01))
        glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow, (180, 140, 240, int(140 + pulse * 60)),
                            (20, 20), 18)
        screen.blit(glow, (sx - 20, sy - 20))
        crystal_pts = [
            (sx, sy - 14), (sx + 8, sy - 4), (sx + 6, sy + 10),
            (sx - 6, sy + 10), (sx - 8, sy - 4),
        ]
        pygame.draw.polygon(screen, (180, 140, 240), crystal_pts)
        pygame.draw.polygon(screen, BLACK, crystal_pts, 2)
        pygame.draw.polygon(screen, (240, 200, 255), [
            (sx, sy - 12), (sx + 4, sy - 4), (sx + 2, sy + 4),
        ])

    elif t.kind == 'lava_pool':
        # Glühende Lava-Pfütze
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.002 + sx * 0.01))
        sw = pygame.Surface((40, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(sw, (40, 15, 8), (0, 0, 40, 24))
        pygame.draw.ellipse(sw, (255, 120, 40, int(180 + pulse * 60)), (4, 3, 32, 18))
        pygame.draw.ellipse(sw, (255, 200, 100, int(180 + pulse * 60)), (10, 7, 20, 10))
        rot = pygame.transform.rotate(sw, math.degrees(t.rot))
        screen.blit(rot, (sx - rot.get_width() // 2, sy - rot.get_height() // 2))

    elif t.kind == 'salt_puddle':
        # Lore-Bibel 4.1 + Audio 7.7: Brassweir, halb-versunken, Salzpfützen.
        # Blass-blaue Pfütze mit Sparkle, deutet auf Salzwunde.
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.001 + sx * 0.01))
        sw = pygame.Surface((44, 26), pygame.SRCALPHA)
        pygame.draw.ellipse(sw, (40, 60, 90, 180), (0, 0, 44, 26))
        pygame.draw.ellipse(sw, (140, 180, 220, int(140 + pulse * 60)),
                            (4, 3, 36, 20))
        pygame.draw.ellipse(sw, (220, 240, 255, int(100 + pulse * 80)),
                            (12, 8, 18, 8))
        rot = pygame.transform.rotate(sw, math.degrees(t.rot))
        screen.blit(rot, (sx - rot.get_width() // 2,
                          sy - rot.get_height() // 2))
        # Salz-Sparkle (2 winzige Kreuze)
        if int(pygame.time.get_ticks() * 0.002 + sx) % 3 == 0:
            pygame.draw.line(screen, (240, 250, 255),
                             (sx - 8, sy - 2), (sx - 6, sy - 2), 1)
            pygame.draw.line(screen, (240, 250, 255),
                             (sx - 7, sy - 3), (sx - 7, sy - 1), 1)

    elif t.kind == 'pier_post':
        # Verfallener Hafen-Pfosten (zerbrochen, schräg, Salzkrusten).
        # Lore: Brassweir-Hafen, von der Salzwunde überspült.
        tilt = math.cos(t.rot) * 4
        # Schatten
        sh = pygame.Surface((20, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 120), (0, 0, 20, 12))
        screen.blit(sh, (sx - 10, sy + 6))
        # Pfosten
        post_pts = [
            (sx - 5 + tilt // 2, sy + 6),
            (sx + 5 + tilt // 2, sy + 6),
            (sx + 4 + tilt, sy - 20),
            (sx - 4 + tilt, sy - 20),
        ]
        pygame.draw.polygon(screen, (90, 60, 30), post_pts)
        pygame.draw.polygon(screen, BLACK, post_pts, 2)
        # Holzmaserung
        pygame.draw.line(screen, (60, 40, 18),
                         (sx + tilt // 2, sy + 4),
                         (sx + tilt, sy - 18), 1)
        # Splitter-Top (zerbrochen)
        top_pts = [(sx - 4 + tilt, sy - 20),
                   (sx + 4 + tilt, sy - 20),
                   (sx + 2 + tilt, sy - 26),
                   (sx - 2 + tilt, sy - 24)]
        pygame.draw.polygon(screen, (110, 75, 40), top_pts)
        pygame.draw.polygon(screen, BLACK, top_pts, 1)
        # Salzkruste am Fuß (weiß-blass)
        pygame.draw.line(screen, (220, 230, 240),
                         (sx - 6 + tilt // 2, sy + 4),
                         (sx + 6 + tilt // 2, sy + 4), 2)

    elif t.kind == 'fishing_net':
        # Hängendes Fischer-Netz (Trocknet am Pier).
        # Pfosten oben links/rechts
        pygame.draw.line(screen, (90, 60, 30),
                         (sx - 12, sy - 14), (sx - 12, sy + 8), 2)
        pygame.draw.line(screen, (90, 60, 30),
                         (sx + 12, sy - 14), (sx + 12, sy + 8), 2)
        # Querbalken
        pygame.draw.line(screen, (90, 60, 30),
                         (sx - 12, sy - 14), (sx + 12, sy - 14), 2)
        # Netz-Pattern
        net_col = (180, 170, 150)
        for gx in range(-10, 11, 4):
            pygame.draw.line(screen, net_col,
                             (sx + gx, sy - 12),
                             (sx + gx, sy + 4), 1)
        for gy in range(-12, 5, 4):
            pygame.draw.line(screen, net_col,
                             (sx - 10, sy + gy),
                             (sx + 10, sy + gy), 1)
        # Toter Fisch im Netz (klein, signature)
        pygame.draw.ellipse(screen, (200, 200, 180),
                            (sx - 3, sy - 4, 8, 4))

    elif t.kind == 'mahnmal_stele':
        # Mahnmal-Marke-Stele: schwarze Steinplatte mit Gold-Gravur.
        # Lore: Mahnmal-Gilde-Signature, eine Mark pro vergessenem Ort.
        # Schatten
        sh = pygame.Surface((28, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 140), (0, 0, 28, 10))
        screen.blit(sh, (sx - 14, sy + 8))
        # Sockel
        pygame.draw.rect(screen, (40, 36, 30), (sx - 10, sy + 4, 20, 6))
        pygame.draw.rect(screen, BLACK, (sx - 10, sy + 4, 20, 6), 2)
        # Stele (vertikal, dunkelgrau)
        pygame.draw.rect(screen, (28, 24, 22), (sx - 7, sy - 22, 14, 28))
        pygame.draw.rect(screen, BLACK, (sx - 7, sy - 22, 14, 28), 2)
        # Gold-Gravur (Linien + 7 Punkte für die 7 Aspekte)
        for i in range(7):
            py = sy - 19 + i * 4
            pygame.draw.line(screen, GOLD,
                             (sx - 5, py), (sx + 5, py), 1)
        # Zentraler Punkt (Salzwunde-Marker)
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.002))
        pygame.draw.circle(screen, (255, 220, 120),
                           (sx, sy - 8), 2 + int(pulse))

    elif t.kind == 'gravestone':
        # Salzgekreuzter-Grab: bemooste Stele mit Riss.
        # Lore: Marrowport, vom Vergessen erfasst — jede Stele ist ein Fischer.
        # Schatten
        sh = pygame.Surface((22, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 120), (0, 0, 22, 8))
        screen.blit(sh, (sx - 11, sy + 6))
        # Bogen-Form (klassisches Grabstein-Silhouette)
        stone_col = (90, 84, 76) if biome != 'frost' else (130, 150, 180)
        crack_col = (40, 36, 30)
        pygame.draw.rect(screen, stone_col, (sx - 8, sy - 4, 16, 12))
        pygame.draw.circle(screen, stone_col, (sx, sy - 4), 8)
        pygame.draw.rect(screen, BLACK, (sx - 8, sy - 4, 16, 12), 1)
        pygame.draw.arc(screen, BLACK, (sx - 8, sy - 12, 16, 16),
                        0, math.pi, 1)
        # Riss von oben nach unten
        pygame.draw.line(screen, crack_col,
                         (sx - 1, sy - 10), (sx + 2, sy + 5), 1)
        # Eingravierte Linien (Name unleserlich)
        for dy in (sy - 1, sy + 2, sy + 5):
            pygame.draw.line(screen, crack_col,
                             (sx - 5, dy), (sx + 5, dy), 1)
        # Moos / Salz-Patina (biome-dependent)
        moss = (90, 130, 70) if biome in ('crypt', 'swamp') else (180, 200, 220)
        pygame.draw.circle(screen, moss, (sx - 5, sy + 2), 2)
        pygame.draw.circle(screen, moss, (sx + 4, sy - 1), 1)

    elif t.kind == 'salt_crystal':
        # Salz-Kristall-Cluster (Akt 1 — Salzküste).
        # Pulsiert leicht.
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.0015 + sx * 0.01))
        glow = pygame.Surface((30, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (180, 210, 240, int(80 + pulse * 50)),
                            (0, 0, 30, 24))
        screen.blit(glow, (sx - 15, sy - 8))
        # Drei Kristalle in Reihe (steigende Größe)
        for i, (dx, h) in enumerate(((-6, -8), (0, -12), (5, -7))):
            pts = [(sx + dx, sy + 4),
                   (sx + dx - 3, sy),
                   (sx + dx, sy + h),
                   (sx + dx + 3, sy)]
            pygame.draw.polygon(screen, (200, 220, 240), pts)
            pygame.draw.polygon(screen, BLACK, pts, 1)
            # Highlight
            pygame.draw.line(screen, (255, 255, 255),
                             (sx + dx - 1, sy), (sx + dx + 1, sy + h + 2), 1)

    elif t.kind == 'town_wall':
        # Stadt-Wall-Segment (Stein-Block, modular für Mauerring).
        # `size` skaliert die Länge; `rot=0` ist horizontal-ost-west.
        # Schatten
        L = max(20, int(t.size))
        H = 14
        sh = pygame.Surface((L + 6, H + 6), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 140), (3, 3, L, H))
        if math.cos(t.rot * 2) > 0.5:
            # horizontal
            screen.blit(sh, (sx - L // 2, sy + 4))
            pygame.draw.rect(screen, (84, 76, 64),
                             (sx - L // 2, sy - H // 2, L, H))
            pygame.draw.rect(screen, BLACK,
                             (sx - L // 2, sy - H // 2, L, H), 2)
            # Stein-Blocks (3-4 Segmente)
            seg = L // 4
            for k in range(1, 4):
                pygame.draw.line(screen, (40, 34, 28),
                                 (sx - L // 2 + k * seg, sy - H // 2),
                                 (sx - L // 2 + k * seg, sy + H // 2), 1)
            # Top-Highlight
            pygame.draw.line(screen, (130, 120, 100),
                             (sx - L // 2, sy - H // 2),
                             (sx + L // 2, sy - H // 2), 2)
        else:
            # vertikal
            screen.blit(sh, (sx - H // 2, sy - L // 2))
            pygame.draw.rect(screen, (84, 76, 64),
                             (sx - H // 2, sy - L // 2, H, L))
            pygame.draw.rect(screen, BLACK,
                             (sx - H // 2, sy - L // 2, H, L), 2)
            seg = L // 4
            for k in range(1, 4):
                pygame.draw.line(screen, (40, 34, 28),
                                 (sx - H // 2, sy - L // 2 + k * seg),
                                 (sx + H // 2, sy - L // 2 + k * seg), 1)
            pygame.draw.line(screen, (130, 120, 100),
                             (sx - H // 2, sy - L // 2),
                             (sx - H // 2, sy + L // 2), 2)

    elif t.kind == 'anvil':
        # Schmiede-Amboss (Otreth-Werkstatt-Signature).
        # Schatten
        sh = pygame.Surface((24, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 140), (0, 0, 24, 10))
        screen.blit(sh, (sx - 12, sy + 6))
        # Sockel-Block
        pygame.draw.rect(screen, (50, 40, 30), (sx - 8, sy + 2, 16, 8))
        pygame.draw.rect(screen, BLACK, (sx - 8, sy + 2, 16, 8), 2)
        # Amboss-Körper (T-Form)
        pygame.draw.rect(screen, (60, 56, 52), (sx - 5, sy - 4, 10, 6))
        pygame.draw.rect(screen, BLACK, (sx - 5, sy - 4, 10, 6), 1)
        pygame.draw.rect(screen, (70, 66, 60), (sx - 10, sy - 8, 20, 4))
        pygame.draw.rect(screen, BLACK, (sx - 10, sy - 8, 20, 4), 1)
        # Glüh-Punkt (Otreth-Hohlauge bei der Arbeit — kleiner Rest-Glow)
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.004))
        pygame.draw.circle(screen, (255, 140, 60),
                           (sx + 6, sy - 6), 1 + int(pulse * 2))

    elif t.kind == 'cursed_altar':
        # Steinerner Altar mit pulsierender Aspekt-Farbe.
        # Update #27: Dungeon-Event-Altäre (4 Varianten, Idx in t.altar_idx).
        used = getattr(t, 'altar_used', False)
        idx = getattr(t, 'altar_idx', 0)
        ASPEKT_COL = [(220, 160, 80), (255, 215, 100),
                       (180, 200, 220), (140, 80, 200)]
        col = ASPEKT_COL[idx % len(ASPEKT_COL)] if not used else (90, 80, 60)
        # Schatten
        sh = pygame.Surface((50, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 180), (0, 0, 50, 16))
        screen.blit(sh, (sx - 25, sy + 12))
        # Steinsockel
        pygame.draw.rect(screen, (60, 50, 40), (sx - 16, sy - 4, 32, 16))
        pygame.draw.rect(screen, BLACK, (sx - 16, sy - 4, 32, 16), 2)
        # Oberer Stein (Mahnmal-Top)
        pygame.draw.rect(screen, (90, 76, 60), (sx - 12, sy - 14, 24, 12))
        pygame.draw.rect(screen, BLACK, (sx - 12, sy - 14, 24, 12), 1)
        # Aspekt-Symbol (oben, pulsierend wenn nicht used)
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003))
        if not used:
            glow = pygame.Surface((40, 30), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (*col, int(80 + 80 * pulse)),
                                 (0, 0, 40, 30))
            screen.blit(glow, (sx - 20, sy - 22))
        # Aspekt-Glyph
        pygame.draw.polygon(screen, col,
            [(sx, sy - 18), (sx + 5, sy - 11), (sx, sy - 4),
             (sx - 5, sy - 11)])
        pygame.draw.polygon(screen, BLACK,
            [(sx, sy - 18), (sx + 5, sy - 11), (sx, sy - 4),
             (sx - 5, sy - 11)], 1)
        if used:
            # „×"-Marker (Altar aufgebraucht)
            pygame.draw.line(screen, (140, 100, 80),
                              (sx - 8, sy - 14), (sx + 8, sy - 2), 2)
            pygame.draw.line(screen, (140, 100, 80),
                              (sx - 8, sy - 2), (sx + 8, sy - 14), 2)

    elif t.kind == 'rune_anchor':
        # Unsichtbarer Anchor — die Runen drumherum sind separate Decor.
        # Wenn rune_active: stärkerer Glow. Sonst subtile Boden-Markierung.
        active = getattr(t, 'rune_active', False)
        rune_t = getattr(t, 'rune_t', 0.0)
        prog = min(1.0, rune_t / 2.0)
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.004))
        # Boden-Glow-Pad
        size = 60
        glow = pygame.Surface((size, size), pygame.SRCALPHA)
        if active:
            col = (180, 140, 240, int(120 + 80 * pulse))
        elif prog > 0:
            col = (220, 180, 110, int(80 + 100 * prog))
        else:
            col = (140, 110, 70, int(40 + 40 * pulse))
        pygame.draw.circle(glow, col, (size // 2, size // 2), size // 2 - 2)
        screen.blit(glow, (sx - size // 2, sy - size // 2))
        # Mittel-Rune (Pentagramm-Stil)
        for k in range(5):
            a = -math.pi / 2 + k * (2 * math.pi / 5)
            xx = sx + int(math.cos(a) * 12)
            yy = sy + int(math.sin(a) * 12)
            pygame.draw.line(screen, (220, 180, 110), (sx, sy), (xx, yy), 1)

    elif t.kind == 'salt_statue':
        # Salzhüter-Statue (Boss-Decor): korrupterte Aspekt-Statue,
        # mit Salz überzogen, zwei rote Kristall-Augen.
        # Schatten
        sh = pygame.Surface((50, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 180), (0, 0, 50, 16))
        screen.blit(sh, (sx - 25, sy + 14))
        # Sockel
        pygame.draw.rect(screen, (60, 56, 50), (sx - 18, sy + 10, 36, 8))
        pygame.draw.rect(screen, BLACK, (sx - 18, sy + 10, 36, 8), 2)
        # Körper (große Säulen-Statue)
        pygame.draw.rect(screen, (180, 200, 220), (sx - 10, sy - 14, 20, 26))
        pygame.draw.rect(screen, BLACK, (sx - 10, sy - 14, 20, 26), 2)
        # Salzkruste (helle Flecken)
        pygame.draw.circle(screen, (240, 245, 255), (sx - 5, sy - 5), 3)
        pygame.draw.circle(screen, (240, 245, 255), (sx + 4, sy + 4), 2)
        pygame.draw.circle(screen, (240, 245, 255), (sx, sy + 8), 2)
        # Kopf
        pygame.draw.circle(screen, (200, 220, 235), (sx, sy - 20), 7)
        pygame.draw.circle(screen, BLACK, (sx, sy - 20), 7, 2)
        # Rote Kristall-Augen
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003))
        eye_col = (220, 60, 60)
        glow = pygame.Surface((20, 12), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*eye_col, int(120 + pulse * 100)),
                           (10, 6), 5)
        screen.blit(glow, (sx - 10, sy - 24))
        pygame.draw.circle(screen, eye_col, (sx - 2, sy - 21), 1)
        pygame.draw.circle(screen, eye_col, (sx + 2, sy - 21), 1)

    elif t.kind == 'underworld_rift':
        # Update #44: Unterwelt-Riss — pulsierender lila-schwarzer Bodenriss.
        # Vor Berührung: glüht intensiv und animiert. Nach Trigger („rift_used"):
        # verblasst zu kalter Asche.
        used = getattr(t, 'rift_used', False)
        ticks = pygame.time.get_ticks()
        # Boden-Schatten (Riss-Außenkontur)
        sh_w, sh_h = 96, 48
        sh = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 200), (0, 0, sh_w, sh_h))
        screen.blit(sh, (sx - sh_w // 2, sy - sh_h // 2))
        if used:
            # Ausgebrannt: graue Asche-Spur
            pygame.draw.ellipse(screen, (60, 50, 60),
                                 (sx - 30, sy - 12, 60, 24))
            pygame.draw.ellipse(screen, (40, 30, 40),
                                 (sx - 30, sy - 12, 60, 24), 2)
            # Asche-Punkte
            for k in range(5):
                a = (k / 5) * math.tau + ticks * 0.0001
                px = sx + int(math.cos(a) * 20)
                py = sy + int(math.sin(a) * 10)
                pygame.draw.circle(screen, (90, 80, 90), (px, py), 1)
        else:
            # Aktiv: pulsierender Riss mit Lila-Glow + Innerer Vortex
            pulse = abs(math.sin(ticks * 0.003))
            glow_a = int(120 + 100 * pulse)
            # 3 äußere Schichten (Lila Halo)
            for i in range(3, 0, -1):
                a = int(40 + 50 * pulse) // i
                g = pygame.Surface((80 + i * 20, 40 + i * 10),
                                    pygame.SRCALPHA)
                pygame.draw.ellipse(g, (180, 80, 220, a),
                                     (0, 0, 80 + i * 20, 40 + i * 10))
                screen.blit(g, (sx - (80 + i * 20) // 2,
                                sy - (40 + i * 10) // 2))
            # Riss-Körper (dunkelviolett)
            pygame.draw.ellipse(screen, (40, 10, 60),
                                 (sx - 32, sy - 14, 64, 28))
            pygame.draw.ellipse(screen, (60, 20, 90),
                                 (sx - 32, sy - 14, 64, 28), 2)
            # Innerer Vortex (rotierend)
            for i in range(5):
                a = ticks * 0.004 + i * 1.2566  # 2π/5
                rad = 18 - i * 2
                px = sx + int(math.cos(a) * rad)
                py = sy + int(math.sin(a) * rad * 0.5)
                col = (220, 150, 255, glow_a) if i % 2 == 0 \
                       else (255, 200, 255, glow_a)
                spark = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(spark, col, (3, 3), 3)
                screen.blit(spark, (px - 3, py - 3))
            # Zentrum: helles Auge
            pygame.draw.circle(screen, (255, 220, 255),
                                (sx, sy), 3)
            pygame.draw.circle(screen, (180, 80, 220),
                                (sx, sy), 3, 1)


# ============================================================
# MINI-MAP
# ============================================================
class FogOfWar:
    """B-14 (Update #50): Service-Wrapper über das pro-Grid `discovered`-Set.

    Bisher inline in `draw_minimap` gepflegt — der Service kapselt jetzt
    Reveal-Logik + Edge-Fade-Calculation in einer testbaren Abstraktion.
    Wird auf-the-fly an die Grid-Instanz gehängt (`grid._fog_service`)
    damit Map-Seed-Wechsel automatisch frische Fog liefert.
    """
    __slots__ = ('grid', 'discovered')

    def __init__(self, grid):
        self.grid = grid
        self.discovered = getattr(grid, '_minimap_discovered', None)
        if self.discovered is None:
            self.discovered = set()
            grid._minimap_discovered = self.discovered

    def reveal_around(self, world_x, world_y, radius_cells):
        """Deckt alle Cells im Radius (in Cells) auf, die in_bounds sind."""
        pcx, pcy = self.grid.world_to_cell(world_x, world_y)
        r2 = radius_cells * radius_cells
        for dy in range(-radius_cells, radius_cells + 1):
            for dx in range(-radius_cells, radius_cells + 1):
                if dx * dx + dy * dy > r2:
                    continue
                tx, ty = pcx + dx, pcy + dy
                if self.grid.in_bounds(tx, ty):
                    self.discovered.add((tx, ty))

    def is_discovered(self, cx, cy):
        return (cx, cy) in self.discovered

    def edge_fade(self, cx, cy):
        """Returnt Alpha-Faktor (0.5..1.0) basierend auf Anzahl undecovered
        Nachbarn — für Edge-Gradient (PLAN B-04).
        """
        undisc = sum(1 for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1))
                     if (cx + ox, cy + oy) not in self.discovered)
        return max(0.5, 1.0 - undisc * 0.15)

    def __iter__(self):
        return iter(self.discovered)

    def __len__(self):
        return len(self.discovered)


def get_fog_service(grid):
    """Lazy-Factory: erstellt/cached ein `FogOfWar` pro Grid."""
    if grid is None:
        return None
    service = getattr(grid, '_fog_service', None)
    if service is None or service.grid is not grid:
        service = FogOfWar(grid)
        grid._fog_service = service
    return service


def _resolve_quest_target_pos(game):
    """Update #88: Liefert die Welt-Position der aktuellen Quest-Stage,
    soweit eindeutig auflösbar. Returns (x, y) tuple oder None.

    Unterstützt:
      - target['npc_name'] (Town): Position des passenden NPCs
      - target['biome']    (Town): Position des passenden Dungeon-Portals
      - target['boss_room'] (Dungeon): Boss-Room-Center via grid.rooms[-1]

    Update #160 (ROADMAP T2.3-C): Wenn `quest_log.tracked_quest_id`
    gesetzt ist, hat diese Quest Priorität — der Compass zeigt auf das
    Pinned-Ziel statt auf die erste Quest in iteration order.
    """
    log = getattr(game, 'quest_log', None)
    if log is None:
        return None
    active = getattr(log, 'active', None) or {}
    # active is a dict {qid: QuestState}; iterate values
    if isinstance(active, dict):
        states = list(active.values())
    else:
        states = list(active)
    # Update #160: Pinned-Quest zuerst, falls vorhanden
    tracked_qid = getattr(log, 'tracked_quest_id', None)
    if tracked_qid and isinstance(active, dict) and tracked_qid in active:
        tracked = active[tracked_qid]
        # Move tracked to front of states list
        states = [tracked] + [s for s in states if s is not tracked]
    for qstate in states:
        st = qstate.stage
        if st is None:
            continue
        target = st.get('target') or {}
        # NPC-Target
        npc_name = target.get('npc_name')
        if npc_name and game.area == 'town':
            for npc in getattr(game, 'npcs', ()):
                if npc.name == npc_name:
                    return (npc.pos.x, npc.pos.y)
        # Biome-Target → Dungeon-Portal in Town
        biome = target.get('biome')
        if biome and game.area == 'town':
            for dp in getattr(game, 'dungeon_portals', ()):
                if getattr(dp, 'biome', None) == biome:
                    return (dp.pos.x, dp.pos.y)
        # Boss-Room → Center des letzten Raums
        if target.get('boss_room') and game.area == 'dungeon':
            grid = getattr(game, 'grid', None)
            if grid is not None and getattr(grid, 'rooms', None):
                room = grid.rooms[-1]
                cx_g = room.x + room.w // 2
                cy_g = room.y + room.h // 2
                wx, wy = grid.cell_to_world_center(cx_g, cy_g)
                return (wx, wy)
    return None


def draw_minimap(screen, game, font_small):
    """Mini-Map rechts oben — PLAN B-Block (Briefing Teil B).

    Funktionen:
      - 256×256 (Briefing-Vorgabe ≥250)
      - Grid-Tiles als Walls/Walkable für Dungeons (B-01/B-02)
      - Fog of War mit Discovered-Tile-Set pro Map-Seed (B-03)
      - POI-Icons in fester Farb-Codierung (B-06)
      - Klassen-themed Rahmen-Farbe (Lore-Anker `quotes.CLASS_FACTION`)
      - Region-Label „Akt N — <Region>" oben unter dem Rahmen
    """
    mm_w, mm_h = 256, 256
    mm_x = SCREEN_W - mm_w - 18
    mm_y = 70
    mm_scale = 0.06

    surf = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
    # Sehr dunkles Basis-Fog (alles unentdeckt = nahezu schwarz)
    surf.fill((6, 4, 3, 220))
    cx, cy = mm_w // 2, mm_h // 2

    p = game.player
    biome_color = BIOMES[game.biome]['ground']

    # --------------------------------------------------------------
    # PLAN B-01/B-02/B-03: Dungeon-Grid mit Fog of War
    # --------------------------------------------------------------
    grid = getattr(game, 'grid', None)
    discovered = None
    fog = None
    if grid is not None:
        # B-14 (Update #50): FogOfWar-Service-Abstraktion.
        fog = get_fog_service(grid)
        discovered = fog.discovered

        # B-05 (Update #50): `light_radius`-Item-Stat addiert auf Default-5.
        from .dungeon_gen import FLOOR, DOOR, TRAP, SECRET
        WALKABLE = (FLOOR, DOOR, TRAP, SECRET)
        try:
            from . import progression as _prog
            light_bonus = int(_prog.effective(p).get('light_radius', 0))
        except Exception:
            light_bonus = 0
        fog.reveal_around(p.pos.x, p.pos.y, 5 + light_bonus)

        # Skala in „Cells pro Minimap-Pixel".
        cell_px = grid.cell  # 80
        tile_size_mm = max(1, int(cell_px * mm_scale))  # ~5 px pro Cell

        # PLAN B-04: Edge-Gradient — Tile-Alpha fällt zu unentdeckten Cells.
        # Tile mit ≥1 unentdeckter Nachbar-Cell bekommt reduzierten Alpha.
        for (tx, ty) in discovered:
            wx, wy = grid.cell_to_world_center(tx, ty)
            rx = int((wx - p.pos.x) * mm_scale + cx - tile_size_mm // 2)
            ry = int((wy - p.pos.y) * mm_scale + cy - tile_size_mm // 2)
            if rx < -tile_size_mm or ry < -tile_size_mm \
                    or rx >= mm_w or ry >= mm_h:
                continue
            # Edge-Fade aus Service (B-14)
            fade = fog.edge_fade(tx, ty)
            t = grid.get(tx, ty)
            if t in WALKABLE:
                col = (*biome_color, int(200 * fade))
            else:
                col = (12, 8, 6, int(220 * fade))
            pygame.draw.rect(surf, col, (rx, ry, tile_size_mm, tile_size_mm))
    else:
        # Offene Welt (Town/Outpost) — pauschaler Boden-Tint
        pygame.draw.rect(surf, (*biome_color, 80),
                         (2, 2, mm_w - 4, mm_h - 4))

    # --------------------------------------------------------------
    # PLAN B-06: POI-Icons (NPCs / Portale / Boss / Loot)
    # --------------------------------------------------------------
    def _in_view(rx, ry):
        return 2 < rx < mm_w - 2 and 2 < ry < mm_h - 2

    # Gegner (rot/orange/gold je Tier)
    # Update #42: Boss IMMER auf der Minimap (POE2-Style). Wenn off-view,
    # wird das Symbol an den Rand geklemmt + pulsiert sanft, damit der
    # Spieler weiß, in welche Richtung der Boss liegt.
    explored_enough = (discovered is not None and len(discovered) >= 18)
    import time as _t
    _puls = 0.7 + 0.3 * abs(math.sin(_t.time() * 2.4))
    boss_drawn = False
    for e in game.enemies:
        rx = (e.pos.x - p.pos.x) * mm_scale + cx
        ry = (e.pos.y - p.pos.y) * mm_scale + cy
        if e.is_boss and explored_enough and not e.dying:
            # Position auf Minimap clampen — Boss-Marker bleibt immer sichtbar
            cl_rx = max(8, min(mm_w - 8, rx))
            cl_ry = max(8, min(mm_h - 8, ry))
            off_view = (cl_rx != rx) or (cl_ry != ry)
            # Pulsierender Boss-Skull mit weißem Outline
            r_outer = 7 if off_view else 6
            r_inner = 5 if off_view else 5
            pul_col = (int(255 * _puls), int(60 * _puls), int(60 * _puls))
            pygame.draw.circle(surf, pul_col,
                               (int(cl_rx), int(cl_ry)), r_outer)
            pygame.draw.circle(surf, (255, 220, 220),
                               (int(cl_rx), int(cl_ry)), r_inner, 1)
            # Mini-Schädel-Andeutung: 2 Punkte = Augen, 1 = Kiefer
            pygame.draw.circle(surf, (10, 8, 6),
                               (int(cl_rx) - 2, int(cl_ry) - 1), 1)
            pygame.draw.circle(surf, (10, 8, 6),
                               (int(cl_rx) + 2, int(cl_ry) - 1), 1)
            pygame.draw.rect(surf, (10, 8, 6),
                             (int(cl_rx) - 1, int(cl_ry) + 1, 3, 1))
            # Richtungs-Pfeil wenn off-view
            if off_view:
                diff_bx = e.pos.x - p.pos.x
                diff_by = e.pos.y - p.pos.y
                bd = math.hypot(diff_bx, diff_by)
                if bd > 1:
                    nbx, nby = diff_bx / bd, diff_by / bd
                    tip_x = cl_rx + nbx * 8
                    tip_y = cl_ry + nby * 8
                    pygame.draw.polygon(surf, (255, 200, 80), [
                        (tip_x, tip_y),
                        (cl_rx - nby * 4, cl_ry + nbx * 4),
                        (cl_rx + nby * 4, cl_ry - nbx * 4),
                    ])
            boss_drawn = True
            continue
        if _in_view(rx, ry):
            if e.is_boss:
                # Boss = großer roter Totenkopf-Kreis (Fallback wenn nicht explored)
                pygame.draw.circle(surf, (255, 80, 80),
                                   (int(rx), int(ry)), 5)
                pygame.draw.circle(surf, (255, 255, 255),
                                   (int(rx), int(ry)), 5, 1)
            elif e.elite:
                pygame.draw.circle(surf, (255, 160, 80),
                                   (int(rx), int(ry)), 3)
            else:
                pygame.draw.circle(surf, (200, 80, 80),
                                   (int(rx), int(ry)), 2)

    # Loot (Gold-/Item-/Gem-Punkt) — Update #131 (B-17): Rarity-Glow-Blink
    # für seltenes Loot (rare/unique/set), statisch für gewöhnliches.
    # Rare/Unique-Items blinken zusätzlich mit hellem Outline-Ring.
    _loot_t = pygame.time.get_ticks() * 0.006
    _loot_blink = 0.5 + 0.5 * abs(math.sin(_loot_t))
    for l in game.loot:
        rx = (l.pos.x - p.pos.x) * mm_scale + cx
        ry = (l.pos.y - p.pos.y) * mm_scale + cy
        if not _in_view(rx, ry):
            continue
        # Rarity-Heuristik: l.color hellgelb (255,220,80) = rare,
        # orange (255,140,40) = unique — diese blinken.
        col = l.color
        is_rare = (col[0] > 200 and col[1] > 180
                   and col[2] < 130)
        is_unique = (col[0] > 220 and col[1] < 180
                     and col[2] < 100)
        if is_unique or is_rare:
            # Pulsierender Outline-Ring um den Loot-Dot
            ring_alpha = int(160 + 80 * _loot_blink)
            ring_col = (col[0], col[1], col[2], ring_alpha)
            ring_r = 4 + int(_loot_blink * 1.5)
            ring_surf = pygame.Surface(
                (ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, ring_col,
                                (ring_r + 2, ring_r + 2),
                                ring_r, 1)
            surf.blit(ring_surf, (int(rx) - ring_r - 2,
                                    int(ry) - ring_r - 2))
        pygame.draw.circle(surf, col, (int(rx), int(ry)), 2)

    # Town-NPCs (verschiedene Symbole pro Rolle)
    NPC_ICONS = {
        'vendor':    ((255, 255, 220), 'square'),    # Markt
        'stash':     ((180, 140, 90),  'square'),    # Truhe
        'mystic':    ((200, 130, 240), 'diamond'),   # Mystik
        'smith':     ((200, 200, 200), 'cross'),     # Werkstatt
        'quest':     ((255, 220,  80), 'star'),      # Quest-Geber
        'innkeeper': ((255, 180, 100), 'circle'),    # Wirt
    }
    for npc in getattr(game, 'npcs', ()):
        rx = (npc.pos.x - p.pos.x) * mm_scale + cx
        ry = (npc.pos.y - p.pos.y) * mm_scale + cy
        if not _in_view(rx, ry):
            continue
        col, shape = NPC_ICONS.get(npc.kind, ((255, 255, 255), 'square'))
        ix, iy = int(rx), int(ry)
        if shape == 'square':
            pygame.draw.rect(surf, col, (ix - 3, iy - 3, 6, 6))
            pygame.draw.rect(surf, (10, 8, 6), (ix - 3, iy - 3, 6, 6), 1)
        elif shape == 'diamond':
            pygame.draw.polygon(surf, col,
                [(ix, iy - 4), (ix + 4, iy), (ix, iy + 4), (ix - 4, iy)])
        elif shape == 'cross':
            pygame.draw.line(surf, col, (ix - 4, iy), (ix + 4, iy), 2)
            pygame.draw.line(surf, col, (ix, iy - 4), (ix, iy + 4), 2)
        elif shape == 'star':
            pygame.draw.circle(surf, col, (ix, iy), 4)
            pygame.draw.circle(surf, (10, 8, 6), (ix, iy), 4, 1)
        else:
            pygame.draw.circle(surf, col, (ix, iy), 3)

    # Dungeon-Portale (in Town): Tür-Symbol
    for dp in getattr(game, 'dungeon_portals', ()):
        rx = (dp.pos.x - p.pos.x) * mm_scale + cx
        ry = (dp.pos.y - p.pos.y) * mm_scale + cy
        if _in_view(rx, ry):
            pygame.draw.rect(surf, (140, 200, 240),
                             (int(rx) - 3, int(ry) - 4, 6, 8))
            pygame.draw.rect(surf, (220, 240, 255),
                             (int(rx) - 3, int(ry) - 4, 6, 8), 1)

    # Update #121: Survival-Portal-Marker auf der Minimap entfernt
    # (Endlos-Modus existiert nicht mehr).

    # In-World-Portale (z.B. zurück zur Stadt aus einem Dungeon)
    for portal in getattr(game, 'portals', ()):
        rx = (portal.pos.x - p.pos.x) * mm_scale + cx
        ry = (portal.pos.y - p.pos.y) * mm_scale + cy
        if _in_view(rx, ry):
            pygame.draw.circle(surf, BIOMES[portal.biome]['accent'],
                               (int(rx), int(ry)), 5, 2)

    # Update #85 B-15: Dungeon-POI-Marker für unbenutzte Altäre, ungelesene
    # Lore-Tafeln und Rune-Circles — nur wenn explored_enough (verhindert
    # Spoiler vor Erkundung) und im Dungeon-Modus.
    if game.area == 'dungeon' and explored_enough:
        for t in getattr(game, 'tiles', ()):
            tkind = getattr(t, 'kind', None)
            if tkind not in ('cursed_altar', 'lore_tablet', 'rune_circle'):
                continue
            # Schon konsumierte POIs ausblenden
            if tkind == 'cursed_altar' and getattr(t, 'altar_used', False):
                continue
            if tkind == 'lore_tablet' and getattr(t, 'lore_read', False):
                continue
            if tkind == 'rune_circle' and getattr(t, 'rune_active', False):
                continue
            rx = (t.x - p.pos.x) * mm_scale + cx
            ry = (t.y - p.pos.y) * mm_scale + cy
            if not _in_view(rx, ry):
                continue
            ix, iy = int(rx), int(ry)
            if tkind == 'cursed_altar':
                # Goldenes Pentagramm-Quadrat (Altar-Symbol)
                pygame.draw.rect(surf, (240, 200, 100),
                                  (ix - 3, iy - 3, 6, 6))
                pygame.draw.rect(surf, (60, 40, 14),
                                  (ix - 3, iy - 3, 6, 6), 1)
                pygame.draw.line(surf, (60, 40, 14),
                                  (ix - 3, iy - 3), (ix + 3, iy + 3), 1)
            elif tkind == 'lore_tablet':
                # Cremefarbenes Buch-Symbol (Tablet)
                pygame.draw.rect(surf, (220, 200, 160),
                                  (ix - 3, iy - 4, 6, 8))
                pygame.draw.line(surf, (80, 60, 30),
                                  (ix, iy - 4), (ix, iy + 4), 1)
            elif tkind == 'rune_circle':
                # Magisches Rune-Symbol — lila Ring + Punkt
                pygame.draw.circle(surf, (170, 120, 240), (ix, iy), 4, 1)
                pygame.draw.circle(surf, (220, 180, 255), (ix, iy), 1)

    # Update #88: Quest-Compass-Marker — goldener Stern + Edge-Arrow auf
    # die aktuelle Quest-Stage-Ziel-Position.  Resolved aus quest_log.
    qpos = _resolve_quest_target_pos(game)
    if qpos is not None:
        qrx = (qpos[0] - p.pos.x) * mm_scale + cx
        qry = (qpos[1] - p.pos.y) * mm_scale + cy
        in_view = _in_view(qrx, qry)
        if in_view:
            # Update #131 (B-17): Quest-Stern rotiert jetzt langsam (0.5 Hz)
            # zusätzlich zum Pulse. Macht die Quest-Position auf der
            # Minimap deutlich auffälliger als ein statischer Stern.
            _qt = pygame.time.get_ticks() * 0.005
            _qp = 0.6 + 0.4 * math.sin(_qt)
            _q_rot = pygame.time.get_ticks() * 0.001  # 0.5 Hz Rotation
            star_col = (int(255 * _qp), int(220 * _qp), 100)
            iqx, iqy = int(qrx), int(qry)
            pygame.draw.circle(surf, star_col, (iqx, iqy), 6)
            pygame.draw.circle(surf, (255, 255, 255), (iqx, iqy), 6, 1)
            # Rotierende Stern-Strahlen (4-Spitzen + 4 kürzere Zwischen-
            # Spitzen für 8-strahligen Effekt)
            for k in range(4):
                ang = _q_rot + math.pi * k / 2
                ex = iqx + int(math.cos(ang) * 9)
                ey = iqy + int(math.sin(ang) * 9)
                pygame.draw.line(surf, star_col, (iqx, iqy), (ex, ey), 1)
            # 4 kürzere Strahlen zwischen den Haupt-Strahlen
            for k in range(4):
                ang = _q_rot + math.pi * k / 2 + math.pi / 4
                ex = iqx + int(math.cos(ang) * 6)
                ey = iqy + int(math.sin(ang) * 6)
                pygame.draw.line(surf, (255, 255, 200),
                                  (iqx, iqy), (ex, ey), 1)
        else:
            # Edge-Arrow zum Ziel
            dx_q = qpos[0] - p.pos.x
            dy_q = qpos[1] - p.pos.y
            qd = math.hypot(dx_q, dy_q)
            if qd > 1:
                nqx, nqy = dx_q / qd, dy_q / qd
                # Schnittpunkt mit Minimap-Border (Padding 12 px)
                pad = 12
                # Scale so dass max(|x|, |y|) = mm_dim/2 - pad
                bound_x = mm_w / 2 - pad
                bound_y = mm_h / 2 - pad
                scale = min(bound_x / max(0.001, abs(nqx)),
                             bound_y / max(0.001, abs(nqy)))
                ex = cx + nqx * scale
                ey = cy + nqy * scale
                # Pfeil-Polygon
                tip = (ex + nqx * 6, ey + nqy * 6)
                base_l = (ex - nqy * 5, ey + nqx * 5)
                base_r = (ex + nqy * 5, ey - nqx * 5)
                pygame.draw.polygon(surf, (255, 220, 100),
                                     [tip, base_l, base_r])
                pygame.draw.polygon(surf, (60, 40, 14),
                                     [tip, base_l, base_r], 1)

    # B-13 (Update #49): Compass-Strip — Himmelsrichtungs-Marker am
    # Minimap-Rand. Velgrad ist nord-fixiert (B-12 Default), also bleiben
    # die Positionen statisch: N oben, S unten, W links, O rechts.
    compass_marks = [
        ('N', cx, 8,            (255, 240, 180)),
        ('S', cx, mm_h - 8,     (200, 180, 140)),
        ('W', 8,  cy,           (200, 180, 140)),
        ('O', mm_w - 8, cy,     (200, 180, 140)),
    ]
    for label, lx, ly, lcol in compass_marks:
        # Notch-Linie
        if label == 'N':
            pygame.draw.line(surf, lcol, (lx, 2), (lx, 12), 2)
        elif label == 'S':
            pygame.draw.line(surf, lcol, (lx, mm_h - 12), (lx, mm_h - 2), 2)
        elif label == 'W':
            pygame.draw.line(surf, lcol, (2, ly), (12, ly), 2)
        else:
            pygame.draw.line(surf, lcol, (mm_w - 12, ly),
                              (mm_w - 2, ly), 2)
        ts = font_small.render(label, True, lcol)
        # Label-Position knapp neben Notch
        if label == 'N':
            surf.blit(ts, (lx - ts.get_width() // 2, 14))
        elif label == 'S':
            surf.blit(ts, (lx - ts.get_width() // 2,
                            mm_h - 14 - ts.get_height()))
        elif label == 'W':
            surf.blit(ts, (14, ly - ts.get_height() // 2))
        else:
            surf.blit(ts, (mm_w - 14 - ts.get_width(),
                            ly - ts.get_height() // 2))

    # B-07 (Update #49): Breadcrumb-Trail — letzte Spieler-Positionen als
    # fadende Punkte VOR dem Player-Marker rendern.
    breadcrumbs = getattr(game, 'breadcrumbs', None)
    if breadcrumbs:
        for (bx, by, age) in breadcrumbs:
            rx = (bx - p.pos.x) * mm_scale + cx
            ry = (by - p.pos.y) * mm_scale + cy
            if not (2 < rx < mm_w - 2 and 2 < ry < mm_h - 2):
                continue
            # Alpha-Fade über 30 s
            alpha = max(0, int(170 * (1.0 - age / 30.0)))
            if alpha < 12:
                continue
            crumb = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(crumb, (255, 200, 80, alpha), (2, 2), 2)
            surf.blit(crumb, (int(rx) - 2, int(ry) - 2))

    # Player-Marker (immer in der Mitte, mit kleinem Richtungs-Pfeil)
    # B-10 (Update #50): Klassen-themed Marker statt generischem Kreis.
    # Form pro Klasse: warrior = Quadrat (Schild), monk = Diamant (Mudra),
    # mage/witch = Stern (Sigil), ranger/huntress = Dreieck (Pfeilspitze),
    # rogue = umgedrehtes Dreieck (Dolch), druid = Kreis-mit-Blatt.
    # Farbe = Aspekt-Halo aus aspects.py.
    try:
        from . import aspects as _asp
        pal = _asp.aspect_palette(p.cls)
        marker_col = pal['halo']
    except Exception:
        marker_col = GOLD_BRIGHT
    MARKER_SHAPE = {
        'warrior': 'square',
        'monk':    'diamond',
        'mage':    'star',
        'witch':   'star',
        'ranger':  'triangle',
        'huntress':'triangle',
        'rogue':   'triangle_inv',
        'druid':   'circle_leaf',
    }
    shape = MARKER_SHAPE.get(p.cls, 'circle')
    if shape == 'square':
        pygame.draw.rect(surf, marker_col, (cx - 4, cy - 4, 8, 8))
        pygame.draw.rect(surf, WHITE, (cx - 4, cy - 4, 8, 8), 1)
    elif shape == 'diamond':
        pygame.draw.polygon(surf, marker_col,
                             [(cx, cy - 5), (cx + 5, cy),
                              (cx, cy + 5), (cx - 5, cy)])
        pygame.draw.polygon(surf, WHITE,
                             [(cx, cy - 5), (cx + 5, cy),
                              (cx, cy + 5), (cx - 5, cy)], 1)
    elif shape == 'star':
        # 4-Strahl-Stern (kompakt für 256-px Minimap)
        pygame.draw.polygon(surf, marker_col, [
            (cx, cy - 6), (cx + 2, cy - 2), (cx + 6, cy),
            (cx + 2, cy + 2), (cx, cy + 6), (cx - 2, cy + 2),
            (cx - 6, cy), (cx - 2, cy - 2)])
        pygame.draw.circle(surf, WHITE, (cx, cy), 2)
    elif shape == 'triangle':
        pygame.draw.polygon(surf, marker_col,
                             [(cx, cy - 6), (cx + 5, cy + 4),
                              (cx - 5, cy + 4)])
        pygame.draw.polygon(surf, WHITE,
                             [(cx, cy - 6), (cx + 5, cy + 4),
                              (cx - 5, cy + 4)], 1)
    elif shape == 'triangle_inv':
        pygame.draw.polygon(surf, marker_col,
                             [(cx, cy + 6), (cx + 5, cy - 4),
                              (cx - 5, cy - 4)])
        pygame.draw.polygon(surf, WHITE,
                             [(cx, cy + 6), (cx + 5, cy - 4),
                              (cx - 5, cy - 4)], 1)
    elif shape == 'circle_leaf':
        pygame.draw.circle(surf, marker_col, (cx, cy), 5)
        pygame.draw.circle(surf, WHITE, (cx, cy), 5, 1)
        # Blatt-Andeutung (kleiner Bogen oben)
        pygame.draw.arc(surf, (140, 220, 140),
                         (cx - 4, cy - 7, 8, 6), 0, math.pi, 2)
    else:
        pygame.draw.circle(surf, marker_col, (cx, cy), 4)
        pygame.draw.circle(surf, WHITE, (cx, cy), 4, 1)

    # Quest-Marker für NPCs auf der Minimap
    # Update #145: player-aware → locked Quests zeigen kein „!"
    log = getattr(game, 'quest_log', None)
    if log is not None:
        for npc in getattr(game, 'npcs', ()):
            mark = log.npc_marker(npc.name, player=p)
            if not mark:
                continue
            rx = (npc.pos.x - p.pos.x) * mm_scale + cx
            ry = (npc.pos.y - p.pos.y) * mm_scale + cy
            if 2 < rx < mm_w - 2 and 2 < ry < mm_h - 2:
                col = (255, 220, 80) if mark == '!' else (255, 200, 130)
                ix, iy = int(rx), int(ry) - 6
                pygame.draw.circle(surf, col, (ix, iy), 5)
                pygame.draw.circle(surf, (10, 8, 6), (ix, iy), 5, 1)
                # Mini-Symbol in der Mitte (1 px)
                pygame.draw.circle(surf, (10, 8, 6), (ix, iy + 1), 1)

    # Bewegungs-Ziel-Pfeil
    if p.moving:
        diff_x = p.target.x - p.pos.x
        diff_y = p.target.y - p.pos.y
        dist = (diff_x * diff_x + diff_y * diff_y) ** 0.5
        if dist > 1:
            nx, ny = diff_x / dist, diff_y / dist
            # Pfeil-Spitze auf Mini-Map (clip auf max 30 px)
            arrow_len = min(28, dist * mm_scale)
            ax = cx + nx * arrow_len
            ay = cy + ny * arrow_len
            pygame.draw.line(surf, (255, 220, 80), (cx, cy), (ax, ay), 2)
            # Pfeil-Spitze
            import math as _m
            ang = _m.atan2(ny, nx)
            pygame.draw.polygon(surf, (255, 220, 80), [
                (ax, ay),
                (ax - _m.cos(ang - 0.5) * 6, ay - _m.sin(ang - 0.5) * 6),
                (ax - _m.cos(ang + 0.5) * 6, ay - _m.sin(ang + 0.5) * 6),
            ])

    # Mouse-Cursor-Indikator (wo zielst du?)
    import pygame as _pg
    mx, my = _pg.mouse.get_pos()
    # Convert mouse screen pos to world pos
    from .constants import SCREEN_W as _SW, SCREEN_H as _SH
    wmx = mx - _SW / 2 + p.pos.x
    wmy = my - _SH / 2 + p.pos.y
    rmx = (wmx - p.pos.x) * mm_scale + cx
    rmy = (wmy - p.pos.y) * mm_scale + cy
    if 2 < rmx < mm_w - 2 and 2 < rmy < mm_h - 2:
        # Kleines Kreuz für Mausziel
        pygame.draw.line(surf, (255, 255, 255),
                          (int(rmx) - 3, int(rmy)),
                          (int(rmx) + 3, int(rmy)), 1)
        pygame.draw.line(surf, (255, 255, 255),
                          (int(rmx), int(rmy) - 3),
                          (int(rmx), int(rmy) + 3), 1)

    # Klassen-themed Rahmen-Farbe (Lore-Anker)
    from . import quotes as _q
    from . import aspects as _asp
    fac = _q.class_faction(p.cls)
    frame_color = fac['color'] if fac else GOLD

    pygame.draw.rect(surf, frame_color, (0, 0, mm_w, mm_h), 2)
    # B-12 (Update #50): Wenn Setting `minimap_rotate` aktiv ist, drehen
    # wir das gesamte Surface so, dass Player-Facing nach oben zeigt.
    # Die rotierte Surface bleibt auf mm_w × mm_h beschnitten.
    if game.settings.get('minimap_rotate', False):
        # Player-Facing nach oben = -90° Offset, dann gegen-rotieren
        angle_deg = -math.degrees(p.facing) - 90
        rotated = pygame.transform.rotozoom(surf, angle_deg, 1.0)
        # Center-Crop auf mm_w × mm_h
        rw, rh = rotated.get_size()
        crop = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
        crop.blit(rotated,
                  (-(rw - mm_w) // 2, -(rh - mm_h) // 2))
        # Rahmen neu zeichnen (da der alte Rahmen mitrotiert wurde)
        pygame.draw.rect(crop, frame_color, (0, 0, mm_w, mm_h), 2)
        surf = crop
    screen.blit(surf, (mm_x, mm_y))

    # Update #30: Filigree-Eck-Ornamente um Minimap (Velgrad-Design).
    minimap_rect = pygame.Rect(mm_x, mm_y, mm_w, mm_h)
    bronze = (154, 118, 66)
    _asp.draw_filigree_corners(screen, minimap_rect, bronze, size=22)
    # Doppel-Rahmen außen
    pygame.draw.rect(screen, bronze,
                      (mm_x - 4, mm_y - 4, mm_w + 8, mm_h + 8), 1)
    # Compass-N oben
    n_label = font_small.render('N', True, (200, 170, 110))
    bg = pygame.Surface((n_label.get_width() + 6,
                         n_label.get_height() + 2), pygame.SRCALPHA)
    bg.fill((10, 6, 4, 220))
    screen.blit(bg, (mm_x + mm_w // 2 - bg.get_width() // 2, mm_y + 4))
    screen.blit(n_label,
                 (mm_x + mm_w // 2 - n_label.get_width() // 2,
                  mm_y + 5))

    # PLAN: Region-Label „Akt N — <Region-Name>" über der Minimap
    # mit Pergament-Box-Hintergrund (Velgrad-Style).
    from . import regions as _reg
    region_text = _reg.region_label(game.biome) or BIOMES[game.biome]['name']
    region_col = _reg.region_accent(game.biome, GOLD_BRIGHT)
    label = font_small.render(region_text.upper(), True, region_col)
    lbl_w = label.get_width() + 24
    lbl_h = label.get_height() + 6
    lbl_x = mm_x + mm_w // 2 - lbl_w // 2
    lbl_y = mm_y - 22
    # Pergament-Hintergrund
    pbg = pygame.Surface((lbl_w, lbl_h), pygame.SRCALPHA)
    pbg.fill((20, 14, 8, 240))
    screen.blit(pbg, (lbl_x, lbl_y))
    pygame.draw.rect(screen, bronze, (lbl_x, lbl_y, lbl_w, lbl_h), 1)
    screen.blit(label, (lbl_x + 12, lbl_y + 3))


# ============================================================
# PORTAL-ZEICHNEN
# ============================================================
def draw_portal(screen, portal, sp):
    sx, sy = int(sp[0]), int(sp[1])
    biome_data = BIOMES[portal.biome]
    accent = biome_data['accent']
    portal.bob += 0.05

    pulse = abs(math.sin(portal.bob * 2))
    glow = pygame.Surface((140, 140), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        alpha = int(45 / i * (0.6 + pulse * 0.4))
        pygame.draw.circle(glow, (*accent, alpha), (70, 70), 25 + i * 7)
    screen.blit(glow, (sx - 70, sy - 70))

    # Portal-Steinrahmen (sechs Steine im Kreis)
    for i in range(6):
        a = (i / 6) * math.tau + portal.bob * 0.3
        bx = sx + math.cos(a) * 30
        by = sy + math.sin(a) * 30
        pygame.draw.circle(screen, (60, 50, 40), (int(bx), int(by)), 5)
        pygame.draw.circle(screen, accent, (int(bx), int(by)), 5, 1)

    pygame.draw.circle(screen, accent, (sx, sy), 22, 3)
    pygame.draw.circle(screen, (*accent, 200), (sx, sy), 16)
    # Innerer Wirbel
    for i in range(3):
        a = portal.bob * 2 + i * 2
        px = sx + math.cos(a) * 8
        py = sy + math.sin(a) * 8
        pygame.draw.circle(screen, WHITE, (int(px), int(py)), 2)
    pygame.draw.circle(screen, WHITE, (sx, sy), 4)
