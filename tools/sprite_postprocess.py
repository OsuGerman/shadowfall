"""Post-Processing für AI-generierte Sprite-PNGs.

Wandelt den schwarzen Background von Mob/Class/Item-Sprites in Alpha-
Transparenz um. Portraits + Boss-Plates + Tiles behalten ihren BG.

Algorithm:
  1. Lade PNG via Pygame (mit Alpha-Channel).
  2. Pixel-Loop: R+G+B < threshold → Alpha = 0.
  3. Soft-Edge-Feathering: Pixel knapp ueber dem Threshold bekommen
     partial Alpha (verhindert harte schwarze Outlines).
  4. Speichere als PNG zurueck.

Usage:
  python tools/sprite_postprocess.py --all
  python tools/sprite_postprocess.py --category mob
  python tools/sprite_postprocess.py --file assets/sprites/mobs/salzhueter_brut.png
  python tools/sprite_postprocess.py --threshold 40 --feather 10
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pygame

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPRITES_DIR  = PROJECT_ROOT / 'assets' / 'sprites'

# Kategorien die transparent BG brauchen.
# Portrait + Boss-Plate + Tile behalten ihren BG (gewollt).
# Update #166: decor + status (Prio-Pass HOCH, beide transparent per Render-Spec).
TRANSPARENT_BG_CATEGORIES = {'mobs', 'classes', 'items', 'decor', 'status'}


def remove_background(png_path: Path,
                      threshold: int = 30,
                      feather: int = 8,
                      flood_from_edges: bool = True,
                      erode: int = 0,
                      bg_color: str = 'black') -> bool:
    """Macht alle Background-Pixel transparent. bg_color: 'black' (default)
    oder 'white'. Bei 'white' wird brightness invertiert (nahe-weiss = BG)."""
    if bg_color == 'white':
        return _remove_bg_impl(png_path, threshold, feather, flood_from_edges,
                                erode, invert=True)
    return _remove_bg_impl(png_path, threshold, feather, flood_from_edges,
                            erode, invert=False)


def remove_black_background(png_path: Path,
                            threshold: int = 30,
                            feather: int = 8,
                            flood_from_edges: bool = True,
                            erode: int = 0) -> bool:
    """Backwards-Compat-Alias fuer remove_background(bg_color='black')."""
    return remove_background(png_path, threshold, feather, flood_from_edges,
                              erode, bg_color='black')


def _remove_bg_impl(png_path: Path,
                    threshold: int,
                    feather: int,
                    flood_from_edges: bool,
                    erode: int,
                    invert: bool) -> bool:
    """Implementation. invert=True: weisser BG (brightness>765-threshold = BG).
    Soft-Edge-Feathering verhindert harte Outlines.

    flood_from_edges: Wenn True (Default), wird zusaetzlich ein Edge-Flood-
        Fill durchgefuehrt — nur das vom Bild-Rand aus erreichbare schwarze
        Areal wird transparent. Innere dunkle Regionen (Charakter-Schatten,
        Stiefel etc.) bleiben erhalten. Verhindert das typische "schwarzer
        Rand bleibt"-Problem.
    erode: Pixel-Erosion-Pass nach BG-Removal. erode=N entfernt N Pixel vom
        Charakter-Rand (frisst Black-Halos weg). Default 0, sinnvoll 1-2.

    Returnt True bei Erfolg, False bei Fehler.
    """
    if not png_path.is_file():
        return False
    # Pygame Display nicht noetig - SDL2 unterstuetzt headless image-only.
    if not pygame.get_init():
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        pygame.init()

    try:
        src = pygame.image.load(str(png_path))
    except Exception as e:
        print(f'  load fail {png_path.name}: {e}', file=sys.stderr)
        return False
    if src.get_size() == (0, 0):
        return False
    w, h = src.get_size()
    # Headless-safe: SRCALPHA-Surface ohne convert_alpha()
    dst = pygame.Surface((w, h), pygame.SRCALPHA)

    # Versuche numpy-Backed (schnell), fallback per-pixel.
    try:
        import numpy as np
        pixels = pygame.surfarray.pixels3d(src)          # (w, h, 3)
        # Pygame surfarray ist (w, h, c) — wir bauen alpha-array.
        # WICHTIG: sum() liefert uint64 → wir casten zu int32 damit
        # spaeter (eff - threshold) keinen Unsigned-Underflow ausloest
        # (uint64 0 - 30 = ~1.8e19 → ganzer Bug-Modus).
        brightness = pixels.sum(axis=2).astype(np.int32)  # (w, h)
        # Bei invert (weisser BG): brightness > 765 - threshold = BG.
        # Wir spiegeln das Problem: effektive_brightness = 765 - brightness.
        # Dann gilt wieder: low → BG, high → Charakter.
        if invert:
            eff_brightness = (765 - brightness).astype(np.int32)
        else:
            eff_brightness = brightness
        # Voll-transparent: eff_brightness < threshold
        # Voll-opaque: eff_brightness > threshold + feather*3
        # Linear zwischen den beiden
        if feather > 0:
            edge_hi = threshold + feather * 3
            alpha = np.clip(
                (eff_brightness - threshold) * (255.0 / (edge_hi - threshold)),
                0, 255
            ).astype(np.uint8)
        else:
            alpha = np.where(eff_brightness < threshold, 0, 255).astype(np.uint8)

        # Edge-Flood-Fill: nur BG-erreichbare bereits-transparente Pixel
        # werden komplett transparent (alpha=0). Pixel die der brightness-
        # Rule nach OPAK sind (alpha > 32) blockieren den Flood — somit
        # bleibt der Charakter intakt und innere dunkle Pixel werden
        # nicht weggefressen.
        if flood_from_edges:
            # Travelable = bereits hauptsaechlich transparent (von Rule 1)
            travelable = alpha < 32
            # Seed: alle travelable-Pixel auf der Bild-Kante
            reachable = np.zeros_like(travelable)
            reachable[0, :]  = travelable[0, :]
            reachable[-1, :] = travelable[-1, :]
            reachable[:, 0]  = travelable[:, 0]
            reachable[:, -1] = travelable[:, -1]
            # Iterative 4-neighbour-Dilation, beschraenkt auf travelable.
            # Schnellabbruch wenn kein neuer Pixel mehr dazukommt.
            for _ in range(max(w, h)):
                prev_count = int(reachable.sum())
                grown = reachable.copy()
                grown[1:, :]  |= reachable[:-1, :]
                grown[:-1, :] |= reachable[1:, :]
                grown[:, 1:]  |= reachable[:, :-1]
                grown[:, :-1] |= reachable[:, 1:]
                reachable = grown & travelable
                if int(reachable.sum()) == prev_count:
                    break
            # Update #175 (Fix Transparenz-Problem): Inner Char-Pixel sollen
            # VOLL-opak sein, nur die EDGE-Ring-Pixel behalten feathered Alpha
            # fuer Soft-Boundary. Vorher: alle non-reachable Pixel behielten
            # ihren brightness-basierten Alpha-Wert → dunkle Robe/Schatten
            # mit brightness 30-60 wurden teil-transparent → Char sah
            # durchsichtig aus.
            #
            # Vorgehen:
            #   1. Char-Mask = ~reachable (alles was nicht von Bildrand erreichbar)
            #   2. Erode 2 → Core (sicher-innen, > 2px vom BG-Rand entfernt)
            #   3. Core-Pixel → alpha=255 (voll opak)
            #   4. Edge-Ring (char_mask AND NOT core) → behaelt feathered alpha
            #      (gibt smooth-edge-Uebergang)
            #   5. BG (reachable) → alpha=0
            char_mask = ~reachable
            # Erode 2px um Core zu bekommen (deep interior)
            core = char_mask.copy()
            for _ in range(2):
                eroded = core.copy()
                eroded[1:, :]  &= core[:-1, :]
                eroded[:-1, :] &= core[1:, :]
                eroded[:, 1:]  &= core[:, :-1]
                eroded[:, :-1] &= core[:, 1:]
                core = eroded
            # Core → voll-opak; restliche char_mask → feathered alpha; BG → 0
            alpha = np.where(core, 255, alpha)
            alpha = np.where(reachable, 0, alpha).astype(np.uint8)

        # Erode: shrink charakter mask um N Pixel (frisst Halos weg)
        if erode > 0:
            opaque = alpha > 0
            for _ in range(erode):
                eroded = opaque.copy()
                eroded[1:, :]  &= opaque[:-1, :]
                eroded[:-1, :] &= opaque[1:, :]
                eroded[:, 1:]  &= opaque[:, :-1]
                eroded[:, :-1] &= opaque[:, 1:]
                opaque = eroded
            alpha = np.where(opaque, alpha, 0).astype(np.uint8)

        # Schreibe Pixel + Alpha in dst
        dst_pixels = pygame.surfarray.pixels3d(dst)
        dst_alpha  = pygame.surfarray.pixels_alpha(dst)
        dst_pixels[:] = pixels
        dst_alpha[:]  = alpha
        del pixels, dst_pixels, dst_alpha  # locks aufheben
    except ImportError:
        # Slow per-pixel fallback (kein numpy)
        src_lock = src.lock()
        for y in range(h):
            for x in range(w):
                r, g, b, a = src.get_at((x, y))
                bright = r + g + b
                if bright < threshold:
                    dst.set_at((x, y), (r, g, b, 0))
                elif feather > 0 and bright < threshold + feather * 3:
                    new_a = int((bright - threshold) * (255 / (feather * 3)))
                    dst.set_at((x, y), (r, g, b, max(0, min(255, new_a))))
                else:
                    dst.set_at((x, y), (r, g, b, 255))
        src.unlock()

    try:
        pygame.image.save(dst, str(png_path))
        return True
    except Exception as e:
        print(f'  save fail {png_path.name}: {e}', file=sys.stderr)
        return False


def process_directory(category_dir: Path, threshold: int, feather: int,
                       flood: bool = True, erode: int = 0) -> tuple[int, int]:
    """Verarbeitet alle .png-Dateien in einem Kategorie-Unterordner."""
    if not category_dir.is_dir():
        return (0, 0)
    pngs = sorted(category_dir.glob('*.png'))
    ok, fail = 0, 0
    for p in pngs:
        before = p.stat().st_size
        if remove_black_background(p, threshold, feather,
                                    flood_from_edges=flood, erode=erode):
            after = p.stat().st_size
            delta = after - before
            print(f'  {category_dir.name}/{p.name:<40} {before//1024}K -> {after//1024}K  '
                  f'({delta:+d}B)')
            ok += 1
        else:
            fail += 1
    return (ok, fail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true',
                    help='Alle transparent-BG-Kategorien (mob/class/item/decor/status)')
    ap.add_argument('--category',
                    choices=['mob', 'class', 'item', 'decor', 'status', 'all'],
                    default=None)
    ap.add_argument('--file', type=str, default=None,
                    help='Einzelnes PNG verarbeiten')
    ap.add_argument('--threshold', type=int, default=30,
                    help='Pixel mit R+G+B < threshold -> alpha=0 (default 30)')
    ap.add_argument('--feather', type=int, default=8,
                    help='Soft-Edge-Pixelbereich gegen harte Outlines '
                         '(default 8; 0=hart-Schnitt)')
    ap.add_argument('--no-flood', action='store_true',
                    help='Edge-Flood-Fill deaktivieren (default an)')
    ap.add_argument('--erode', type=int, default=0,
                    help='N Pixel vom Rand wegfressen (default 0; '
                         'sinnvoll 1-2 gegen Black-Halos)')
    ap.add_argument('--bg', choices=['black', 'white'], default='black',
                    help='Background-Farbe die entfernt wird (default black)')
    args = ap.parse_args()

    if args.file:
        p = Path(args.file)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        ok = remove_background(p, args.threshold, args.feather,
                                flood_from_edges=not args.no_flood,
                                erode=args.erode, bg_color=args.bg)
        print(f'{"OK" if ok else "FAIL"}: {p}')
        return

    targets = []
    if args.all or args.category == 'all' or args.category is None:
        targets = ['mobs', 'classes', 'items', 'decor', 'status']
    elif args.category == 'mob':
        targets = ['mobs']
    elif args.category == 'class':
        targets = ['classes']
    elif args.category == 'item':
        targets = ['items']
    elif args.category == 'decor':
        targets = ['decor']
    elif args.category == 'status':
        targets = ['status']

    total_ok, total_fail = 0, 0
    for sub in targets:
        d = SPRITES_DIR / sub
        if not d.is_dir():
            continue
        print(f'=== {sub}/ ===')
        ok, fail = process_directory(d, args.threshold, args.feather,
                                       flood=not args.no_flood,
                                       erode=args.erode)
        total_ok += ok
        total_fail += fail
    print(f'\nFertig. {total_ok} verarbeitet, {total_fail} failed.')


if __name__ == '__main__':
    main()
