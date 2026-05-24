"""Per-Biome Wall-Tile-Generator (Update #170).

Erzeugt UNIQUE Wall-Tiles fuer jedes Biom mit biom-spezifischen
Algorithmen — NICHT die gleiche "darken+noise+joints"-Logik fuer alle.
Jedes Biom bekommt seinen eigenen Wall-Charakter:

  crypt        → Stein-Mauer mit Joint-Pattern (Original)
  frost        → Ice-Block-Wand, Frost-Kristall-Risse, hellblaue Highlights
  lava         → Obsidian-Wand mit gluehenden Cracks (Floor-Cracks intensiviert)
  swamp        → Modrige Bohlen, Diagonal-Faser-Pattern, Wurzel-Reste
  astral       → Cosmic-Kristall mit Stern-Spots, lila Glow-Adern
  desert       → Sandstein mit horizontalen Wettering-Baendern, beige
  town         → Mauerwerk + Holzbalken-Joints, mittel-grau
  wound_salt   → Salt-Pillar-Cluster (helle Kristall-Klumpen auf dunkel)
  wound_ash    → Verbrannte Borke, dunkel mit roten Glut-Resten
  wound_hollow → Void-Rift-Wand, schwarz mit purple-rifts
  hollow_word  → Rune-Glyphen-Stein, geaetzte Symbole, bronze-Aether-Glow

Tools die kombiniert werden (je nach Biom):
  - Darken + Saturate (alle)
  - Joint-Pattern (crypt/town) ← rechteckige Mauerwerk-Lines
  - Crystal-Spike (frost/wound_salt) ← branching crystals
  - Crack-Glow (lava/wound_ash) ← extrudieren bestehende Floor-Cracks
  - Vein-Pattern (swamp/astral/wound_hollow) ← organic curves
  - Horizontal-Bands (desert) ← weathered sandstone strata
  - Star-Spots (astral/hollow_word) ← klein helle Punkte
  - Rune-Glyph-Stamps (hollow_word) ← geometric ASCII-like marks

Usage:
  python tools/wall_from_floor.py --all
  python tools/wall_from_floor.py --biome lava

Output: assets/sprites/tiles/<biome>_wall_w.png

Doku: VELGRAD_RENDER_SPEC.md (tile_wall category)
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TILES_DIR = PROJECT_ROOT / 'assets' / 'sprites' / 'tiles'


# ============================================================
# BIOME → FLOOR-SOURCE-FILE
# ============================================================
BIOME_FLOOR_SOURCE = {
    'crypt':        'crypt_floor_a.png',
    'frost':        'frost_glass_ruins_akt_2.png',
    'lava':         'lava_akt_3.png',
    'swamp':        'swamp_akt_4.png',
    'astral':       'astral_akt_5.png',
    'desert':       'desert_akt_1b.png',
    'town':         'town_brassweir.png',
    'wound_salt':   'wound_salt_akt_6a.png',
    'wound_ash':    'wound_ash_akt_6b.png',
    'wound_hollow': 'wound_hollow_akt_6c.png',
    'hollow_word':  'hollow_word_akt_7.png',
}


# ============================================================
# BASIS-TRANSFORMS (kleine wiederverwendbare Steps)
# ============================================================
def _darken(px, factor):
    """Multiplikative Brightness-Reduktion (factor in 0..1, 0=ganz dunkel)."""
    px *= (1.0 - factor)
    return px


def _saturate(px, mult):
    """Saturation-Multiplikator (1.0 neutral, >1.0 farbiger, <1.0 grauer)."""
    if mult == 1.0:
        return px
    gray = px.mean(axis=2, keepdims=True)
    return gray + (px - gray) * mult


def _tint(px, rgb_offset):
    """Add RGB offsets (kann auch negativ sein) — fuer Biome-Mood-Shift."""
    px[..., 0] += rgb_offset[0]
    px[..., 1] += rgb_offset[1]
    px[..., 2] += rgb_offset[2]
    return px


def _noise(px, amp, rng):
    """Add high-frequency noise (Stein-Textur)."""
    if amp <= 0:
        return px
    import numpy as np
    n = rng.integers(-amp, amp + 1, size=px.shape, dtype=np.int16
                      ).astype(px.dtype)
    return px + n


def _vignette(px, strength=0.25):
    """Radial-Darkening von Mitte zu Ecken."""
    import numpy as np
    w, h = px.shape[0], px.shape[1]
    cx, cy = w / 2, h / 2
    max_r = (cx ** 2 + cy ** 2) ** 0.5
    yy, xx = np.indices((w, h))
    dist = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
    factor = 1.0 - (dist / max_r) * strength
    factor = np.clip(factor, 0.0, 1.0)
    for c in range(3):
        px[..., c] *= factor
    return px


# ============================================================
# BIOM-SPEZIFISCHE OVERLAY-PATTERNS
# ============================================================
def _add_joint_pattern(px, joint_cell, joint_darken=0.25, offset_mauerwerk=True):
    """Rechteckiges Mauerwerk-Joint-Pattern (crypt, town)."""
    w, h = px.shape[0], px.shape[1]
    factor_h = 1.0 - joint_darken
    factor_v = 1.0 - joint_darken * 0.8
    # Horizontal joints
    for y in range(0, h, joint_cell):
        if y < h:
            px[:, y, :] *= factor_h
        if y + 1 < h:
            px[:, y + 1, :] *= (1.0 - 0.10)
    # Vertical joints versetzt
    offset_pattern = [0, joint_cell // 2] if offset_mauerwerk else [0, 0]
    for row_i, y_start in enumerate(range(0, h, joint_cell)):
        ox = offset_pattern[row_i % 2]
        for x in range(ox, w, joint_cell):
            if x < w:
                y_end = min(y_start + joint_cell, h)
                px[x, y_start:y_end, :] *= factor_v
    return px


def _add_crystal_spikes(px, color=(180, 220, 255), n_spikes=12, rng=None):
    """Branching Eis/Kristall-Spikes (frost, wound_salt)."""
    import numpy as np
    if rng is None:
        rng = np.random.default_rng(7)
    w, h = px.shape[0], px.shape[1]
    for _ in range(n_spikes):
        x0 = int(rng.integers(0, w))
        y0 = int(rng.integers(0, h))
        # Hauptast
        length = int(rng.integers(30, 100))
        ang = rng.uniform(0, math.tau)
        dx = math.cos(ang)
        dy = math.sin(ang)
        for t in range(length):
            x = int(x0 + dx * t)
            y = int(y0 + dy * t)
            if 0 <= x < w and 0 <= y < h:
                # Helle Linie, fade-out mit Distanz
                fade = 1.0 - (t / length)
                for c in range(3):
                    px[x, y, c] = px[x, y, c] * (1.0 - fade * 0.6) + color[c] * fade * 0.6
        # Verzweigungen
        for _ in range(int(rng.integers(1, 3))):
            branch_t = int(rng.integers(5, length // 2 + 1))
            bx = int(x0 + dx * branch_t)
            by = int(y0 + dy * branch_t)
            ang2 = ang + rng.uniform(-1.2, 1.2)
            blen = int(rng.integers(8, 30))
            for t in range(blen):
                x = int(bx + math.cos(ang2) * t)
                y = int(by + math.sin(ang2) * t)
                if 0 <= x < w and 0 <= y < h:
                    fade = 1.0 - (t / blen)
                    for c in range(3):
                        px[x, y, c] = px[x, y, c] * (1.0 - fade * 0.4) + color[c] * fade * 0.4
    return px


def _intensify_floor_cracks(px, glow_color=(255, 120, 40), strength=0.7):
    """Findet dunkle Crack-Linien im Floor und macht sie GLUEHEND (lava, wound_ash).
    Voraussetzung: Floor hat bereits Crack-Pattern, hier nur amplifiziert.
    """
    import numpy as np
    # Crack-Detection: lokal-darker-Pixel als Glow-Kandidaten
    brightness = px.mean(axis=2)
    # Threshold: pixel ist crack wenn deutlich dunkler als ringsherum (z.B. <30% of avg)
    avg = brightness.mean()
    crack_mask = brightness < (avg * 0.4)
    # Apply glow color where mask, mit Distance-Falloff zur Mitte des Cracks
    for c, gc in enumerate(glow_color):
        # Lerp pixel toward glow color in crack regions
        px[crack_mask, c] = (
            px[crack_mask, c] * (1.0 - strength) + gc * strength
        )
    return px


def _add_diagonal_veins(px, color=(80, 100, 60), n_veins=18, thickness=2, rng=None):
    """Diagonale organische Faser-Linien (swamp, wound_hollow)."""
    import numpy as np
    if rng is None:
        rng = np.random.default_rng(11)
    w, h = px.shape[0], px.shape[1]
    for _ in range(n_veins):
        x0 = int(rng.integers(-30, w + 30))
        y0 = int(rng.integers(0, h))
        ang = rng.uniform(math.pi / 6, math.pi / 3)
        if rng.random() < 0.5:
            ang = -ang
        length = int(rng.integers(80, max(81, min(w, h))))
        dx = math.cos(ang)
        dy = math.sin(ang)
        for t in range(length):
            x = int(x0 + dx * t)
            y = int(y0 + dy * t)
            for tk in range(-thickness, thickness + 1):
                for ty in range(-thickness, thickness + 1):
                    xx = x + tk
                    yy = y + ty
                    if 0 <= xx < w and 0 <= yy < h:
                        # leichtes Darkening, organisch wirkend
                        blend = 0.35 * (1 - abs(tk) / (thickness + 1))
                        for c in range(3):
                            px[xx, yy, c] = (
                                px[xx, yy, c] * (1.0 - blend) + color[c] * blend
                            )
    return px


def _add_horizontal_strata(px, n_bands=8, darken=0.20, rng=None):
    """Horizontale Wettering-Baender (desert sandstone)."""
    import numpy as np
    if rng is None:
        rng = np.random.default_rng(13)
    w, h = px.shape[0], px.shape[1]
    band_h = h // n_bands
    for i in range(n_bands):
        y_start = i * band_h + int(rng.integers(-4, 4))
        y_end = y_start + int(rng.integers(2, 6))
        if y_start < 0:
            y_start = 0
        if y_end > h:
            y_end = h
        if y_end > y_start:
            px[:, y_start:y_end, :] *= (1.0 - darken)
    return px


def _add_star_specks(px, color=(220, 200, 255), n_stars=80, rng=None):
    """Helle Spots (astral, hollow_word)."""
    import numpy as np
    if rng is None:
        rng = np.random.default_rng(17)
    w, h = px.shape[0], px.shape[1]
    for _ in range(n_stars):
        x = int(rng.integers(0, w))
        y = int(rng.integers(0, h))
        size = int(rng.integers(1, 3))
        intensity = rng.uniform(0.4, 0.9)
        for dx in range(-size, size + 1):
            for dy in range(-size, size + 1):
                xx = x + dx
                yy = y + dy
                if 0 <= xx < w and 0 <= yy < h:
                    falloff = max(0, 1.0 - (dx ** 2 + dy ** 2) ** 0.5 / (size + 1))
                    blend = intensity * falloff
                    for c in range(3):
                        px[xx, yy, c] = (
                            px[xx, yy, c] * (1.0 - blend) + color[c] * blend
                        )
    return px


def _add_rune_glyphs(px, color=(200, 180, 80), n_glyphs=6, rng=None):
    """Geaetzte Rune-Symbole (hollow_word). Geometric ASCII-Style-Marks."""
    import numpy as np
    if rng is None:
        rng = np.random.default_rng(19)
    w, h = px.shape[0], px.shape[1]
    glyph_size = 28
    for _ in range(n_glyphs):
        cx = int(rng.integers(glyph_size, w - glyph_size))
        cy = int(rng.integers(glyph_size, h - glyph_size))
        # Pick a glyph-shape (rectangle-frame, T, X, V)
        shape_id = int(rng.integers(0, 4))
        # Linien-Color blended in
        def _draw_line(x1, y1, x2, y2, blend=0.65):
            # Bresenham
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            steps = max(abs(x2 - x1), abs(y2 - y1))
            if steps == 0:
                return
            for s in range(steps + 1):
                t = s / steps
                xi = int(x1 + (x2 - x1) * t)
                yi = int(y1 + (y2 - y1) * t)
                if 0 <= xi < w and 0 <= yi < h:
                    for c in range(3):
                        px[xi, yi, c] = (
                            px[xi, yi, c] * (1.0 - blend) + color[c] * blend
                        )
        if shape_id == 0:
            # Rechteck-Frame
            _draw_line(cx - glyph_size // 2, cy - glyph_size // 2,
                       cx + glyph_size // 2, cy - glyph_size // 2)
            _draw_line(cx + glyph_size // 2, cy - glyph_size // 2,
                       cx + glyph_size // 2, cy + glyph_size // 2)
            _draw_line(cx + glyph_size // 2, cy + glyph_size // 2,
                       cx - glyph_size // 2, cy + glyph_size // 2)
            _draw_line(cx - glyph_size // 2, cy + glyph_size // 2,
                       cx - glyph_size // 2, cy - glyph_size // 2)
        elif shape_id == 1:
            # T-Form
            _draw_line(cx - glyph_size // 2, cy - glyph_size // 2,
                       cx + glyph_size // 2, cy - glyph_size // 2)
            _draw_line(cx, cy - glyph_size // 2, cx, cy + glyph_size // 2)
        elif shape_id == 2:
            # X-Form
            _draw_line(cx - glyph_size // 2, cy - glyph_size // 2,
                       cx + glyph_size // 2, cy + glyph_size // 2)
            _draw_line(cx + glyph_size // 2, cy - glyph_size // 2,
                       cx - glyph_size // 2, cy + glyph_size // 2)
        else:
            # V-Form
            _draw_line(cx - glyph_size // 2, cy - glyph_size // 2,
                       cx, cy + glyph_size // 2)
            _draw_line(cx, cy + glyph_size // 2,
                       cx + glyph_size // 2, cy - glyph_size // 2)
    return px


# ============================================================
# PER-BIOM WALL-RECIPE
# ============================================================
def _build_wall_for_biome(biome: str, floor_px, rng):
    """Wendet biom-spezifische Transforms an. Returnt modified array."""
    px = floor_px.copy()
    import numpy as np
    px = px.astype(np.float32)

    if biome == 'crypt':
        # Stein-Mauer mit Joint-Pattern
        px = _darken(px, 0.50)
        px = _tint(px, (15, -5, -10))
        px = _saturate(px, 1.0)
        px = _noise(px, 18, rng)
        px = _add_joint_pattern(px, joint_cell=64, joint_darken=0.25)
        px = _vignette(px, 0.25)

    elif biome == 'frost':
        # Eis-Block-Wand mit Crystal-Spikes, hellblauer Tint
        px = _darken(px, 0.40)
        px = _tint(px, (-25, -10, 30))
        px = _saturate(px, 1.2)
        px = _noise(px, 12, rng)
        px = _add_crystal_spikes(
            px, color=(200, 230, 255), n_spikes=14, rng=rng)
        px = _vignette(px, 0.20)

    elif biome == 'lava':
        # Obsidian-Wand: dunkel + gluehende Cracks vom Floor verstaerkt
        px = _darken(px, 0.65)
        px = _tint(px, (10, -10, -25))
        px = _saturate(px, 1.1)
        px = _intensify_floor_cracks(
            px, glow_color=(255, 110, 30), strength=0.55)
        px = _noise(px, 20, rng)
        px = _vignette(px, 0.30)

    elif biome == 'swamp':
        # Modrige Bohlen mit Wurzel-Adern
        px = _darken(px, 0.55)
        px = _tint(px, (-20, 5, -20))
        px = _saturate(px, 0.85)
        px = _add_diagonal_veins(
            px, color=(60, 75, 45), n_veins=22, thickness=2, rng=rng)
        px = _noise(px, 16, rng)
        px = _vignette(px, 0.22)

    elif biome == 'astral':
        # Cosmic-Kristall mit Stern-Spots
        px = _darken(px, 0.55)
        px = _tint(px, (-5, -15, 25))
        px = _saturate(px, 1.4)
        px = _add_star_specks(
            px, color=(230, 200, 255), n_stars=120, rng=rng)
        px = _add_diagonal_veins(
            px, color=(160, 120, 220), n_veins=10, thickness=1, rng=rng)
        px = _vignette(px, 0.18)

    elif biome == 'desert':
        # Sandstein mit horizontalen Wettering-Baendern
        px = _darken(px, 0.40)
        px = _tint(px, (20, 5, -20))
        px = _saturate(px, 0.85)
        px = _add_horizontal_strata(
            px, n_bands=10, darken=0.18, rng=rng)
        px = _noise(px, 16, rng)
        px = _vignette(px, 0.20)

    elif biome == 'town':
        # Mauerwerk + Holzbalken — gross-skaliges Pattern
        px = _darken(px, 0.45)
        px = _tint(px, (5, -5, -10))
        px = _saturate(px, 0.95)
        px = _noise(px, 14, rng)
        px = _add_joint_pattern(
            px, joint_cell=80, joint_darken=0.30,
            offset_mauerwerk=True)
        px = _vignette(px, 0.20)

    elif biome == 'wound_salt':
        # Salz-Pillar-Cluster: helle Kristalle auf dunkel
        px = _darken(px, 0.55)
        px = _tint(px, (10, 10, -10))
        px = _saturate(px, 0.85)
        px = _add_crystal_spikes(
            px, color=(230, 220, 200), n_spikes=18, rng=rng)
        px = _add_star_specks(
            px, color=(220, 210, 180), n_stars=40, rng=rng)
        px = _vignette(px, 0.22)

    elif biome == 'wound_ash':
        # Verbrannte Borke + Glut-Reste
        px = _darken(px, 0.65)
        px = _tint(px, (15, -5, -15))
        px = _saturate(px, 0.80)
        px = _intensify_floor_cracks(
            px, glow_color=(180, 80, 20), strength=0.35)
        px = _noise(px, 18, rng)
        px = _vignette(px, 0.30)

    elif biome == 'wound_hollow':
        # Void-Rift-Wand: schwarz + purple-rifts
        px = _darken(px, 0.70)
        px = _tint(px, (-10, -10, 20))
        px = _saturate(px, 1.1)
        px = _add_diagonal_veins(
            px, color=(120, 60, 180), n_veins=16, thickness=2, rng=rng)
        px = _noise(px, 12, rng)
        px = _vignette(px, 0.35)

    elif biome == 'hollow_word':
        # Rune-Glyphen-Stein mit Aether-Glow
        px = _darken(px, 0.50)
        px = _tint(px, (20, -5, 15))
        px = _saturate(px, 1.15)
        px = _add_rune_glyphs(
            px, color=(220, 180, 90), n_glyphs=7, rng=rng)
        px = _add_star_specks(
            px, color=(220, 200, 140), n_stars=40, rng=rng)
        px = _noise(px, 12, rng)
        px = _vignette(px, 0.22)

    else:
        # Fallback: generic
        px = _darken(px, 0.50)
        px = _noise(px, 16, rng)
        px = _vignette(px, 0.25)

    import numpy as np
    return np.clip(px, 0, 255).astype(np.uint8)


# ============================================================
# MAIN
# ============================================================
def generate_wall(biome: str, floor_path: Path, out_path: Path,
                   seed: int = 42) -> bool:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    import pygame
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.set_mode((1, 1))

    if not floor_path.is_file():
        print(f'  ERROR: Source-Floor nicht gefunden: {floor_path}',
              file=sys.stderr)
        return False
    try:
        src = pygame.image.load(str(floor_path))
    except Exception as e:
        print(f'  ERROR: Load fail: {e}', file=sys.stderr)
        return False

    try:
        import numpy as np
    except ImportError:
        print('  ERROR: numpy benoetigt', file=sys.stderr)
        return False

    rng = np.random.default_rng(seed)
    w, h = src.get_size()
    floor_px = pygame.surfarray.pixels3d(src).copy()
    del src

    wall_px = _build_wall_for_biome(biome, floor_px, rng)

    out_surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(out_surf, wall_px)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(out_surf, str(out_path))
    return True


def main():
    ap = argparse.ArgumentParser(
        description='Per-Biome Wall-Tile-Generator')
    ap.add_argument('--biome', type=str, default=None)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--skip-existing', action='store_true')
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    if args.all:
        biomes = list(BIOME_FLOOR_SOURCE.keys())
    elif args.biome:
        biomes = [args.biome]
    else:
        print('Bitte --biome <name> oder --all angeben.')
        print(f'Verfuegbare biomes: {sorted(BIOME_FLOOR_SOURCE.keys())}')
        return

    print('=' * 60)
    print(f'  Per-Biome Wall-Generator (unique pro Biom)')
    print('=' * 60)

    ok = skipped = failed = 0
    for biome in biomes:
        floor_name = BIOME_FLOOR_SOURCE.get(biome)
        if not floor_name:
            print(f'  [{biome}] keine Floor-Source')
            failed += 1
            continue
        floor_path = TILES_DIR / floor_name
        out_path = TILES_DIR / f'{biome}_wall_w.png'

        if args.skip_existing and out_path.is_file():
            print(f'  [{biome}] EXISTS, skip')
            skipped += 1
            continue

        result = generate_wall(biome, floor_path, out_path,
                                seed=args.seed)
        if result:
            print(f'  [{biome}] OK')
            ok += 1
        else:
            print(f'  [{biome}] FAIL')
            failed += 1

    print('=' * 60)
    print(f'  Done. OK={ok}  Skipped={skipped}  Failed={failed}')
    print('=' * 60)


if __name__ == '__main__':
    main()
